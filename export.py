# -*- encoding: utf-8 -*-
# @File   : __init__.py
# @Time   : 2023/11/14 17:40:39
# @Author : Chloride

from os.path import exists, join

from _ares_ini import INIClass, INISection


def _ex_regs(map_: INIClass, registry, target: INIClass):
    reg = map_.getTypeList(registry)
    del map_[registry]
    target[registry] = dict(zip(range(len(reg)), reg))
    _ex_entries(map, target, *reg)


def _ex_entries(map_: INIClass, target: INIClass, *entries):
    for i in entries:
        if i not in map_:
            continue
        target[i] = map_[i]
        del map_[i]


def _ex_compressed(map_: INIClass, section_name, file):
    with open(file, 'wb') as fp:
        for i in map_.getTypeList(section_name):
            fp.write(f'{i};;')
    try:
        del map[section_name]
    except Exception:
        pass


def exportMapElems(self: INIClass, out_dir: str):
    """To split map files to smaller files (git friendly).

    e.g. `exportMapElems(yr_a07, 'D:/yra07')` =>
    - `D:/yra07/(...).ini`
    - `D:/yra07/(...).bin`
    - `D:/yra07/partial.ini`
    """
    t = INIClass()
    _ex_regs(self, 'Houses', t)
    _ex_regs(self, 'Countries', t)
    with open(join(out_dir, 'Houses.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_regs(self, 'TaskForces', t)
    _ex_regs(self, 'ScriptTypes', t)
    _ex_regs(self, 'TeamTypes', t)
    _ex_entries(self, t, 'AITriggerTypes', 'AITriggerTypesEnable')
    with open(join(out_dir, 'AI.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_entries(self, t, 'Triggers', 'Events', 'Actions', 'Tags')
    with open(join(out_dir, 'Logics.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_entries(self, t, 'Infantry', 'Units', 'Aircraft', 'Structures')
    with open(join(out_dir, 'Technos.ini'), 'w', encoding='utf-8') as fp:
        t.writeStream(fp)
    t.clear()

    _ex_compressed(self, 'IsoMapPack5', join(out_dir, 'iso.bin'))
    _ex_compressed(self, 'OverlayPack', join(out_dir, 'ovl.bin'))
    _ex_compressed(self, 'OverlayDataPack', join(out_dir, 'ovldata.bin'))
    with open(join(out_dir, 'partial.ini'), 'w', encoding='utf-8') as fp:
        self.writeStream(fp)


def _extend_bin(bin_path, extend_name):
    s = ""
    with open(bin_path, 'rb') as fp:
        while fp.readable():
            s += fp.read()
    s = s.split(';;')[:-1]  # like 'aa;;bb;;' => ['aa', 'bb', '']
    return INISection(extend_name, **zip(range(1, len(s)), s))


def compilePartialMap(src_dir, out_name):
    """To merge partial files into a map file.

    PS: src_dir shouldn't end with `\\` or `/`!

    e.g. `compilePartialMap('D:/yra07')` => `D:/yra07/yra07.map`
    """
    if not exists(src_dir):
        return
    if not exists(join(src_dir, "partial.ini")):
        return
    out = INIClass()
    out.read(join(src_dir, "partial.ini"),
             join(src_dir, 'Houses.ini'),
             join(src_dir, 'AI.ini'),
             join(src_dir, 'Logics.ini'),
             join(src_dir, 'Technos.ini'),
             encoding='utf-8')
    out['IsoMapPack5'] = _extend_bin(join(src_dir, 'iso.bin'), 'IsoMapPack5')
    out['OverlayPack'] = _extend_bin(join(src_dir, 'ovl.bin'), 'OverlayPack')
    out['OverlayDataPack'] = _extend_bin(join(src_dir, 'ovldata.bin'),
                                         'OverlayDataPack')
    with open(join(src_dir, f"{out_name}.map"), 'w',
              encoding='utf-8') as fp:
        out.writeStream(fp)
