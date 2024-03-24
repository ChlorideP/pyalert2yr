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

from .formats.ini import INIClass


def _ex_regs(map_: INIClass, registry, target: INIClass):
    reg = map_.getTypeList(registry)
    if not reg:
        return
    del map_[registry]
    target[registry] = dict(zip(range(len(reg)), reg))
    _ex_entries(map_, target, *reg)


def _ex_entries(map_: INIClass, target: INIClass, *entries):
    for i in entries:
        if i not in map_:
            continue
        target[i] = map_[i]
        del map_[i]


def _ex_binaries(map_: INIClass, section, target_fn):
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
    _ex_regs(self, 'Houses', t)
    _ex_regs(self, 'Countries', t)
    with open(join(out_dir, 'houses.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_regs(self, 'TaskForces', t)
    _ex_regs(self, 'ScriptTypes', t)
    _ex_regs(self, 'TeamTypes', t)
    _ex_entries(self, t, 'AITriggerTypes', 'AITriggerTypesEnable')
    with open(join(out_dir, 'AI_local.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_entries(self, t,
                'VariableNames', 'Triggers', 'Events', 'Actions', 'Tags')
    with open(join(out_dir, 'logics.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_entries(self, t,
                'Infantry', 'Units', 'Aircraft', 'Structures',
                'Smudge', 'Terrain',
                'CellTags', 'Waypoints')
    with open(join(out_dir, 'objects.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_binaries(self, 'IsoMapPack5', join(out_dir, 'iso.mappkg'))
    _ex_binaries(self, 'OverlayPack', join(out_dir, 'ovl.mappkg'))
    _ex_binaries(self, 'OverlayDataPack', join(out_dir, 'ovldata.mappkg'))

    with open(join(out_dir, 'partial.ini'), 'w', encoding='utf-8') as fp:
        self.writeStream(fp)


def _im_binaries(target_map: INIClass, package_fn, target_section):
    target_map[target_section] = {}
    with open(package_fn, 'rb') as fp:
        while True:
            curpair = fp.read(4 + 70)  # int 4b, value char* 70b.
            if not curpair:
                break
            curpair = unpack('i70s', curpair)
            target_map[target_section].update(
                [(str(curpair[0]), curpair[1].decode().replace('\x00', ''))])


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
    out.read(join(src_dir, "partial.ini"),
             join(src_dir, 'houses.ini'),
             join(src_dir, 'AI_local.ini'),
             join(src_dir, 'logics.ini'),
             join(src_dir, 'objects.ini'),
             encoding='utf-8')
    _im_binaries(out, join(src_dir, 'iso.mappkg'), 'IsoMapPack5')
    _im_binaries(out, join(src_dir, 'ovl.mappkg'), 'OverlayPack')
    _im_binaries(out, join(src_dir, 'ovldata.mappkg'), 'OverlayDataPack')
    with open(join(src_dir, f"{out_name}.map"), 'w',
              encoding='utf-8') as fp:
        out.writeStream(fp)
