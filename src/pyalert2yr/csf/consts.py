# -*- encoding: utf-8 -*-
# @File   : consts.py
# @Time   : 2024/10/10 01:15:56
# @Author : Kariko Lin

from enum import Enum


# may not really need.
class CsfLang(int, Enum):
    Universal = -1  # Ares implemented
    en_US = 0
    en_UK = 1
    de = 2  # German
    fr = 3  # French
    es = 4  # Spanish
    it = 5  # Italian
    jp = 6  # Japanese
    Jabberwockie = 7
    kr = 8  # Korean
    zh = 9  # Chinese
    # int gt 10 as Unknown.


SHIMAKAZE_SCHEMA = 'https://shimakazeproject.github.io/Schemas'


class CsfMark(str, Enum):
    IS_CSF = ' FSC'
    IS_LBL = ' LBL'
    IS_VAL = ' RTS'
    IS_EVAL = 'WRTS'
