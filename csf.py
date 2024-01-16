# -*- encoding: utf-8 -*-
# @File   : csf.py
# @Time   : 2024/01/09 21:17:24
# @Author : Chloride
"""C&C Stringtable Format

Support .csf files IO and JSON, XML files import/export.

The JSON formatting follows [Shimakaze](https://frg2089.github.io)'s schema,
while the XML's **partially** does.

The SIMPLE YAML document, as it described, only support simple value,
with just `label: str` pair form.

Direct operation on CsfDocument instance is also supported,
but in my opinion, way more complex than just editing text files.
"""

import json
import yaml
from collections.abc import Iterator, MutableMapping
from ctypes import c_ubyte
from io import FileIO
from struct import pack, unpack
from typing import Any, Dict, List, NamedTuple, Optional, TypedDict, Union
from xml.dom import minidom
from xml.etree import ElementTree as et

__all__ = ['CSF_TAG', 'LBL_TAG', 'VAL_TAG', 'EVAL_TAG', 'LANG_LIST',
           'CsfHead', 'CsfVal', 'CsfDocument', 'InvalidCsfException',
           'csfToJSONV2', 'csfToXML', 'importJSONV2', 'importXML',
           'csfToSimpleYAML', 'importSimpleYAML']


CSF_TAG = " FSC"
LBL_TAG = " LBL"
VAL_TAG = " RTS"
EVAL_TAG = "WRTS"

LANG_LIST = [
    'en_US',
    'en_UK',
    'de',  # German
    'fr',  # French
    'es',  # Spanish
    'it',  # Italian
    'jp',  # Japanese
    'Jabberwockie',
    'kr',  # Korean
    'zh'  # Chinese
]

JSON_HEAD = {
    "$schema": "https://shimakazeproject.github.io/json/csf/v2/schema.json",
    "protocol": 2
}


YAML_SPECIAL_SIGNS_1 = [
    '_', '?', ',', '[', ']', '{', '}', '#', '&', '*', '!', '|',
    '>', '"', '%', ':'
]
YAML_SPECIAL_SIGNS_2 = "'"
YAML_SCHEMA_HEADER = '# yaml-language-server: \
$schema=https://shimakazeproject.github.io/Schemas/yaml/csf/metadata.yaml'
YAML_SCHEMA_BODY = '# yaml-language-server: \
$schema=https://shimakazeproject.github.io/Schemas/yaml/csf/v1.yaml'


class CsfHead(NamedTuple):
    """Only for IO process."""
    version: int  # offset 04H, after CSF_TAG.
    numlabels: int
    numvalues: int
    unused: int
    language: int


class CsfVal(TypedDict):
    value: Union[str, List[str]]
    extra: Optional[str]


class InvalidCsfException(Exception):
    """To record errors when reading .CSF files."""
    pass


# def _codingvalue(valdata: bytes, start=0, lenvaldata=None):
def _codingvalue(valdata: bytearray):
    # bytes would throw TypeError
    valdata = bytearray(valdata)
    i = 0
    while i < len(valdata):
        # only ubyte can do (
        valdata[i] = c_ubyte(~valdata[i]).value
        i += 1
    return valdata


class CsfDocument(MutableMapping):
    version = 3
    language = 0

    def __init__(self):
        # str as label tag, list as values (or evals)
        self.__data: Dict[str, List[CsfVal]] = {}
        # it seems there are Csf(E)Vals without label ...
        # just leave them out = =
        # self.__isolated: List[Union[CsfVal, CsfEVal]] = []

    def __getitem__(self, lbl: str) -> Union[CsfVal, List[CsfVal]]:
        return (self.__data[lbl] if len(self.__data[lbl]) > 1
                else self.__data[lbl][0])

    def __setitem__(self, lbl: str, val: Union[CsfVal, List[CsfVal]]):
        # for multiple value, game would only use the first one.
        try:
            self.__data[lbl][0] = CsfVal(val)
        except Exception:
            self.__data[lbl] = val if isinstance(val, list) else [val]

    def __delitem__(self, lbl: str) -> None:
        return self.__data.__delitem__(lbl)

    def __iter__(self) -> Iterator:
        return self.__data.__iter__()

    def __len__(self) -> int:
        return self.__data.__len__()

    def getValidValue(self, label) -> Optional[str]:
        """Get the value really read by `game*.exe`."""
        try:
            return self.__data[label][0].get('value', '')
        except IndexError:
            return None

    def setdefault(self, label, string, *, extra=None):
        """Append a label which doesn't exist in document,
        with single `CsfVal`."""
        if label in self.__data:
            return
        self[label] = CsfVal(value=string, extra=extra)

    def __readheader(self, fp: FileIO):
        if fp.read(4).decode('ascii') != CSF_TAG:
            raise InvalidCsfException('NOT csf file')
        header = CsfHead(*unpack('LLLLL', fp.read(4 * 5)))
        return header

    def __readlabel(self, fp: FileIO):
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
        if fp.read(4).decode('ascii') != LBL_TAG:
            raise InvalidCsfException('NOT a proper Csf Label')

        numstr, lenlbl = unpack('LL', fp.read(4 * 2))
        lblname = fp.read(lenlbl).decode('ascii')
        self.__data[lblname] = []

        i = 0
        while i < numstr:
            self.__data[lblname].append(self.__readvalue(fp))
            i += 1

    __EV_SWITCH = {
        EVAL_TAG: True,
        VAL_TAG: False,
    }

    def __readvalue(self, fp: FileIO):
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
        if (isev := self.__EV_SWITCH.get(fp.read(4).decode('ascii'))) is None:
            raise InvalidCsfException('Not a proper Csf Label Value')

        length = unpack('L', fp.read(4))[0] << 1
        data = CsfVal(value=_codingvalue(fp.read(length)).decode('utf-16'),
                      extra=None)
        if isev:
            elength = unpack('L', fp.read(4))[0]
            data['extra'] = fp.read(elength).decode('ascii')
        return data

    def readCsf(self, filepath):
        with open(filepath, 'rb') as fp:
            h = self.__readheader(fp)
            i = 0
            while i < h.numlabels:
                self.__readlabel(fp)
                i += 1
        return len(self)

    @property
    def header(self) -> CsfHead:
        numstr = 0
        for i in self.__data.values():
            numstr += len(i)
        return CsfHead(self.version, len(self), numstr, 0, self.language)

    def __writeLabels(self, fp: FileIO, lbl: str, val: List[CsfVal]):
        fp.write(pack(f'<4sLL{len(lbl)}s',
                      LBL_TAG.encode('ascii'), len(val), len(lbl),
                      lbl.encode('ascii')))
        for i in val:  # value
            lv, isev = len(i['value']), i.get('extra') is not None
            fp.write(pack(
                f'<4sL{lv << 1}s',
                (EVAL_TAG if isev else VAL_TAG).encode('ascii'), lv,
                _codingvalue(i['value'].encode('utf-16'))[2:]))
            if isev:
                ev = len(i['extra'])
                fp.write(pack(f'<L{ev}s', ev, i['extra'].encode('ascii')))

    def writeCsf(self, filepath):
        # force little endian.
        with open(filepath, 'wb') as fp:
            # 00(0x00) - 24(0x17)
            fp.write(pack('<4sLLLLL',  # header
                          CSF_TAG.encode('ascii'), *self.header))
            # 0x18
            for k, v in self.__data.items():
                self.__writeLabels(fp, k, v)


def _tojsonvalue(val: Union[CsfVal, List[CsfVal]]) -> dict:
    if isinstance(val, list):
        ret = {'values': [_tojsonvalue(i) for i in val]}
    else:
        ret = val.copy()
        if '\n' in ret['value']:
            ret['value'] = ret['value'].split('\n')
        if ret['extra'] is None:
            del ret['extra']
    return ret


def _fromjson(val: Union[Dict[str, Any], List[str], str]):
    if isinstance(val, str):  # one-line val
        ret = CsfVal(value=val, extra=None)
    elif isinstance(val, list):  # multi-line val
        ret = CsfVal(value='\n'.join(val), extra=None)
    elif isinstance(val, dict) and 'values' not in val:  # Eval
        ret = CsfVal(value=val['value'], extra=val.get('extra'))
    else:
        ret = []
        for i in val['values']:  # multiple values, needs further process.
            ret.append(_fromjson(i))
    return ret


def csfToJSONV2(self: CsfDocument, jsonfilepath, encoding='utf-8', indent=2):
    """Convert to Shimakaze Csf-JSON v2 Document."""
    ret = JSON_HEAD.copy()
    ret['version'] = self.version
    ret['language'] = self.language
    ret['data'] = {}
    for k, v in self.items():
        v = _tojsonvalue(v)
        if 'values' not in v and 'extra' not in v:
            v = v['value']
        ret['data'][k] = v
    with open(jsonfilepath, 'w', encoding=encoding) as fp:
        json.dump(ret, fp, ensure_ascii=False, indent=indent)


def importJSONV2(jsonfilepath, encoding='utf-8') -> CsfDocument:
    ret = CsfDocument()
    with open(jsonfilepath, 'r', encoding=encoding) as fp:
        src = json.load(fp)
    ret.version = src['version']
    ret.language = src['language']
    for k, v in src['data'].items():
        ret[k] = _fromjson(v)
    return ret


def csfToXML(self: CsfDocument, xmlfilepath, encoding='utf-8', indent='\t'):
    """Convert to XML Document."""
    root = et.Element('Resources', {'Version': str(self.version),
                                    'Language': str(self.language)})
    tmp = []
    for k, v in self.items():
        lbl = et.SubElement(root, 'Label', {'name': k})
        if isinstance(v, dict):
            if v['extra'] is not None:
                lbl.attrib['extra'] = v['extra']
            lbl.text = v['value']
        else:
            vals = et.SubElement(lbl, 'Values')
            lbl = [lbl, vals]
            for i in v:
                ei = et.SubElement(vals, 'Value')
                if i['extra'] is not None:
                    ei.attrib['extra'] = i['extra']
                ei.text = i['value']
                lbl.append(ei)
        tmp.append(lbl)
    # tree = et.ElementTree(root)
    rawstring = et.tostring(root, encoding)
    formatted = minidom.parseString(rawstring)
    xmlstream = formatted.toprettyxml(encoding=encoding, indent=indent)
    with open(xmlfilepath, 'wb') as fp:
        fp.write(xmlstream)


def importXML(xmlfilepath) -> CsfDocument:
    ret = CsfDocument()
    tree = et.parse(xmlfilepath)
    root = tree.getroot()  # Resources
    ret.version = int(root.attrib.get('Version', '3'))
    ret.language = int(root.attrib.get('Language', '0'))
    for lbl in root:
        if (_ := list(lbl)) and _[0].tag == 'Values':  # multi values
            lblvalue = [CsfVal(value=v.text, extra=v.attrib.get('extra'))
                        for v in list(_[0])]
        else:
            lblvalue = CsfVal(value=lbl.text, extra=lbl.attrib.get('extra'))
        ret[lbl.attrib['name']] = lblvalue
    return ret


def csfToSimpleYAML(self: CsfDocument, yamlfilepath,
                    encoding='utf-8', indent=2):
    """Convert to SIMPLE yaml file."""
    yaml_special_signs = YAML_SPECIAL_SIGNS_1.copy()
    yaml_special_signs.append(YAML_SPECIAL_SIGNS_2)
    # manual dump - - the pyyaml output is too ugly
    with open(yamlfilepath, 'w', encoding='utf-8') as fp:
        fp.write(f'{YAML_SCHEMA_HEADER}\n'
                 f'lang: {self.language}\n'
                 f'version: {self.version}\n'
                 '---\n')  # header
        fp.write(f'{YAML_SCHEMA_BODY}\n')  # body
        for k in self.keys():
            v = self.getValidValue(k)
            if v is None:
                v = "''"
            elif '\n' in v:  # multi line (with (>-) or without (>) special)
                prefix = '>\n'
                for i in yaml_special_signs:
                    if i in v:
                        prefix = '>-\n'
                        break
                v = (prefix + v).replace('\n', f'\n{indent * " "}')
            elif YAML_SPECIAL_SIGNS_2 in v:
                v = f'"{v}"'
            else:
                for i in YAML_SPECIAL_SIGNS_1:
                    if i in v:
                        v = f"'{v}'"
                        break
            if ': ' in k:
                k = f"'{k}'"
            fp.write(f'{k}: {v}\n')


def importSimpleYAML(yamlfilepath, encoding='utf-8') -> CsfDocument:
    with open(yamlfilepath, 'r', encoding=encoding) as fp:
        header, data = yaml.load_all(fp.read(), yaml.FullLoader)
    ret = CsfDocument()
    ret.language = header['lang']
    ret.version = header['version']
    for k, v in data.items():
        # may there be some pure digits considered as int
        ret[k] = CsfVal(value=str(v), extra=None)
    return ret
