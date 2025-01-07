# -*- encoding: utf-8 -*-
# @File   : __init__.py
# @Time   : 2024/10/10 01:16:53
# @Author : Kariko Lin

from .model import IniSectionProxy, IniClass
from .parser import IniParser


# 讲道理在不保证 INI 树完整的情况下，我也不好说什么实现更合理一些。
# 弄继承还要考虑 INI 默认值问题。只是`<undefined>`可能并不合理。
# 但我也没什么更好的办法。
