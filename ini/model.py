# -*- encoding: utf-8 -*-
# @File   : model.py
# @Time   : 2024/10/10 00:57:10
# @Author : Kariko Lin

"""
Basically INI Structure with Ares Inheritance support.

I MAY NOT CONSIDER PHOBOS DFS `$Inherit`,
which is fxxking harder to merge (when init proxies).
"""

from collections.abc import MutableMapping


class IniSectionProxy(MutableMapping[str, str]):
    # basically we may find a sequence of inheritance links
    # and what the proxy does is that
    # merging those PARENT sections into one dict (read only to user),
    # and then provide a R/W access to dict of section itself.
    ...


class IniClass(MutableMapping[str, IniSectionProxy]):
    # in case I'd like to consider two list model
    # while one stores section declarations, another stores real dicts.
    # those key-value dicts may get accessed by Proxy pointers.
    ...
