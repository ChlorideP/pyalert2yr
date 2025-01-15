# -*- encoding: utf-8 -*-
# @File   : model.py
# @Time   : 2024/10/10 00:57:10
# @Author : Kariko Lin

"""
Basically INI Structure with Inheritance support.

As for `[#include]`, just see `ini.parser`.
"""

from collections.abc import MutableMapping
from typing import Generator, Iterator, Sequence, TypedDict
from warnings import warn

# from ..abstract import T


class IniSectionProxy(MutableMapping[str, str]):
    """INI 小节字典。

    维护一个 INI 小节所有的键值对（含继承下来的），包括 Ares 的`+=`。
    但请注意：删、改父小节的键值，*实际并不会真正影响到父小节*。

    所有键值对均*应该*是`str: str`类型（哪怕值为空串），
    但由于 Python 的动态类型性质，运行时并不会对此作出限制。

    此外，`+=`会在内部转换为`__PyYR_0`的形式。
    当然最简便的方法还是直接用`self.to_type_list()`获取整个列表。
    """

    __PLUS_EQUAL_CNT = 0

    # basically we may find a sequence of inheritance links
    # and what the proxy does is that
    # merging those PARENT sections into one dict (read only to user),
    # and then provide a R/W access to dict of section itself.
    def __init__(
        self, section_name: str, /,
        this_dict: dict[str, str], *parent_dicts: dict[str, str]
    ) -> None:
        self._name = section_name
        # in case shared ptr to item of IniClass.__raw
        self._data: dict[str, str] = this_dict
        self.__parent: dict[str, str] = {}
        for i in parent_dicts:
            self.__parent.update(i)

    def __getitem__(self, key: str) -> str:
        if key in self._data:
            return self._data[key]
        elif key in self.__parent:
            return self.__parent[key]
        else:
            raise KeyError(key)

    # shall update in child section, since parent is merged and read-only.
    def __setitem__(self, key: str, value: str) -> None:
        if key == '+':
            key = f'__PyYR_{self.__PLUS_EQUAL_CNT}'
            self.__PLUS_EQUAL_CNT += 1
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
        # samely, keys in parent are unable to del
        # have to override.
        if key in self.__parent:
            warn(
                f'该小节存在继承关系且父小节仍然存在 "{key}" 词条。'
                'Phobos 文档指出，即便在这里删除了该词条，游戏仍会读取父小节那里的值。'
            )

    def __contains__(self, key: object) -> bool:
        return key in self._data or key in self.__parent

    def __len__(self) -> int:
        return len(self.to_dict())

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __str__(self) -> str:
        return f"[{self._name}]"

    def __repr__(self) -> str:
        return '[%s] { .cnt = %d }' % (self._name, len(self._data))

    def to_dict(self) -> dict[str, str]:
        """合并继承关系，获取该小节所有实际的键值对。"""
        mrg = self.__parent.copy()
        mrg.update(self._data)
        return mrg

    def to_type_list(self) -> Sequence[str]:
        """获取该小节的*不重复*值表。主要用于“注册表”。

        注：“注册表”是国人 modder 的习惯叫法。
        比如`GACNST`属于建筑，“注册”在`BuildingTypes`小节里。
        """
        ret: dict[str, None] = {}
        for i in self.values():
            ret.setdefault(i, None)
        return list(ret.keys())

    # 说起来一个小节还应该有什么操作（


class IniSectionMeta(TypedDict):
    section: str
    pairs: dict[str, str]
    parents: list[str] | None


class IniClass(MutableMapping[str, IniSectionProxy]):
    """INI 文件（或树）表示。支持以下形式的 INI 小节和键值对（不含注释）：

        ```ini
        key = val  ; 使用 self.header 访问游离的键值对。

        [section]
        key233 = val666
        [section]:[parent]  ; Ares 继承
        key233 = val114514
        [Section]
        $Inherits = section,parent  ; Phobos 继承
        ```

    另注：增删改继承关系请使用`self.inherits`字典。
    Phobos 设于小节的`$Inherits`键仅在读写文件时参与处理。
    """
    # in case I'd like to consider two list model
    # while one stores section declarations, another stores real dicts.
    # those key-value dicts may get accessed by Proxy pointers.
    def __init__(self) -> None:
        self.__header: dict[str, str] = {}
        self.__raw_dicts: dict[str, dict[str, str]] = {}
        self.__inherits: dict[str, list[str]] = {}

    @property
    def inherits(self) -> dict[str, list[str]]:
        """`IniClass`实际维护的继承关系表。"""
        return self.__inherits  # unable to replace ptr, just R/W keys.

    @property
    def header(self) -> IniSectionProxy:
        """位于文件头部的，不属于任何小节的游离键值对。"""
        # section declaration is impossible to contain ';'.
        return IniSectionProxy('; PyYR_Maintained', self.__header)

    def __getitem__(self, key: str) -> IniSectionProxy:
        if key not in self:
            raise KeyError(key)
        return IniSectionProxy(
            key,
            self.__raw_dicts[key],
            *(dic for _, dic in self.__traverse_parents(key)))

    def __setitem__(
        self,
        key: str,
        value: IniSectionProxy | dict[str, str]
    ) -> None:
        self.__raw_dicts[key] = (
            value.to_dict()
            if isinstance(value, IniSectionProxy)
            # shouldn't keep ptr to external dict in key setting operation.
            else value.copy()
        )

    def __delitem__(self, key: str) -> None:
        del self.__raw_dicts[key]
        if key in self.__inherits:
            del self.__inherits[key]

    def __contains__(self, key: object) -> bool:
        return key in self.__raw_dicts

    def __len__(self) -> int:
        return len(self.__raw_dicts)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__raw_dicts)

    def _get_meta(self, key: str) -> IniSectionMeta:
        """for IniParser.write()."""
        return IniSectionMeta(
            section=key,
            pairs=self.__raw_dicts[key],
            parents=self.__inherits.get(key)
        )

    def _set_meta(self, meta: IniSectionMeta) -> None:
        """for IniTreeParser reading."""
        if meta['section'] not in self.__raw_dicts:
            self.__raw_dicts[meta['section']] = meta['pairs'].copy()
        else:
            self.__raw_dicts[meta['section']].update(meta['pairs'])
        if meta['parents']:  # not None not empty
            self.inherits[meta['section']] = meta['parents']

    def __traverse_parents(self, key: str) -> Generator[tuple[
        str,
        dict[str, str]
    ]]:
        stack = self.__inherits.get(key, [])
        stack.reverse()
        while stack:
            i = stack.pop()
            if i not in self:
                warn(f'[{key}] 存在父小节 "{i}"，但当前文档中找不到它。')
                continue
            yield i, self.__raw_dicts[i]
            stack.extend(reversed(self.__inherits.get(i, [])))
        return

    def setdefault(
        self, key: str, default: IniSectionProxy | dict[str, str],
    ) -> IniSectionProxy:
        if key not in self:
            self.__raw_dicts[key] = (
                default._data.copy()
                if isinstance(default, IniSectionProxy)
                else default
            )
        return self[key]

    def find_section_mro(self, section: str) -> list[str]:
        """遍历当前实例中指定 INI 小节的有效继承关系
        （按 Phobos 介绍的深度优先顺序排列）。

        注意：遍历结果*不代表*实际游戏读到的继承关系。
        由于本项目不参与 MIX 包的处理，实例代表的 INI 树很可能*并不完整*，继承关系亦然。
        """
        return [name for name, _ in self.__traverse_parents(section)]

    # 一个 INI 文件（或者 INI 树）还要有什么操作捏？
