# -*- encoding: utf-8 -*-
# @File   : __init__.py
# @Time   : 2023/11/14 17:40:39
# @Author : Chloride
"""
Since `.map` files are basically INIs, it sounds great to manage them with Git.

However, a map would consists with thousands of lines, even
compressed map packs within unreadable texts, meaningless to diff.

So with this module, you could split a map into lower scale INIs and
package binaries, which is Git friendly.
"""
# It's fine to just decode and encode map packs, but I am lazy to continue.

from os.path import exists, join
from struct import pack, unpack
from typing import Tuple

from .formats.ini import INISection, INIClass, INIParser

__all__ = ['splitMap', 'joinMap']


def copyRegistry(src: INIClass, registry, dst: INIClass):
    if registry not in src:
        return
    if not (reg := src[registry].toTypeList()):
        return
    del src[registry]
    dst[registry] = INISection(zip(
        [str(i) for i in range(len(reg))], reg))
    copyRegItems(src, dst, *reg)


def copyRegItems(map_: INIClass, target: INIClass, *entries):
    for i in entries:
        if i not in map_:
            continue
        target[i] = map_[i]
        del map_[i]


def exportMappkg(map_: INIClass, section, target_fn):
    if section not in map_:
        return
    with open(target_fn, 'wb') as f:
        for k, v in map_[section].items():
            cur = pack('i70s', int(k), v.encode())
            f.write(cur)
    del map_[section]


def splitMap(self: INIClass, out_dir: str):
    """To split map files to smaller files (git friendly).

    e.g. `splitMap(yr_a07, 'D:/yra07')` =>
    - `D:/yra07/(...).ini`
    - `D:/yra07/*.mappkg`
    - `D:/yra07/partial.ini`
    """
    t = INIClass()
    copyRegistry(self, 'Houses', t)
    copyRegistry(self, 'Countries', t)
    INIParser.write(t, join(out_dir, 'houses.ini'), 'utf-8')
    t.clear()

    copyRegistry(self, 'TaskForces', t)
    copyRegistry(self, 'ScriptTypes', t)
    copyRegistry(self, 'TeamTypes', t)
    copyRegItems(self, t, 'AITriggerTypes', 'AITriggerTypesEnable')
    INIParser.write(t, join(out_dir, 'AI_local.ini'), 'utf-8')
    t.clear()

    copyRegItems(self, t,
                 'VariableNames', 'Triggers', 'Events', 'Actions', 'Tags')
    INIParser.write(t, join(out_dir, 'logics.ini'), 'utf-8')
    t.clear()

    copyRegItems(self, t,
                 'Infantry', 'Units', 'Aircraft', 'Structures',
                 'Smudge', 'Terrain',
                 'CellTags', 'Waypoints')
    INIParser.write(t, join(out_dir, 'objects.ini'), 'utf-8')
    t.clear()

    exportMappkg(self, 'IsoMapPack5', join(out_dir, 'iso.mappkg'))
    exportMappkg(self, 'OverlayPack', join(out_dir, 'ovl.mappkg'))
    exportMappkg(self, 'OverlayDataPack', join(out_dir, 'ovldata.mappkg'))

    INIParser.write(self, join(out_dir, 'partial.ini'), 'utf-8')


def loadMappkg(target_map: INIClass, package_fn, target_section):
    target_map[target_section] = {}
    with open(package_fn, 'rb') as fp:
        while True:
            curpair = fp.read(4 + 70)  # int 4b, value char* 70b.
            if not curpair:
                break
            curpair: Tuple[int, bytes] = unpack('i70s', curpair)
            target_map[target_section].update({
                str(curpair[0]): curpair[1].decode().replace('\x00', '')})


def joinMap(src_dir, out_name):
    """To merge partial files into a map file.

    PS: src_dir shouldn't end with `\\` or `/`!

    e.g. `joinMap('D:/yra07', 'antrc')` => `D:/yra07/antrc.map`
    """
    if not exists(src_dir):
        return
    if not exists(join(src_dir, "partial.ini")):
        return
    out = INIClass()
    INIParser.readTree(join(src_dir, "partial.ini"),
                       join(src_dir, 'houses.ini'),
                       join(src_dir, 'AI_local.ini'),
                       join(src_dir, 'logics.ini'),
                       join(src_dir, 'objects.ini'),
                       sequential=True)
    loadMappkg(out, join(src_dir, 'iso.mappkg'), 'IsoMapPack5')
    loadMappkg(out, join(src_dir, 'ovl.mappkg'), 'OverlayPack')
    loadMappkg(out, join(src_dir, 'ovldata.mappkg'), 'OverlayDataPack')
    INIParser.write(out, join(src_dir, f"{out_name}.map"))
