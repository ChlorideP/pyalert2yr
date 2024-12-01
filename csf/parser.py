# -*- encoding: utf-8 -*-
# @File   : rw.py
# @Time   : 2024/10/10 01:15:59
# @Author : Kariko Lin
import json
import warnings
from ctypes import c_ubyte
from io import BufferedReader, BufferedWriter, TextIOWrapper
from re import S as FULL_MATCH
from re import compile as regex
from struct import pack, unpack
from time import localtime, strftime
from typing import TypedDict
from xml.dom import minidom
from xml.etree import ElementTree as et

import yaml

from ..abstract import FileHandler
from .consts import SHIMAKAZE_SCHEMA, CsfMark
from .model import CsfDocument, CsfHead, CsfVal


class InvalidCsfRecord(Exception):
    """To record errors when reading .CSF files."""
    pass


# should keep this base class for better type hinting.
class CsfParser(FileHandler[CsfDocument]):
    ...


class CsfFileParser(CsfParser):
    @staticmethod
    def codingValue(valdata: bytearray | bytes) -> bytearray:
        # bytes would throw TypeError
        valdata = bytearray(valdata)
        i = 0
        while i < len(valdata):
            # only ubyte can do (
            valdata[i] = c_ubyte(~valdata[i]).value
            i += 1
        return valdata

    def __readheader(self, fp: BufferedReader) -> CsfHead:
        if fp.read(4).decode('ascii') != CsfMark.IS_CSF:
            raise InvalidCsfRecord('文件头错误或损坏——不是有效的红红 CSF 文件。')
        header = CsfHead(*unpack('LLLLL', fp.read(4 * 5)))
        return header

    def __readlabel(self, fp: BufferedReader, _csf: CsfDocument) -> None:
        """Label:

        -----------
        offset | element
        ----|------
        00H | char tag[4]
        04H | DWORD numstr
        08H | DWORD lenlbl
        0CH | char lblname[lenlbl]

        consider it as a struct with char* char** elements.
        """
        if fp.read(4).decode('ascii') != CsfMark.IS_LBL:
            raise InvalidCsfRecord('键值对校验失败——文件可能已损坏。')

        numstr, lenlbl = unpack('LL', fp.read(4 * 2))
        lblname = fp.read(lenlbl).decode('ascii')
        lblval: list[CsfVal] = []
        i = 0
        while i < numstr:
            lblval.append(self.__readvalue(fp))
            i += 1
        _csf[lblname] = lblval

    def __readvalue(self, fp: BufferedReader) -> CsfVal:
        """Value:

        ---------------------
        offset   |  element
        ---------|-----------
        00H      | char tag[4]
        04H      | DWORD lenval
        08H      | byte val[2 * lenval]
        (08+2*lenval)H     | leneval
        (08+2*lenval+04)H  | char eval[leneval]

        According to modenc,
        `val[2 * lenval]` was unicode encoded, with XORed bits content.
        """
        match fp.read(4).decode('ascii'):
            case CsfMark.IS_EVAL:
                is_eval = True
            case CsfMark.IS_VAL:
                is_eval = False
            case _:
                raise InvalidCsfRecord('CSF 值校验失败——文件可能已损坏。')

        length = unpack('L', fp.read(4))[0] << 1
        data = CsfVal(value=self.codingValue(fp.read(length)).decode('utf-16'))
        if is_eval:
            elength = unpack('L', fp.read(4))[0]
            data.extra = fp.read(elength).decode('ascii')
        return data

    def read(self) -> CsfDocument:
        ret = CsfDocument()
        with open(self._fn, 'rb') as fp:
            h = self.__readheader(fp)
            i = 0
            while i < h.numlabels:
                self.__readlabel(fp, ret)
                i += 1
        return ret

    def __writevalue(
        self, fp: BufferedWriter, val: CsfVal
    ) -> None:
        len_v = len(val.value)
        fp.write(pack(
            f'<4sL{len_v << 1}s',
            (CsfMark.IS_EVAL if val.extra else CsfMark.IS_VAL).encode('ascii'),
            len_v,
            self.codingValue(val.value.encode('utf-16'))[2:]))
        if val.extra is not None and (len_e := len(val.extra)) > 0:
            fp.write(pack(f'<L{len_e}s', len_e, val.extra.encode('ascii')))

    def __writelabels(
        self, fp: BufferedWriter, lbl: str, val: list[CsfVal]
    ) -> None:
        fp.write(pack(
            f'<4sLL{len(lbl)}s',
            CsfMark.IS_LBL.encode('ascii'),
            len(val),
            len(lbl),
            lbl.encode('ascii')))
        for i in val:
            self.__writevalue(fp, i)

    def write(self, _csf: CsfDocument) -> None:
        # force little endian.
        with open(self._fn, 'wb') as fp:
            fp.write(pack(   # header
                '<4sLLLLL',
                CsfMark.IS_CSF.encode('ascii'),
                *_csf.header))
            for k, v in _csf._items():
                self.__writelabels(fp, k, v)


class _JsonV2ValuePack(TypedDict, total=False):
    values: list['_JsonV2ValuePack']
    value: str | None | list[str]
    extra: str | None


_CsfJsonV2 = TypedDict('_CsfJsonV2', {
    '$schema': str,
    'protocol': int,
    'version': int,
    'language': int,
    'data': dict[str, _JsonV2ValuePack | str | list[str] | None]
}, total=False)


class CsfJsonV2Parser(CsfParser):
    JSON_TEMPLATE = _CsfJsonV2({
        "$schema": f"{SHIMAKAZE_SCHEMA}/json/csf/v2.json",
        "protocol": 2,
    })

    def __init__(self, filename: str, encoding: str = 'utf-8') -> None:
        super().__init__(filename)
        self._codec = encoding

    @staticmethod
    def __parse_vals(
        val: _JsonV2ValuePack | str | list[str] | None
    ) -> list[CsfVal]:
        if val is None:  # latest standard - empty val
            ret = [CsfVal(value="", extra=None)]
        elif isinstance(val, str):  # one-line val
            ret = [CsfVal(value=val, extra=None)]
        elif isinstance(val, list):  # multi-line val
            ret = [CsfVal(value='\n'.join(val), extra=None)]
        elif isinstance(val, dict) and 'values' not in val:  # Eval
            extra = val.get('extra')
            ret = CsfJsonV2Parser.__parse_vals(val['value'])
            ret[0].extra = extra
        else:
            ret = []
            for i in val['values']:  # multiple values, needs further process.
                ret.extend(CsfJsonV2Parser.__parse_vals(i))
        return ret

    def read(self) -> CsfDocument:
        ret = CsfDocument()
        with open(self._fn, 'r', encoding=self._codec) as fp:
            src: _CsfJsonV2 = json.load(fp)
        ret.version = src['version']
        ret.language = src['language']
        for k, v in src['data'].items():
            ret[k] = self.__parse_vals(v)
        return ret

    @staticmethod
    def __to_vals(val: list[CsfVal]) -> _JsonV2ValuePack:
        ret: _JsonV2ValuePack = {}
        if len(val) > 1:
            ret['values'] = [CsfJsonV2Parser.__to_vals([i]) for i in val]
        else:
            if '\n' in val[0].value:
                ret['value'] = val[0].value.split('\n')
            if val[0].extra:
                ret['extra'] = val[0].extra
        return ret

    def write(self, _csf: CsfDocument, indent: int = 2) -> None:
        """Convert to Shimakaze Csf-JSON v2 Document."""
        ret = self.JSON_TEMPLATE.copy()
        ret['version'] = _csf.version
        ret['language'] = _csf.language
        ret['data'] = {}
        for k, v in _csf._items():
            val = self.__to_vals(v)
            if 'values' not in val and 'extra' not in val:
                ret['data'][k] = val.get('value')
            else:
                ret['data'][k] = val
        with open(self._fn, 'w', encoding=self._codec) as fp:
            json.dump(ret, fp, ensure_ascii=False, indent=indent)


# may need to simplify the V1 implements,
# but I didn't really use XML. just keep it now.
class CsfXmlParser(CsfParser):
    """Since the encoding of xml is limited,
    this serializer would only supports 'utf-8'."""

    XML_SCHEMA_TYPENS = 'http://www.w3.org/2001/XMLSchema'
    XML_MODEL = (
        "<?xml-model "
        f'href="{SHIMAKAZE_SCHEMA}/xml/csf/v1.xsd" '
        'type="application/xml" '
        f'schematypens="{XML_SCHEMA_TYPENS}"?>\n')

    def read(self) -> CsfDocument:
        # keep compat with external styled xml
        indent_chk = regex(r'\n[ \t]+', FULL_MATCH)
        ret = CsfDocument()
        root = et.parse(self._fn).getroot()  # Resources
        ret.version = int(root.attrib.get('version', '3'))
        ret.language = int(root.attrib.get('language', '0'))
        for lbl in root:
            if (cur := list(lbl)) and cur[0].tag == 'Values':  # multi values
                lblvalue: CsfVal | list[CsfVal] = (
                    CsfVal(value="") if cur[0].text is None else
                    [CsfVal(value=indent_chk.sub('\n', v.text),
                            extra=v.attrib.get('extra')) for v in list(cur[0])]
                )
            else:
                lblvalue = (
                    CsfVal(value="") if lbl.text is None
                    else CsfVal(value=indent_chk.sub('\n', lbl.text))
                )
                lblvalue.extra = lbl.attrib.get('extra')
            ret[lbl.attrib['name']] = lblvalue
        return ret

    @staticmethod
    def __to_val(elem_node: et.Element, v: CsfVal) -> None:
        if v.extra:  # not None, not empty
            elem_node.attrib['extra'] = v.extra
        elem_node.text = v.value

    def __to_nodes(self, root: et.Element, k: str, v: list[CsfVal]) -> None:
        lbl = et.SubElement(root, 'Label', {'name': k})
        if len(v) == 1:
            self.__to_val(lbl, v[0])
        else:
            vals = et.SubElement(lbl, 'Values')
            for i in v:
                ei = et.SubElement(vals, 'Value')
                self.__to_val(ei, i)

    def write(self, _csf: CsfDocument, indent: str = '\t') -> None:
        """Convert to Shimakaze Csf-XML V1 Document.
        Only `utf-8` supported."""
        root = et.Element('Resources', {'protocol': '1',
                                        'version': str(_csf.version),
                                        'language': str(_csf.language)})
        for k, v in _csf._items():
            self.__to_nodes(root, k, v)
        formatted = minidom.parseString(et.tostring(root, 'utf-8'))
        xmllines = formatted.toprettyxml(
            indent, encoding='utf-8').decode().split('\n')
        with open(self._fn, 'w', encoding='utf-8') as fp:
            fp.write(f'{xmllines[0]}\n')
            fp.write(self.XML_MODEL)
            cnt = 1
            while cnt < len(xmllines):
                fp.write(f'{xmllines[cnt]}\n')
                cnt += 1


class _YamlMetaPack(TypedDict):
    lang: int
    version: int


class CsfLLangParser(CsfParser):
    """Due to complex implements of YAML signs,
    there is also LLF which is similar to YAML,
    but way more convenient for RA2 modders.

    Thanks to the following contributors to new lang file format:
    `Mr.L` & `TwinkleStar`."""
    YAML_SPECIAL_SIGNS_1 = [
        '_', '?', ',', '[', ']', '{', '}', '#', '&', '*', '!', '|',
        '>', '"', '%', ':'
    ]
    YAML_SPECIAL_SIGNS_2 = "'"
    YAML_SCHEMA_HEADER = (
        '# yaml-language-server: '
        f'$schema={SHIMAKAZE_SCHEMA}/yaml/csf/metadata.yaml')
    YAML_SCHEMA_BODY = (
        '# yaml-language-server: '
        f'$schema={SHIMAKAZE_SCHEMA}/yaml/csf/v1.yaml')

    def __init__(
            self,
            filename: str,
            encoding: str = "utf-8", *,
            yaml_compat: bool = False) -> None:
        """The keyword `yaml_compat` means that,
        just read the file as a normal YAML, otherwise read it as LLF."""
        super().__init__(filename)
        self._codec = encoding
        self._is_yaml = yaml_compat

    def __to_pairs(
        self, k: str, v: str | None, indent: int = 2
    ) -> tuple[str, str]:
        if v is None:
            v = "''" if self._is_yaml else ''
        elif '\n' in v:
            # `>-` in yaml means "folded", which means '\n\n' -> '\n',
            # which is why LLF was designed (too much special signs for L10N).
            mulline = '|-\n' if self._is_yaml else '>-\n'
            # LLF force 2-space indent, unable to adjust.
            lineindent = f'\n{indent * ' '}' if self._is_yaml else '\n  '
            v = (mulline + v).replace('\n', lineindent)
        if not self._is_yaml:
            return k, v

        if self.YAML_SPECIAL_SIGNS_2 in v:
            v = f'"{v}"'
        else:
            for i in self.YAML_SPECIAL_SIGNS_1:
                if i in v:
                    v = f"'{v}'"
                    break
        if ': ' in k:
            k = f"'{k}'"
        return k, v

    def __parse_pairs(self, fp: TextIOWrapper) -> dict[str, str]:
        ret: dict[str, str] = {}
        line_count = 0
        key, val = "", ""
        while True:
            # EOF
            if not (i := fp.readline()):
                break
            line_count += 1
            # commit before next line income.
            if len(key) > 0:
                ret[key] = val
            # issues dealt
            if i.strip().startswith('#'):
                continue
            if i.count(': ') > 1:
                warnings.warn(
                    f"第 {line_count} 行的 CSF 键可能提前截断！"
                    f"安全起见，已跳过该键值对：\n\t{i}")
                key, val = '', ''
                continue
            # parse
            if ': ' in i:
                key, val = i.split(': ', 1)
                key = key.strip()
                val = val.replace('>-', '').split(' #')[0].strip()
            elif len(key) > 0 and i.startswith('  '):
                val += '\n' + i.strip()
        return ret

    def read(self) -> CsfDocument:
        with open(self._fn, 'r', encoding=self._codec) as fp:
            header: _YamlMetaPack
            data: dict[str, str]
            if self._is_yaml:
                header, data = yaml.load_all(fp.read(), yaml.FullLoader)
            else:
                header = {'lang': 0, 'version': 3}
                data = self.__parse_pairs(fp)
        ret = CsfDocument()
        ret.language = header['lang']
        ret.version = header['version']
        for k, v in data.items():
            # may there be some pure digits considered as int
            ret[k] = CsfVal(value=str(v), extra=None)
        return ret

    def write(self, _csf: CsfDocument, indent: int = 2) -> None:
        """Convert to yaml file."""
        # manual dump as the pyyaml output is too ugly
        curtime = strftime("%Y-%m-%d %H:%M:%S", localtime())
        with open(self._fn, 'w', encoding=self._codec) as fp:
            fp.write(
                (
                    f'{self.YAML_SCHEMA_HEADER}\n'
                    f'lang: {_csf.language}\n'
                    f'version: {_csf.version}\n'
                    '---\n'
                    f'{self.YAML_SCHEMA_BODY}\n'
                )
                if self._is_yaml else
                (
                    f'# {self._fn.split('.')[0]}\n'
                    f'# csf count: {len(_csf)}\n'
                    f'# build time: {curtime}\n\n'
                )
            )
            for k, v in _csf._items():
                fp.write('%s: %s\n' % self.__to_pairs(k, v[0].value, indent))
