"""X3D's environmental sensors, told what they sense -- NumPy only

A `ProximitySensor` watches the viewer, a `TransformSensor` its
`targetObject`, within the box of `size` about `center` (ISO/IEC 19775-1,
22.4); a `VisibilitySensor` whether its box is in view. Whoever draws the
scene calls `observe` each frame with what the sensor senses, in the
sensor's own coordinates, and the sensor sends its events.

- Entering the box sends `isActive TRUE` and `enterTime`; leaving it sends
  `isActive FALSE` and `exitTime`.
- While inside, a `ProximitySensor` or `TransformSensor` sends
  `position_changed` and `orientation_changed` when either changes.
- A box with any side of zero senses nothing, and a sensor that is not
  `enabled` is left, sending `isActive FALSE` where it was active.

The times are the sensor's :meth:`~vrml.x3d.timing.Timed.now` unless
`observe` is given one.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from numpy.typing import ArrayLike

from vrml.x3d import nodes as x3d
from vrml.x3d import timing

__all__ = ['SENSORS', 'ProximitySensor', 'Region', 'TransformSensor', 'VisibilitySensor']


class Region(timing.Timed):
    """An environmental sensor's box, and its entering and leaving"""

    center: Any
    size: Any
    enabled: Any
    isActive: Any
    enterTime: Any
    exitTime: Any

    def sized(self) -> bool:
        """Whether the box has every side longer than zero"""
        return bool(np.all(np.asarray(self.size, dtype=np.float64) > 0))

    def contains(self, point: ArrayLike) -> bool:
        """Whether `point`, in the sensor's coordinates, is within its box"""
        if not self.sized():
            return False
        size = np.asarray(self.size, dtype=np.float64)
        offset = np.abs(np.asarray(point, dtype=np.float64)[:3] - np.asarray(self.center, np.float64))
        return bool(np.all(offset <= size / 2.0))

    def active(self) -> bool:
        """Whether the sensor is sensing what it watches"""
        return bool(self.__dict__.get('_active', False))

    def sense(self, inside: bool, now: Optional[float]) -> bool:
        """Enter or leave as `inside` says; whether the sensor is active after"""
        inside = bool(inside) and bool(self.enabled)
        if inside != self.active():
            when = self.now() if now is None else float(now)
            self.__dict__['_active'] = inside
            self.isActive = inside
            if inside:
                self.enterTime = when
            else:
                self.exitTime = when
        return inside


class Posed(Region):
    """A sensor that sends the position and orientation of what it watches"""

    position_changed: Any
    orientation_changed: Any

    def observe(self, position: ArrayLike, orientation: ArrayLike,
                now: Optional[float] = None) -> None:
        """What the sensor watches is at `position`, turned by `orientation`

        Both are in the sensor's coordinates; `orientation` is an X3D
        rotation (axis, angle).
        """
        if not self.sense(self.contains(position), now):
            return
        position = np.asarray(position, dtype=np.float64)[:3]
        orientation = np.asarray(orientation, dtype=np.float64)[:4]
        last = self.__dict__.get('_pose')
        if last is None or not np.allclose(last[0], position):
            self.position_changed = position
        if last is None or not np.allclose(last[1], orientation):
            self.orientation_changed = orientation
        self.__dict__['_pose'] = (position, orientation)

    def sense(self, inside: bool, now: Optional[float]) -> bool:
        if not inside:
            self.__dict__.pop('_pose', None)
        return Region.sense(self, inside, now)


class ProximitySensor(Posed, x3d.ProximitySensor):
    """The viewer within a box"""


class TransformSensor(Posed, x3d.TransformSensor):
    """A target object within a box"""


class VisibilitySensor(Region, x3d.VisibilitySensor):
    """A box in view"""

    def observe(self, visible: bool, now: Optional[float] = None) -> None:
        """Whether some of the box is in view"""
        self.sense(bool(visible) and self.sized(), now)


#: Each sensor class by its X3D name.
SENSORS: "dict[str, type]" = {cls.PROTO: cls for cls in (
    ProximitySensor, TransformSensor, VisibilitySensor)}
