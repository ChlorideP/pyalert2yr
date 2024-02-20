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
from chardet import detect
from io import TextIOWrapper
from os.path import join, split
from typing import Callable, Iterable, MutableMapping

__all__ = ['INIClass', 'INISection', 'scanINITree']


class INISection(MutableMapping):
    @staticmethod
    def __bool_conv(val: str):
        return val[0].lower() in ('1', 'y', 't')

    @staticmethod
    def __list_conv(val: str):
        return val.split(',')

    __VAL_CONV = {
        True: "yes",
        False: "no",
        None: ""
    }
    __CONVERTER = {
        bool: __bool_conv,
        list: __list_conv
    }

    def __init__(self, section: str, _super=None, **kwargs):
        self._name = section
        self.parent = _super
        self.__pairs = {}
        if kwargs:
            self.update(kwargs)

    def __setitem__(self, k, v):
        if isinstance(v, (list, tuple, set)):
            v = ','.join(map(str, v))
        self.__pairs[str(k)] = self.__VAL_CONV.get(v, str(v))

    def __delitem__(self, k):
        del self.__pairs[k]

    def __getitem__(self, key):
        return self.__pairs[key]

    def __contains__(self, item):
        return item in self.__pairs

    def __len__(self) -> int:
        return len(self.__pairs)

    def __iter__(self):
        return iter(self.__pairs)

    def __repr__(self):
        _info = "[%s]" % self._name
        if self.parent:
            _info += ":[%s]" % self.parent
        return _info

    def __str__(self):
        return self._name

    def find(self, key):
        """
        Try to search the section who contains key, recursively.

        Returns:
            `INISection` if found, otherwise `str` or `None`.
        """
        sect = self
        while isinstance(sect, INISection):
            if key in sect.__pairs:
                break
            sect = sect.parent
        return sect

    def get(self, key, converter: Callable[[str], object] = str, default=None):
        """
        Returns converted value if key is reachable (i.e.
        could be found in current context), otherwise `default`.
        """
        target = self.find(key)
        if isinstance(target, INISection):
            value: str = target[key]
            if not value:  # null value
                return None
            else:
                return self.__CONVERTER.get(converter, converter)(value)
        else:
            return default

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

    def _update_myself(self, section):
        if not isinstance(section, INISection):
            raise TypeError(type(section))
        self._name = section._name
        self.parent = section.parent
        self.__pairs = dict(section.items())


class INIClass(Iterable):
    __diff = 0  # for multiple inis processing

    def __init__(self):
        """Initialize an empty INI structure."""
        self.__raw: dict[str, INISection] = {}

    def __getitem__(self, key):
        return self.__raw[key]

    def __setitem__(self, key, value):
        key = str(key)
        if key not in self.__raw:
            self.__raw[key] = INISection(key)

        if isinstance(value, INISection):
            self.__raw[key]._update_myself(value)
        else:
            self.__raw[key].update(value)

    def __delitem__(self, key):
        del self.__raw[key]

    def __contains__(self, key):
        return key in self.__raw

    def __len__(self):
        return len(self.__raw)

    def __iter__(self):
        return iter(self.__raw)

    def getTypeList(self, section):
        if section not in self.__raw:
            return tuple()

        ret = []
        for i in self.__raw[section].values():
            if i not in ret and i != '':
                ret.append(i)
        return ret

    def clear(self):
        return self.__raw.clear()

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
        self[old]._name = new

        # Everything may look automatic if I change it list[INISection].
        # However I'm too lazy to do that.
        sectNames = [i._name for i in self._sections]
        sects = list(self._sections)
        self.__raw = dict(zip(sectNames, sects))

        return True

    @property
    def _section_heads(self):
        return self.__raw.keys()

    @property
    def _sections(self):
        return self.__raw.values()

    def writeStream(self, fp: TextIOWrapper, pairing='=', blankline=1):
        """
        Save as a C&C ini.

        Args:
            pairing: how to connect key with value?
            blankline: how many lines between sections?
        """
        for i in self.__raw.values():
            fp.write(f"{repr(i)}\n")
            for key, value in i.items():
                fp.write(f"{key}{pairing}{value}\n")
            fp.write("\n" * blankline)

    def readStream(self, stream: TextIOWrapper):
        """
        Load a C&C ini.
        """
        while True:
            i = stream.readline()
            if len(i) == 0:
                break

            if i[0] == '[':
                curSect = [j.strip()[1:-1]
                           for j in i.split(';')[0].split(':')]
                this = self.__raw.get(curSect[0])
                if this is None:
                    base = (None if len(curSect) == 1
                            else self.__raw.get(curSect[1], curSect[1]))
                    this = INISection(curSect[0], base)
                    self.__raw[curSect[0]] = this
            elif '=' in i:
                j = i.split('=', 1)
                j[0] = j[0].strip()

                if ';' not in j[0]:
                    key = f'+{self.__diff}' if j[0] == '+' else j[0]
                    self.__diff += 1

                    this[key] = j[1].split(';')[0].strip()

    def read(self, *inis, encoding=None):
        """
        Read C&C inis one by one.

        Args:
            *inis: inis included by `self`.
            encoding: def to auto (None).

        Hint:
            - The auto encoding detect may not be effective.
            It's recommended to just consider `gb18030` or `utf-8`.
        """
        for i in inis:
            if encoding is None:
                with open(i, 'rb') as fs:
                    encoding = detect(fs.read())['encoding']
            try:
                with open(i, 'r', encoding=encoding) as fs:
                    self.readStream(fs)
            except OSError as e:
                warnings.warn(
                    f'INI tree incorrect - {e.strerror}: {e.filename}')


def scanINITree(root) -> list:
    """
    To fetch all available INIs in the `[#include]`, for `INIClass` reading.

    Hint:
        - We assume the inis are all based on the directory of root.
        - Files that get `UserWarning` will be skipped,
        which means the result may not be always correct.

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

        try:
            doc.read(root)
        except OSError as e:
            warnings.warn(f'{e.strerror}: {e.filename}')
            continue
        except UnicodeDecodeError as e:
            warnings.warn(
                f'Includes skipped: DecodeError({e.encoding}) - {root}')
            ret.append(root)
        else:
            ret.append(root)

        if '#include' in doc:
            rootinc = [join(rootdir, i)
                       for i in doc['#include'].values()]
            rootinc.reverse()
            stack.extend(rootinc)
        doc.clear()

    # ret.pop(0)  # remove the initial root.
    return ret
