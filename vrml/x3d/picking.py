"""X3D's pick sensors, told what their picking geometry touches -- NumPy only

A pick sensor (ISO/IEC 19775-1, 38) tests its `pickingGeometry` against the
shapes under its `pickTarget` nodes. Whoever draws the scene does the
geometry: each frame it calls `observe` with a :class:`Pick` for every shape
touched, in the order it found them, and the sensor sends its events.

- `sortOrder` chooses among the picks: ``ANY`` the first found, ``CLOSEST``
  the nearest (the default, and what an unknown value means), ``ALL`` every
  one as found, ``ALL_SORTED`` every one nearest first.
- `isActive TRUE` is sent when something is picked and `isActive FALSE` when
  nothing is; `pickedGeometry` is sent when the shapes chosen change.
- A `LinePickSensor` sends `pickedPoint`, `pickedNormal` and
  `pickedTextureCoordinate`, and a `PointPickSensor` `pickedPoint`, for the
  chosen picks in their order, when they change.
- A sensor that is not `enabled`, or whose `objectType` holds ``NONE``,
  picks nothing.

:func:`matches` is the `objectType` test a pickable group's labels are put
to (`matchCriterion`).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, NamedTuple

import numpy as np
from numpy.typing import ArrayLike

from vrml.x3d import nodes as x3d
from vrml.x3d import timing

__all__ = [
    'PICK_SENSORS', 'LinePickSensor', 'Pick', 'PickSensor', 'PointPickSensor',
    'PrimitivePickSensor', 'VolumePickSensor', 'matches',
]

#: The orders `sortOrder` names; any other is CLOSEST.
SORT_ORDERS = ('ANY', 'CLOSEST', 'ALL', 'ALL_SORTED')


class Pick(NamedTuple):
    """One shape the picking geometry touches

    geometry -- what `pickedGeometry` sends for it: the picked shape
    distance -- how far it is, by which `sortOrder` chooses
    points, normals, texCoords -- for a line or point sensor, where it was
        touched, in the sensor's coordinates; three values a row
    """

    geometry: Any
    distance: float
    points: ArrayLike = ()
    normals: ArrayLike = ()
    texCoords: ArrayLike = ()


def matches(sensorTypes: Iterable[str], objectTypes: Iterable[str], criterion: str) -> bool:
    """Whether a pickable object labelled `objectTypes` is picked by a sensor's `sensorTypes`

    ``NONE`` on either side is never picked and ``ALL`` on either side always
    is. Otherwise ``MATCH_ANY`` wants a label in common, ``MATCH_EVERY`` every
    one of the sensor's labels among the object's, and ``MATCH_ONLY_ONE``
    exactly one label in common.
    """
    sensor, found = set(sensorTypes), set(objectTypes)
    if 'NONE' in sensor or 'NONE' in found:
        return False
    if 'ALL' in sensor or 'ALL' in found:
        return True
    shared = len(sensor & found)
    if criterion == 'MATCH_EVERY':
        return shared == len(sensor)
    if criterion == 'MATCH_ONLY_ONE':
        return shared == 1
    return shared > 0


def _rows(picks: Sequence[Pick], name: str) -> np.ndarray:
    """The picks' `name` values joined into one array of three a row"""
    rows = [np.asarray(getattr(pick, name), dtype=np.float64).reshape(-1, 3) for pick in picks]
    return np.concatenate(rows) if rows else np.zeros((0, 3))


class PickSensor(timing.Timed):
    """What every pick sensor does with the picks it is told of"""

    enabled: Any
    objectType: Any
    matchCriterion: Any
    sortOrder: Any
    isActive: Any
    pickedGeometry: Any

    #: The point events the sensor sends, with the `Pick` value each is made of.
    POINT_EVENTS: tuple[tuple[str, str], ...] = ()

    def senses(self) -> bool:
        """Whether the sensor picks at all: enabled, and not of object type NONE"""
        return bool(self.enabled) and 'NONE' not in list(self.objectType)

    def accepts(self, objectTypes: Iterable[str]) -> bool:
        """Whether an object labelled `objectTypes` can be picked by this sensor"""
        return matches(self.objectType, objectTypes, str(self.matchCriterion))

    def chosen(self, picks: Sequence[Pick]) -> list[Pick]:
        """The picks `sortOrder` keeps, in the order they are sent"""
        if not picks:
            return []
        order = str(self.sortOrder)
        if order == 'ANY':
            return [picks[0]]
        if order == 'ALL':
            return list(picks)
        ordered = sorted(picks, key=lambda pick: pick.distance)
        if order == 'ALL_SORTED':
            return ordered
        return ordered[:1]

    def observe(self, picks: Sequence[Pick]) -> None:
        """The shapes the picking geometry touches this frame, in the order found"""
        chosen = self.chosen(picks) if self.senses() else []
        active = bool(chosen)
        if active != bool(self.__dict__.get('_active', False)):
            self.__dict__['_active'] = active
            self.isActive = active
        geometry = [pick.geometry for pick in chosen]
        last = self.__dict__.get('_geometry')
        if (last is not None or geometry) and not _same_nodes(last or [], geometry):
            self.pickedGeometry = geometry
        self.__dict__['_geometry'] = geometry
        for event, name in self.POINT_EVENTS:
            values = _rows(chosen, name)
            last_values = self.__dict__.get('_' + event)
            if last_values is None and not len(values):
                continue
            if last_values is None or not np.array_equal(last_values, values):
                setattr(self, event, values)
            self.__dict__['_' + event] = values


def _same_nodes(first: Sequence[Any], second: Sequence[Any]) -> bool:
    return len(first) == len(second) and all(a is b for a, b in zip(first, second))


class LinePickSensor(PickSensor, x3d.LinePickSensor):
    """Line segments against the targets: where each crosses a surface"""

    POINT_EVENTS = (('pickedPoint', 'points'), ('pickedNormal', 'normals'),
                    ('pickedTextureCoordinate', 'texCoords'))


class PointPickSensor(PickSensor, x3d.PointPickSensor):
    """Points against the targets: those within them"""

    POINT_EVENTS = (('pickedPoint', 'points'),)


class PrimitivePickSensor(PickSensor, x3d.PrimitivePickSensor):
    """A box, cone, cylinder or sphere against the targets"""


class VolumePickSensor(PickSensor, x3d.VolumePickSensor):
    """A closed geometry against the targets"""


#: Each pick sensor class by its X3D name.
PICK_SENSORS: "dict[str, type]" = {cls.PROTO: cls for cls in (
    LinePickSensor, PointPickSensor, PrimitivePickSensor, VolumePickSensor)}
