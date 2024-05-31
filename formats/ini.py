# -*- coding: utf-8 -*-
# @Time: 2022/04/20 0:00
# @Author: Chloride
"""C&C INI handler.

Since Ares implemented new features of ini structure,
- section inheritance: `[A]:[B]`
- fast append: `+= C`
- include sub inis: `[#include]` (NOT directly)

the standard lib `configparser` won't be suitable anymore.
"""

import warnings
from io import BytesIO, TextIOWrapper
from multiprocessing.pool import ThreadPool
from os.path import join, split
from threading import Thread
from typing import (AnyStr, ItemsView, Iterator, KeysView, List,
                    MutableMapping, Optional, Sequence, ValuesView)
from uuid import uuid1 as guid

from chardet import detect_all as guess_codec

__all__ = ['INIClass', 'INISection', 'INIParser']


class INISection(MutableMapping):
    """... is a dict, maintaining pairs and comments.

    In principle, `INISection` stores data by the following terms:
    - `key: [value]`
    - `key: [value, trail_comment]`
    - `f';{comment_guid}': [None, line_comment]`

    All above SHOULD be `str: List[str | None]`,
    however in runtime we wouldn't limit that much.

    And to get things easier, key-value access would ignore comments.
    """
    def __init__(self, **pairs_to_import):
        """Init a dictionary of ini entries included by section."""
        self.__raw: MutableMapping[str, List[Optional[AnyStr]]] = {}
        self._keydiff = 0
        self.summary: Optional[AnyStr] = None
        if pairs_to_import:
            self.update(pairs_to_import)

    def __setitem__(self, k: str, v: str):
        if k == '+':
            k = '+%d' % self._keydiff
            self._keydiff += 1
        if k not in self:
            self.__raw[k] = [v]
        else:
            self.__raw[k][0] = v

    def __getitem__(self, key: str) -> str:
        return self.__raw[key][0]

    def __delitem__(self, key: str) -> None:
        del self.__raw[key]

    def __len__(self) -> int:
        return len(self.__raw)

    def __iter__(self) -> Iterator:
        return iter(self.keys())  # shouldn't include comments' UUID.

    def __repr__(self) -> str:
        return self.__raw.__repr__()

    def keys(self) -> KeysView:
        return (i for i in self.__raw.keys() if not i.startswith(';'))

    def values(self) -> ValuesView:
        return (i[0] for i in self.__raw.values() if i[0] is not None)

    def items(self) -> ItemsView:
        return ((k, v[0]) for k, v in self.__raw.items()
                if not k.startswith(';'))

    def _items_raw(self):
        return self.__raw.items()

    def _append_line_comment(self, comment: str):
        self.__raw[f';{str(guid())}'] = [None, comment]

    def _add_inline_comment(self, key, comment):
        raw_val_list = self.__raw[key]
        if len(raw_val_list) > 1:
            raw_val_list[1] = comment
        else:
            raw_val_list.append(comment)


class INIClass(MutableMapping[str, INISection]):
    """... is simply a group of dict,
    representing a whole INI file (or tree).
    """
    def __init__(self):
        """Init an empty INI document."""
        self.__raw: MutableMapping[str, INISection] = {}
        self.inheritance = {}
        self.header = INISection()

    def __getitem__(self, key: str) -> INISection:
        return self.__raw.__getitem__(key)

    def __setitem__(self, key: str, value: INISection) -> None:
        return self.__raw.__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        if key in self.inheritance:
            del self.inheritance[key]
        return self.__raw.__delitem__(key)

    def __iter__(self) -> Iterator:
        return self.__raw.__iter__()

    def __len__(self) -> int:
        return self.__raw.__len__()

    def getTypeList(self, section):
        """Collects a **ordered** sequence of the "type" list section,
        like `BuildingTypes`, with elements **unique**.
        """
        if section not in self.__raw:
            return tuple()

        ret = []
        for i in self.__raw[section].values():
            if i is None or i == '':
                continue
            if i in ret:
                continue
            ret.append(i)
        return ret

    def recursiveFind(self, section, key) -> Sequence[Optional[str]]:
        """Start searching from a specific section.

        If key not found and inheritance detected, then go further,
        until the condition broken.

        Returns:
            - the name of section, which contains the given key,
              or `None` if tracking stopped.
            - its value (like `self[section][key]`), or `None`.
        """
        value = None
        while True:
            if key in self[section]:
                value = self[section][key]
                break
            section = self.inheritance.get(section)
            if section is None:
                break
        return section, value

    def clear(self):
        self.inheritance.clear()
        self.header.clear()
        self.__raw.clear()

    def rename(self, old, new):
        """Rename a section.

        Args:
            old: The section name to be replaced.
            new: Name to apply.

        Returns:
            `True` if succeed, otherwise `False`.
            May not success if `old` is not found or `new` already exists.
        """
        if old not in self.__raw or new in self.__raw:
            return False

        sections, datas = list(self.keys()), list(self.values())
        oldidx = sections.index(old)
        sections[oldidx] = new
        oldinherit = self.inheritance.get(old)
        if oldinherit is not None:
            del self.inheritance[old]
            self.inheritance[new] = oldinherit
        self.__raw = dict(zip(sections, datas))
        return True

    def update(self,
               section: str,
               entries: INISection,
               inherit: Optional[str] = None):
        """To update (or append) a section with given infos."""
        if section not in self.__raw:
            self.__raw[section] = entries
        else:
            self.__raw[section].update(entries)
        if inherit is not None:
            self.inheritance[section] = inherit


class INIParser:
    """To read from a specific INI tree, or write to a single INI file."""
    @staticmethod
    def __merge(target: INIClass, source: INIClass):
        target.header.update(source.header)
        for section in source:
            target.update(section, source[section],
                          source.inheritance.get(section))

    def __set_header(self, doc: INIClass, stream: BytesIO):
        header = self.__read_entries(stream)
        if not doc.header:
            doc.header = header
            return
        last = list(doc.keys())[-1]
        for k, v in header._items_raw():
            if not k.startswith(';'):
                doc.header.update(k=v)
                continue
            doc[last]._append_line_comment(v)

    # at least "stack" works well.
    # queue with producer-consumer model may brings little (or even no)
    # performance improvement.
    def dfsWalk(self, rootini_path) -> INIClass:
        """Try to traversal and read an INI [#include] tree.

        Hint:
            This method works with two assumption below ensured:
            - ALL ini paths are based on a common parent directory,
              like `D:/yr_Ares/` in the following paths:
                - `D:/yr_Ares/rulesmd.ini`,
                - `D:/yr_Ares/rules_hotfix.ini`,
                - `D:/yr_Ares/Includes/rules_GDI.ini`.
            - INIs should ALL be readable, without encrypted, or mix packed.

            If an ini file is NOT FOUND, or NOT READABLE,
            then a `UserWarning` will be given and the file will be skipped.
        """
        rootdir, stack = split(rootini_path)[0], [rootini_path]
        ret = INIClass()
        while len(stack) > 0:
            try:
                root = self.read(stack.pop())
            except OSError as e:
                warnings.warn(f"INI tree may not correct: \n  {e}")
                continue
            merger = Thread(target=self.__merge, args=(ret, root),
                            daemon=True)
            merger.start()
            if '#include' in root:
                _ = ThreadPool(len(root['#include']))
                includes = _.map(lambda x: join(rootdir, x),
                                 root['#include'].values())
                _.close()
                _.join()
                includes.reverse()
                stack.extend(includes)
            merger.join()
        return ret

    # in case we get bytes from file buffer ORDERLY,
    # implementing coroutines may not be very effective.
    def read(self, ini_path) -> INIClass:
        """Read from a single C&C ini."""
        ret, parser = INIClass(), None
        with open(ini_path, 'rb') as fp:
            buffer = b''
            while (i := fp.readline()) or buffer:
                if i and not i.strip().startswith(b'['):
                    buffer += i
                    continue
                if not (buffer := buffer.strip()):
                    buffer = i
                    continue
                if parser is not None:
                    parser.join()
                parser = Thread(
                    target=(self.__read_section if buffer.startswith(b'[')
                            else self.__set_header),
                    args=(ret, BytesIO(buffer)), daemon=True)
                parser.start()
                buffer = i
        return ret

    def __read_section(self, doc: INIClass, stream: BytesIO):
        section = self.__decode_str(stream, b']', start=b'[')
        inherit = summary = None
        _next = stream.read(1)
        if _next == b':':
            inherit = self.__decode_str(stream, b']', start=b'[')
            _next = stream.read(1)
        if _next != b'\n':
            summary = self.__decode_str(
                stream, b'\n', buffer_init=_next, trim=True)
        entries = self.__read_entries(stream)
        if summary is not None and summary != '':
            entries.summary = summary
        doc.update(section, entries, inherit)

    def __read_entries(self, stream: BytesIO) -> INISection:
        entries = INISection()
        while i := stream.read(1):
            entry = self.__decode_str(
                stream, b'\n', buffer_init=i).rstrip()
            try:
                key, raw_value = entry.split('=', 1)
            except ValueError:
                entries._append_line_comment(entry)
                continue
            if (key := key.strip()) == '':
                continue
            if key.startswith(';'):
                entries._append_line_comment(f"{key}={raw_value}")
                continue
            entries[key] = raw_value.split(';', 1)[0].strip()
            if key == '+':
                key = f"+{entries._keydiff - 1}"
            comment = raw_value.replace(entries[key], '', 1)
            if comment.strip() != '':
                entries._add_inline_comment(key, comment)
        return entries

    @staticmethod
    def __decode_str(stream: BytesIO, *ends: bytes,
                     buffer_init=b'', start=None, trim=False) -> str:
        while i := stream.read(1):
            if start is not None and i == start:
                continue
            if i in ends:
                break
            buffer_init += i

        # too complex to make each codec have a try.
        codec = guess_codec(buffer_init)[0]
        try:
            buffer_init = buffer_init.decode(
                'utf-8' if codec is None or codec['confidence'] < 0.8
                else codec['encoding'])
        except UnicodeDecodeError:
            buffer_init = buffer_init.decode('gbk')

        if trim:
            buffer_init = buffer_init.strip()
        return buffer_init

    @staticmethod
    def __write_entries(fp: TextIOWrapper,
                        entries: INISection,
                        pairing: str,
                        blankline: int):
        for k, v in entries._items_raw():
            if str.startswith(k, ';'):
                fp.write(f'{str.replace(v[1], '=', pairing)}\n')
                continue
            fp.write(f'{k}{pairing}')
            if len(v) == 1:
                fp.write(f"{v[0]}\n")
            else:
                fp.write(f"{v[0]}{v[1]}\n")
        fp.write("\n" * blankline)

    @staticmethod
    def __write_section_decl(fp: TextIOWrapper,
                             section: str,
                             summary: str,
                             inherit: Optional[str]):
        fp.write(f'[{section}]')
        if inherit is not None:
            fp.write(f':[{inherit}]')
        if summary:
            fp.write(summary)
        fp.write('\n')

    @staticmethod
    def write(doc: INIClass, ini_path, encoding='utf-8', *,
              pairing='=', blankline=1):
        """Save as a C&C ini. (needs `await`)

        Args:
            pairing: how to connect key with value?
            blankline: how many lines between sections?
        """
        with open(ini_path, 'w', encoding=encoding) as fp:
            INIParser.__write_entries(fp, doc.header, pairing, blankline)
            for k, v in doc.items():
                INIParser.__write_section_decl(
                    fp, k, v.summary, doc.inheritance.get(k))
                INIParser.__write_entries(fp, v, pairing, blankline)
