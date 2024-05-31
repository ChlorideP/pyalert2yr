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

from io import BytesIO, TextIOWrapper
from multiprocessing.pool import ThreadPool
from os.path import join, split
from threading import Thread
from typing import (ItemsView, Iterator, KeysView, List, MutableMapping,
                    Optional, Sequence, ValuesView)
from uuid import uuid1 as guid
from warnings import warn

from chardet import detect_all as guess_codec

__all__ = ['INIClass', 'INISection', 'INIParser']


class INISection(MutableMapping[str, Optional[str]]):
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
        self.__raw: MutableMapping[str, List[Optional[str]]] = {}
        self.__diff = 0
        self.summary: Optional[str] = None
        if pairs_to_import:
            self.update(pairs_to_import)

    @property
    def keyDiff(self):
        """To get know how many `+=` in the section.
        At least you won't have to guess key: `+?`"""
        return self.__diff

    def __setitem__(self, k: str, v: Optional[str]):
        if k == '+':
            k = '+%d' % self.__diff
            self.__diff += 1
        if k not in self:
            self.__raw[k] = [v]
        else:
            self.__raw[k][0] = v

    def __getitem__(self, key: str) -> Optional[str]:
        return self.__raw[key][0]

    def __delitem__(self, key: str) -> None:
        del self.__raw[key]

    def __len__(self) -> int:
        return len(self.__raw)

    def __iter__(self) -> Iterator:
        return iter(self.keys())  # shouldn't include comments' UUID.

    def __repr__(self) -> str:
        return self.__raw.__repr__()

    def keys(self) -> KeysView[str]:
        return (i for i in self.__raw.keys() if not i.startswith(';'))

    def values(self) -> ValuesView[Optional[str]]:
        return (self.__raw[k][0] for k in self.__raw.keys()
                if not k.startswith(';'))

    def items(self) -> ItemsView[str, Optional[str]]:
        return ((k, v[0]) for k, v in self.__raw.items()
                if not k.startswith(';'))

    def _update_raw(self, external: 'INISection'):
        return self.__raw.update(external.__raw)

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
        return self.__raw.__setitem__(key, INISection(value))

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
    def __sync_header(self, target: INIClass, header: INISection):
        if not target.header:
            target.header._update_raw(header)
            return
        _header = target.header
        if len(target.keys()) > 0:
            last = list(target.keys())[-1]
            _header = target[last]
        for k, v in header._items_raw():
            if not k.startswith(';'):
                target.header.update(k=v)
                continue
            _header._append_line_comment(v)

    def __set_header(self, doc: INIClass, stream: BytesIO):
        return self.__sync_header(doc, self.__read_entries(stream))

    def __merge(self, target: INIClass, source: INIClass):
        self.__sync_header(target, source.header)
        for section in source:
            target.update(section, source[section],
                          source.inheritance.get(section))

    def read(self, inipath, errmsg="INI tree may not correct: "):
        """Read from a single C&C ini.

        Hint:
            If an ini file is NOT FOUND, or NOT READABLE, then
            a `UserWarning` will be shown and `None` will be returned.

            You may have to instead call `_read`
            if you'd like to manually handle the `OSError`.
        """
        inidict = None
        try:
            inidict = self._read(inipath)
        except OSError as e:
            warn(f"{errmsg}\n  {e}")
        return inidict

    def readTree(self, rootpath, *subpaths, sequential=False) -> INIClass:
        """Try to read a sequence of inis, or DFS walk an INI include tree.

        CAUTIONS:
            - When `sequential` is `True`, the method would only read
            `rootpath` and `subpaths`, ignoring `[#include]` in each INI.

            - The `[#include]` DFS walk needs the assumption below ensured:
                - ALL ini paths are based on a common parent directory,
                like `D:/yr_Ares/` in the following paths:
                    - root `D:/yr_Ares/rulesmd.ini`,
                    - sub `D:/yr_Ares/rules_hotfix.ini`,
                    - sub `D:/yr_Ares/Includes/rules_GDI.ini`.
                - INIs should ALL be readable, without encrypted or mix packed.
        """
        ret = INIClass()
        rootdir, stack = split(rootpath)[0], [self.read(rootpath)]
        while len(stack) > 0:
            if (root := stack.pop()) is None:
                continue
            merger = Thread(target=self.__merge, args=(ret, root), daemon=True)
            merger.start()
            if sequential:
                subpaths = dict(zip(range(len(subpaths)), subpaths))
            elif '#include' in root:
                subpaths = root['#include']
            else:
                continue
            _ = ThreadPool(len(subpaths))
            rootincs = _.map(lambda x: self.read(join(rootdir, x)),
                             subpaths.values())
            _.close()
            _.join()
            rootincs.reverse()
            stack.extend(rootincs)
            merger.join()
        return ret

    def _read(self, inipath) -> INIClass:
        """Read from a single C&C ini.

        CAUTION:
            May raise `OSError`.
        """
        ret, parser = INIClass(), None
        with open(inipath, 'rb') as fp:
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
                key = f"+{entries.keyDiff - 1}"
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
                try:
                    fp.write(f'{str.replace(v[1], '=', pairing)}\n')
                except TypeError:
                    pass
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
    def write(doc: INIClass, inipath, encoding='utf-8', *,
              pairing='=', blankline=1):
        """Save as a C&C ini. (needs `await`)

        Args:
            pairing: how to connect key with value?
            blankline: how many lines between sections?
        """
        with open(inipath, 'w', encoding=encoding) as fp:
            INIParser.__write_entries(fp, doc.header, pairing, blankline)
            for k, v in doc.items():
                INIParser.__write_section_decl(
                    fp, k, v.summary, doc.inheritance.get(k))
                INIParser.__write_entries(fp, v, pairing, blankline)
