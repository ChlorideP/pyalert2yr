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

import logging
from collections.abc import MutableMapping
from io import StringIO
from multiprocessing.pool import ThreadPool
from os.path import join, split
from queue import Queue
from threading import Thread
from typing import Callable, Iterator, Mapping, Optional, Sequence
from uuid import uuid1 as guid
from warnings import warn

from chardet import detect as guess_codec

__all__ = ['INIClass', 'INISection', 'INIParser']


class INISection(MutableMapping[str, Optional[str]]):
    """... is a dict, just maintaining pairs, within `+=`.

    All above SHOULD be `str: str | None`,
    however in runtime we wouldn't limit that much.

    Note: you may have to do `toTypeList()` conversion
    to get access to `+=` items.
    """
    def __init__(self, pairs_to_import: Mapping[str, str] = None):
        """Init a dictionary of ini entries included by section."""
        self.__raw: MutableMapping[str, Optional[str]] = {}
        if pairs_to_import:
            self.update(pairs_to_import)

    def __setitem__(self, k: str, v: Optional[str]):
        if k == '+':
            k = '%d' % int(str(guid())[0:8], 16)
        self.__raw[k] = v

    def __getitem__(self, key: str) -> Optional[str]:
        return self.__raw[key]

    def __delitem__(self, key: str) -> None:
        del self.__raw[key]

    def __len__(self) -> int:
        return len(self.__raw)

    def __iter__(self) -> Iterator:
        return iter(self.__raw)

    def __repr__(self) -> str:
        return self.__raw.__repr__()

    def find(self, key):
        """Deprecated now. Try `INIClass.findKey()`."""
        raise NotImplementedError("The V1 APIs are now unsupported.")

    def get(self, key, converter: Callable[[str], object] = str, default=None):
        if converter is list:
            return self.getlist(key)
        elif converter is bool:
            return self.getbool(key)
        elif key not in self:
            return default
        else:
            return converter(self[key])

    # lazy to implement auto converter. just manual.
    def getbool(self, key):
        return (None if key not in self
                else self[key] and self[key][0].lower() in ('1', 'y', 't'))

    def getlist(self, key):
        return () if key not in self else self[key].split(',')

    def toTypeList(self):
        """Collects a *ordered* values sequence, with elements *unique*.

        Mainly serves for the "type list", i.e.
        ```ini
        [BuildingTypes]
        0 = GACNST  ; like, the left INDEX and the right TYPE_DECL.
        ```
        """
        ret = []
        for i in self.__raw.values():
            if i is None or i == '':
                continue
            if i in ret:
                continue
            ret.append(i)
        return ret

    def sortPairs(self, key=None, *, reverse=False):
        """
        Sort the key-value pairs in ascending order, just like sorted().

        Hint:
            Each pair will be packed into a (key, value) tuple.
            You may find it easy to use interger index.

        Examples:
            - by value length:
                `self.sortPairs(key=lambda x: len(x[1]))`
            - by keys (make sure they are comparable):
                `self.sortPairs(key=lambda x: x[0])
        """
        keys = sorted(self.__pairs.items(), key=key, reverse=reverse)
        pairs = {k: self.__pairs.get(k) for k in keys}
        self.__pairs = pairs


class INIClass(MutableMapping[str, INISection]):
    """... is simply a group of dict,
    representing a whole INI file (or tree).
    """
    def __init__(self):
        """Init an empty INI document."""
        self.__raw: MutableMapping[str, INISection] = {}
        self.inherits = {}
        # still keep this header to
        # maintain pairs not belong to any section.
        self.header = INISection()

    def __getitem__(self, key: str) -> INISection:
        return self.__raw.__getitem__(key)

    def __setitem__(self, key: str, value: INISection) -> None:
        return self.__raw.__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        if key in self.inherits:
            del self.inherits[key]
        return self.__raw.__delitem__(key)

    def __iter__(self) -> Iterator:
        return self.__raw.__iter__()

    def __len__(self) -> int:
        return self.__raw.__len__()

    def findKey(self, section, key,
                recursive=False) -> Sequence[Optional[str]]:
        """Start searching from a specific section.

        If key not found, inheritance detected and `recursive` is True,
        then go further, until the condition broken.

        Returns:
            - if found: a tuple within
                - section, which contains the key, its name
                - the corresponding value
            - if not found: a `(None, None)` tuple.
            - if tracking stopped due to `recursive=False`: a tuple within
                - section name or `None` (as mentioned above)
                - `None`
        """
        value = None
        while True:
            if key in self[section]:
                value = self[section][key]
                break
            section = self.inherits.get(section)
            if not recursive or section is None:
                break
        return section, value

    def getTypeList(self, section):
        """Deprecated now. Try `self[section].toTypeList()` instead."""
        warn("The V1 APIs are now deprecated.", DeprecationWarning)
        if section not in self:
            return ()
        else:
            return self[section].toTypeList()

    def setdefault(self, section, inherit: str = None):
        """If `section` not in self, then add it;
        if `inherit` is not None, then add (or override) it."""
        if section not in self.__raw:
            self.__raw[section] = INISection()
        if inherit is not None:
            self.inherits[section] = inherit

    def clear(self):
        self.inherits.clear()
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
        oldinherit = self.inherits.get(old)
        if oldinherit is not None:
            del self.inherits[old]
            self.inherits[new] = oldinherit
        self.__raw = dict(zip(sections, datas))
        return True

    def update(self, another: 'INIClass'):
        """To merge `another` into self."""
        self.header.update(another.header)
        self.inherits.update(another.inherits)
        for decl, data in another.items():
            self.add(decl, data)


class INIParser:
    def __init__(self) -> None:
        self.mergequeue = Queue()

    def __merge(self, ret: INIClass):
        while True:
            subini = self.mergequeue.get()
            ret.update(subini)

    def read(self, inipath, errmsg="INI tree may not correct: "):
        """Read from a single C&C ini.

        Hint:
            If an ini file is NOT FOUND, or NOT READABLE, then
            a `UserWarning` will be shown and `None` will be returned.

            You may have to instead call `_read`
            if you'd like to manually handle the `OSError`.
        """
        try:
            with open(inipath, 'rb') as fp:
                raw = fp.read()
        except OSError as e:
            logging.warning(f"{errmsg}\n  {e}")
            return None

        try:
            codec = guess_codec(raw)
            if codec is None or codec['confidence'] < 0.8:
                codec = {'encoding': 'utf-8'}
            raw = raw.decode(codec)
        except UnicodeDecodeError:
            raw = raw.decode('gbk')
        return self._read(StringIO(raw))

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
        # use producer-consumer model instead of sequential creating thread.
        merger = Thread(target=self.__merge, args=(ret,), daemon=True)
        merger.start()
        while len(stack) > 0:
            if (root := stack.pop()) is None:
                continue
            self.mergequeue.put(root)
            if not sequential and '#include' in root:
                subpaths = root['#include'].values()
            if not subpaths:
                continue
            pool = ThreadPool(len(subpaths))
            rootincs = pool.map(lambda x: self.read(join(rootdir, x)),
                                subpaths)
            pool.close()
            pool.join()
            rootincs.reverse()
            stack.extend(rootincs)
        merger.join()
        return ret

    def _read(self, buffer: StringIO) -> INIClass:
        """Read from a single C&C ini chars buffer.

        CAUTION:
            May raise `OSError`.
        """
        ret = INIClass()
        this_sect = ret.header
        while (i := buffer.readline()):
            if i[0] == '[':
                section = dict(zip(
                    ['decl', 'base'],
                    [j.strip()[1:-1] for j in i[:i.find(';')].split(':')]))
                ret.setdefault(section['decl'], section.get('base'))
                this_sect = ret[section['decl']]
            elif '=' in i:
                key, val = i.split('=', 1)
                key = key.strip()
                if ';' not in key:
                    this_sect[key] = val.split(';')[0].strip()
        return ret

    @staticmethod
    def write(doc: INIClass, inipath, encoding='utf-8', *,
              pairing='=', blankline=1):
        """Save as a C&C ini.

        Args:
            pairing: how to connect key with value?
            blankline: how many lines between sections?
        """
        with open(inipath, 'w', encoding=encoding) as fp:
            for key, val in doc.header.items():
                fp.write(f'{key}{pairing}{val}\n')
                fp.write("\n" * blankline)
            for sect, data in doc.items():
                fp.write(f'[{sect}]')
                if (inherit := doc.inherits.get(sect)) is not None:
                    fp.write(f':[{inherit}]')
                fp.write('\n')
                for key, val in data.items():
                    fp.write(f'{key}{pairing}{val}\n')
                    fp.write("\n" * blankline)
