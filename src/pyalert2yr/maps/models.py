# -*- encoding: utf-8 -*-
# @File   : models.py
# @Time   : 2024/09/08 15:52:32
# @Author : Kariko Lin

from dataclasses import dataclass
from typing import TypedDict

from ..abstract import SerializedComponents


# see modenc.
class TechnoProperties(TypedDict):
    owner: str
    techno: str
    health: str   # int
    coord_x: str  # int
    coord_y: str  # int


# in case Inf, Units, Airs are all FootTypes,
# but TypedDict must be in ordered.
class Infantry(TechnoProperties):
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


class Vehicle(UnitProperties):
    onbridge: str   # bool
    follows_index: str  # int
    autocreate_no: str      # bool
    autocreate_yes: str     # bool


class Aircraft(UnitProperties):
    autocreate_no: str      # bool
    autocreate_yes: str     # bool


class Building(TechnoProperties):
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


# FIXME: Type alias of FootType and TechnoType.
FootType = Infantry | Vehicle | Aircraft
TechnoType = FootType | Building


@dataclass
class TriggerAction:
    action_id: str = '0'
    # real p1 right here, in INI expression
    p1_type: str = '0'  # basically enum, but I haven't check out YRpp
    # this is real p2 in INI, and samely below.
    p1: str = '0'
    p2: str = '0'
    p3: str = '0'
    p4: str = '0'
    p5: str = '0'
    waypoint: str = 'A'


class TriggerEvent(TypedDict, total=False):
    event_id: str
    extp2_switch: str
    p1: str
    p2: str


class Trigger(TypedDict):
    owner: str
    attach: str
    desc: str
    disabled: str  # bool
    easy: str   # bool
    mid: str   # bool
    hard: str   # bool
    _repeat: str  # unused


class TriggerTag(TypedDict):
    repeat_type: str  # int
    desc: str
    assoc: str


class ActionsPointer(SerializedComponents[TriggerAction]):
    """A seeker like `StringIO`, to get trigger actions easier."""
    def __init__(self, actions: str | list[str]) -> None:
        if isinstance(actions, str):
            actions = actions.split(',')
        self.__raw = actions
        self._seek = 1
        self._curidx = 0

    @property
    def length(self) -> int:
        return int(self.__raw[0])

    def reset_seek(self) -> None:
        self._seek = 1
        self._curidx = 0

    @property
    def seekable(self) -> bool:
        return self._curidx < self.length

    def next(self) -> None:
        if not self.seekable:
            return
        self._curidx += 1
        self._seek += 8

    @property
    def current(self) -> TriggerAction:
        # triggerID = actionsCount, (actionID,p1,p2,p3,p4,p5,p6,p7), ...
        return TriggerAction(*self.__raw[self._seek: self._seek + 8])

    @current.setter
    def current(self, val: TriggerAction) -> None:
        self.__raw[self._seek: self._seek + 8] = [
            val.action_id, val.p1_type, val.p1, val.p2, val.p3,
            val.p4, val.p5]

    def __str__(self) -> str:
        return ','.join(self.__raw)


class EventsPointer(SerializedComponents[TriggerEvent]):
    """A seeker like `StringIO`, to get trigger events easier."""

    def __init__(self, actions: str | list[str]) -> None:
        if isinstance(actions, str):
            actions = actions.split(',')
        self.__raw = actions
        self._seek = 1
        self._curidx = 0

    @property
    def length(self) -> int:
        return int(self.__raw[0])

    def reset_seek(self) -> None:
        self._seek = 1
        self._curidx = 0

    @property
    def seekable(self) -> bool:
        return self._curidx < self.length

    def next(self) -> None:
        if not self.seekable:
            return
        self._curidx += 1
        match self.current['extp2_switch']:
            case '2':
                self._seek += 4
            case _:
                self._seek += 3

    @property
    def current(self) -> TriggerEvent:
        # triggerID = e_cnt, (eID,tag,p1), (eID,tag,p1,[optional p2]), ...
        e = TriggerEvent(
            event_id=self.__raw[self._seek],
            extp2_switch=self.__raw[self._seek + 1],
            p1=self.__raw[self._seek + 2]
        )
        if e['extp2_switch'] == '2':
            e['p2'] = self.__raw[self._seek + 3]
        return e

    @current.setter
    def current(self, val: TriggerEvent) -> None:
        seq = [val['event_id'], val['extp2_switch'], val['p1']]
        if len(val) == 4:
            seq.append(val['p2'])
        match self.current['extp2_switch']:
            case '2':
                _range = 4
            case _:
                _range = 3
        self.__raw[self._seek: self._seek + _range] = seq

    def __str__(self) -> str:
        return ','.join(self.__raw)
