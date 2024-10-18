# -*- encoding: utf-8 -*-
# @File   : model.py
# @Time   : 2024/10/10 01:14:19
# @Author : Kariko Lin

# I would like to split since the original V1 (and V2)
# csf.py was in a mess.

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import NamedTuple


class CsfHead(NamedTuple):
    """Only for IO process."""
    version: int  # offset 04H, after CSF_TAG.
    numlabels: int
    numvalues: int
    unused: int
    language: int


# have to give up TypedDict as it may not stable in runtime,
# like missing keys in interactive console, when user instantiates
@dataclass(kw_only=True)
class CsfVal:
    value: str
    extra: str | None = None


class CsfDocument(MutableMapping[str, CsfVal]):
    ...  # TODO: refactor structure
