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

from io import BufferedReader
import warnings
from os.path import join, split
from queue import Queue
from threading import Thread
from typing import AnyStr, ItemsView, Iterator, KeysView, List, ValuesView
from typing import MutableMapping, Optional, Sequence
from uuid import uuid1 as guid

from chardet import detect_all as guess_codec

__all__ = ['INIClass', 'INISection', 'iniTreeDFSWalk']


class INISection(MutableMapping):
    """In case, INISection is just a dict like:
    ```python
    {
        key: value,
        key2: [value, comment],
        comment_guid: [None, line_comment]
    }
    ```
    To get things easier, key-value access would ignore comments.

    And be cautious, INISection wouldn't do any type validation
    when operating key-values.
    """
    def __init__(self, **pairs_to_import):
        """Init a dictionary of ini entries included by section."""
        self.__raw: MutableMapping[str, List[Optional[AnyStr]]] = {}
        self.summary: Optional[AnyStr] = None
        if pairs_to_import:
            self.update(pairs_to_import)

    def __setitem__(self, k: str, v: str):
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

    def keys(self) -> KeysView:
        return (i for i in self.__raw.keys() if not i.startswith(';'))

    def values(self) -> ValuesView:
        return (i[0] for i in self.__raw.values() if i is not None)

    def items(self) -> ItemsView:
        return ((k, v[0]) for k, v in self.__raw.items()
                if not k.startswith(';'))

    def _append_line_comment(self, comment: str):
        self.__raw[f'{str(guid())}'] = [None, comment]

    def _add_inline_comment(self, key, comment):
        raw_val_list = self.__raw[key]
        if len(raw_val_list) > 1:
            raw_val_list[1] = comment
        else:
            raw_val_list.append(comment)


class INIClass(MutableMapping):
    """A INIClass is simply a group of dict like:
    ```python
    header = {
        ";a8a8a8a8": [None, "ddtms"],
        "ExtConfig": ["~/Desktop/wland/config.yaml"]
    }
    entries = {
        "InfantryTypes": {  # INISection in fact.
            '0': ['E1'],
            '1': ['E2', 'CNM'],
            ';c412bf52': [None, 'ssks']
        },
        "E2": {}
    }
    inheritance = {
        "E2": "E1"  # keys of E1 would copy to E2 ingame.
    }
    ```
    """
    def __init__(self):
        """Init an empty INI document."""
        self.__readqueue = Queue()
        self.__diff = 0
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
        '''Collects a ordered sequence of the "type" list section,
        like `BuildingTypes`, with elements unique.
        '''
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
        """
        Rename a section.

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

    def write(self, filename, encoding='utf-8',
              *, pairing='=', commenting='; ', blankline=1):
        """
        Save as a C&C ini.

        Args:
            pairing: how to connect key with value?
            commenting: how the individual comment lines start with?
                (ps: the inline comments won't be affected)
            blankline: how many lines between sections?
        """

        def writeEntries():
            for k, v in entries.items():
                if str.startswith(k, ';'):
                    fp.write(f'{commenting}{v[1]}\n')
                    continue
                fp.write(f'{k}{pairing}')
                if len(v) == 1:
                    fp.write(f"{v[0]}\n")
                else:
                    fp.write(f"{v[0]}{v[1]}\n")
            fp.write("\n" * blankline)

        def writeSection():
            fp.write(f'[{section}]')
            if inherit is not None:
                fp.write(f':[{inherit}]')
            if entries.summary:
                fp.write(f'{entries.summary}')
            fp.write('\n')

        with open(filename, 'w', encoding=encoding) as fp:
            entries = self.header
            writeEntries()
            for k, v in self.__raw.items():
                section, entries = k, v
                inherit = self.inheritance.get(k)
                writeSection()
                writeEntries()

    def __read_file(self):
        """
        Load C&C ini(s) into buffer.
        """
        while True:
            fp: BufferedReader = self.__readqueue.get()
            section = self.header
            while i := fp.read(1):
                if i == b'[':
                    section = self.__read_section(fp)
                elif i == b';':
                    section._append_line_comment(self.__decode_str(fp, b'\n'))
                elif i == b'\n':
                    continue
                else:
                    self.__read_entry(
                        section, self.__decode_str(fp, b'\n', buffer_init=i))
            fp.close()
            self.__readqueue.task_done()

    @staticmethod
    def __decode_str(stream: BufferedReader,
                     *ends: bytes,
                     buffer_init=b'',
                     start=None,
                     trim=False) -> str:
        while i := stream.read(1):
            if start is not None and i == start:
                continue
            if i in ends:
                break
            buffer_init += i

        # too complex to make each one have a try.
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

    def __read_section(self, stream: BufferedReader) -> INISection:
        cur = self.__decode_str(stream, b']')
        if cur not in self.__raw:
            self.__raw[cur] = ret = INISection()
        else:
            ret = self.__raw[cur]

        _next = stream.read(1)
        if _next == b':':
            self.inheritance[cur] = self.__decode_str(stream, b']', start=b'[')
        if _next != b'\n':
            summary = self.__decode_str(
                stream, b'\n', buffer_init=_next, trim=True)
            if summary != '':
                ret.summary = summary
        return ret

    def __read_entry(self, section: INISection, entry: str):
        try:
            key, raw_value = entry.split('=', 1)
        except ValueError:
            section._append_line_comment(entry)
            return
        key = key.strip()
        if key == '':
            return
        if key == '+':
            key = f'+{self.__diff}'
            self.__diff += 1
        section[key] = raw_value.split(';', 1)[0].strip()
        comment = raw_value.replace(section[key], '', 1)
        if comment.strip() != '':
            section._add_inline_comment(key, comment)

    def read(self, *filepaths):
        """
        Read (a group of) C&C ini(s).

        Args:
            *inis: inis to be loaded.
        """
        Thread(target=self.__read_file, daemon=True).start()
        for i in filepaths:
            try:
                fp = open(i, 'rb')
                self.__readqueue.put(fp)
            except OSError as e:
                warnings.warn(f"INI tree may load incorrectly: {e}")
                continue
        self.__readqueue.join()


def iniTreeDFSWalk(root) -> list:
    """
    To fetch all available INIs in the `[#include]`, for `INIClass` reading.

    Hint:
        - We assume the inis are all based on the directory of root.
        - The sequence returned may NOT CORRECT,
        but surely be FULL (nobody skipped).
        - The reading process is STILL SLOW when reading A SINGLE INI FILE,
        which is unfortunately how this function does (one by one),
        since the `[#include]` may be partial unless a whole file parsed.

    Args:
        root: the beginning ini file path of traversal. i.e. './rulesmd.ini'.

    Returns:
        A list of inis, with the beginning ini placed in [0].
    """
    # In fact, this is just pre-order traversal of the sub ini tree.
    doc = INIClass()
    ret, stack = [], [root]
    rootdir = split(root)[0]

    while len(stack) > 0:
        root = stack.pop()
        doc.read(root)
        ret.append(root)
        if '#include' in doc:
            rootinc = [join(rootdir, i)
                       for i in doc['#include'].values()]
            rootinc.reverse()
            stack.extend(rootinc)
        doc.clear()

    # ret.pop(0)  # remove the initial root.
    return ret
