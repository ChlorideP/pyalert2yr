# -*- encoding: utf-8 -*-
# @File   : model.py
# @Time   : 2024/10/10 01:14:19
# @Author : Kariko Lin

# I would like to split since the original V1 (and V2)
# csf.py was in a mess.

import warnings
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Iterator, NamedTuple, Sequence


class CsfHead(NamedTuple):
    """Only for IO process."""
    version: int  # offset 04H, after CSF_TAG.
    numlabels: int
    numvalues: int
    unused: int
    language: int


# have to give up TypedDict as it may not stable in runtime,
# like missing keys in interactive console, when user instantiates.
@dataclass(kw_only=True)
class CsfVal:
    value: str
    extra: str | None = None


class CsfDocument(MutableMapping[str, CsfVal]):
    """提供最简单的键值对文本读写支持，但也兼容多值文本的存储。"""
    version = 3
    language = 0  # CsfLang.en_US

    def __init__(self) -> None:
        # str as label tag, list as values (or evals)
        self.__data: dict[str, list[CsfVal]] = {}
        # to maintain original keys for saving files
        self.__keyproxy: dict[str, str] = {}

    def __getitem__(self, key: str) -> CsfVal:
        """获取游戏实际使用的 CSF 值（也就是多值当中的第一个）。"""
        return self.__data[key.upper()][0]

    def __setitem__(
        self,
        key: str,
        value: CsfVal | Sequence[CsfVal] | str
    ) -> None:
        if key.upper() in self.__keyproxy:
            warnings.warn(
                f'文档已存在同名键值对"{key}: {self.__data[key.upper()]}"，'
                '请注意旧值将被覆盖。')
        self.__keyproxy[key.upper()] = key

        if isinstance(value, str):
            value = CsfVal(value=value)
        if isinstance(value, CsfVal):
            value = [value]
        else:
            warnings.warn(
                f'CSF 键 "{key}" 是多值字符串，'
                '请注意旧式的 CSF 编辑器将不兼容。')
        self.__data[key.upper()] = list(value)

    def __delitem__(self, key: str) -> None:
        del self.__data[key.upper()]
        del self.__keyproxy[key]

    def __iter__(self) -> Iterator[str]:
        return self.__data.__iter__()

    def __len__(self) -> int:
        return self.__data.__len__()

    def getAllValues(self, lbl: str) -> list[CsfVal]:
        """Get whole values list associated with given label."""
        return self.__data[lbl.upper()]

    def _items(self) -> zip[tuple[str, list[CsfVal]]]:
        """Iterate for each label and corresponding values list."""
        return zip(self.__keyproxy.values(), self.__data.values())

    @property
    def header(self) -> CsfHead:
        numstr = 0
        for i in self.__data.values():
            numstr += len(i)
        return CsfHead(
            self.version,
            len(self),
            numstr,
            0,
            self.language)
