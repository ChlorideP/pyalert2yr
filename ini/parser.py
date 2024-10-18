# -*- encoding: utf-8 -*-
# @File   : rw.py
# @Time   : 2024/10/10 01:04:45
# @Author : Kariko Lin

from os import PathLike

from .model import IniClass
from ..abstract import FileHandler


class IniParser(FileHandler[IniClass]):
    def __init__(self, filename: str, encoding: str | None = None):
        super().__init__(filename)
        self._codec = encoding

    def read(self) -> IniClass:
        return NotImplemented

    def readTree(
            self,
            *subinis: str | PathLike[str],
            sequential: bool = True) -> IniClass:
        """Note: this method may not need specifying `encoding`,
        since `chardet` would guess each file.
        """
        return NotImplemented

    def write(self, instance: IniClass) -> None:
        """Note: for ini loaded by `readTree()`,
        the output would be ONLY ONE ini file."""
        ...
