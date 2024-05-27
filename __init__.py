# -*- encoding: utf-8 -*-
# @File   : __init__.py
# @Time   : 2023/11/14 20:01:52
# @Author : Chloride

import logging

from .formats.ini import INIClass, INISection, iniTreeDFSWalk
from .formats.csf import CsfDoc, CsfFileParser, CsfJsonV2Parser
from .map_split import splitMap, joinMap

__all__ = [
    'INIClass', 'INISection', 'iniTreeDFSWalk',
    'CsfDoc', 'CsfFileParser', 'CsfJsonV2Parser',
    'splitMap', 'joinMap'
]

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s: %(message)s')
