# -*- encoding: utf-8 -*-
# @File   : techno_props.py
# @Time   : 2024/06/30 14:45:45
# @Author : Chloride

"""To batch editing some properties in map technos,
like preset techno instances (Infantry, Units),
or techno type classes override ([YAPPET], etc)."""

from multiprocessing.pool import ThreadPool
from random import Random
from typing import Callable, TypedDict, Union

from .formats.ini import INISection, INIClass


# see modenc.
class TechnoProperties(TypedDict):
    owner: str
    techno: str
    health: str   # int
    coord_x: str  # int
    coord_y: str  # int


# in case Inf, Units, Airs are all FootTypes,
# but TypedDict must be in ordered.
class InfantryProps(TechnoProperties):
    sub_cell: str  # int
    mission: str
    facing: str    # int
    tag: str
    veterancy: str  # int
    group: str      # int
    onbridge: str   # bool
    autocreate_no: str      # bool
    autocreate_yes: str     # bool


class UnitProperties(TechnoProperties):
    facing: str     # int
    mission: str
    tag: str
    veterancy: str  # int
    group: str      # int


class VehicleProps(UnitProperties):
    onbridge: str   # bool
    follows_index: str  # int
    autocreate_no: str      # bool
    autocreate_yes: str     # bool


class AircraftProps(UnitProperties):
    autocreate_no: str      # bool
    autocreate_yes: str     # bool


class BuildingProps(TechnoProperties):
    facing: str     # int
    tag: str
    ai_sellable: str        # bool # obsolete
    ai_rebuildable: str     # bool # obsolete
    powered: str    # bool
    upgrades: str   # int
    spotlight: str  # int / enum
    plugin1: str
    plugin2: str
    plugin3: str
    ai_repairable: str      # bool
    nominal: str


FootTypeProps = Union[InfantryProps, VehicleProps, AircraftProps]
TechnoProps = Union[FootTypeProps, BuildingProps]

#  no need idx anymore.
# IDX_FT_MISSION = 6
# IDX_TECHNO = 1
# IDX_HEALTH = 2
# IDX_HOUSE = 0

# global rules
T_BUILDING = "BuildingTypes"
T_INFANTRY = "InfantryTypes"
T_VEHICLE = "VehicleTypes"
T_AIRCRAFT = "AircraftTypes"

KEY_SW = "SuperWeapon"


_random = Random(114514)


def replaceValue(section: INISection,
                 value_func: Callable[[str], str]):
    procpool = ThreadPool(len(section))
    pairs = procpool.map(
        lambda x, y: (x, value_func(y)),
        section.items())
    procpool.close()
    procpool.join()
    section.update(pairs)


def ftStatusReplace(section: INISection, status: str, *,
                    ft: FootTypeProps,
                    owner: str = None,
                    techno: str = None):
    def updateStatus(val: str):
        v: FootTypeProps = ft(zip(ft.__annotations__.keys(), val.split(',')))
        if techno is not None and v['techno'] != techno:
            return val
        if owner is None or v['owner'] == owner:
            v['mission'] = status
        return ','.join(v.values())

    return replaceValue(section, updateStatus)


def technoTypeReplace(section: INISection, src: str, *dst: str,
                      category: TechnoProps, random=False):
    def updateTechno(val: str):
        v: TechnoProps = category(
            zip(category.__annotations__.keys(), val.split(',')))
        if (v['techno'] == src):
            v['techno'] = (
                dst[0] if rand is None or len(dst) == 1
                else dst[rand.randint(0, len(dst) - 1)])
            val = v.values()
        return val

    rand = None if not random else _random
    return replaceValue(section, updateTechno)


def technoRandomFacing(section: INISection, *, category: TechnoProps):
    def updateFacing(val: str):
        v: TechnoProps = category(
            zip(category.__annotations__.keys(), val.split(',')))
        v['facing'] = str(_random.randint(0, 255))
        return ','.join(v.values())

    return replaceValue(section, updateFacing)


def technoRandomHP(section: INISection, *, category: TechnoProps):
    def updateHealth(val: str):
        v: TechnoProps = category(
            zip(category.__annotations__.keys(), val.split(',')))
        v['health'] = str(_random.randint(0, 255))
        return ','.join(v.values())

    return replaceValue(section, updateHealth)


def inhibitCapturable(mapdoc: INIClass, *todo: str,
                      rules: INIClass = None,
                      recurse=False):
    if 'Structures' not in mapdoc:  # even no buildings
        return
    presets = {BuildingProps(zip(BuildingProps.__annotations__.keys(),
                                 v.split(',')))['techno']
               for v in mapdoc['Structures'].values()}
    for i in todo:
        if i not in presets:
            continue
        if rules is not None:
            capval = rules.findKey(i, "Capturable", recurse)[1]
            if capval is not None:
                capval = capval.lower().startswith(('1', 'y', 't'))
        else:
            capval = True
        if capval:
            mapdoc.add(i, {"Capturable": "false"})
