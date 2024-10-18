# -*- encoding: utf-8 -*-
# @File   : rw.py
# @Time   : 2024/10/10 01:15:59
# @Author : Kariko Lin

from .model import CsfDocument
from ..abstract import FileHandler


class InvalidCsfRecord(Exception):
    """To record errors when reading .CSF files."""
    pass


class CsfParser(FileHandler[CsfDocument]):
    ...


class CsfFileParser(CsfParser):
    ...


class CsfJsonV2Parser(CsfParser):
    ...


class CsfXmlParser(CsfParser):
    ...


class CsfLLangParser(CsfParser):
    """Due to complex implements of YAML signs,
    there is also LLF which is similar to YAML,
    but way more convenient for RA2 modders.

    Thanks to contribution of new lang file format:
    `Mr.L` & `TwinkleStar`."""
    def __init__(
            self,
            filename: str,
            encoding: str = "utf-8", *,
            yaml_compat: bool = False) -> None:
        super().__init__(filename)
        self._codec = encoding
