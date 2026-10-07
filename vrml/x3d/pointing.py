"""X3D's pointing-device sensors, told where the pointer is -- NumPy only

A pointing-device sensor (ISO/IEC 19775-1, 20) senses the pointer over the
geometry that shares its parent. Nothing here reads a pointer: whoever has one
calls, in the sensor's own coordinates,

- :meth:`Pointing.pointerOver` as the pointer moves, with the :class:`Hit` on
  the sensor's geometry or None;
- :meth:`Pointing.pointerPress` when the primary button goes down over it,
  with the hit and the pointer's :class:`Ray`;
- :meth:`Pointing.pointerDrag` as the pointer moves while the button is held,
  with the hit (or None) and the ray;
- :meth:`Pointing.pointerRelease` when the button comes up, with whether the
  pointer is still over the sensor's geometry.

A `TouchSensor` sends `isOver`, the hit's point, normal and texture
coordinate, `isActive` while held and `touchTime` for a release over it. The
drag sensors map the drag onto a plane (`PlaneSensor`), about an axis
(`CylinderSensor`) or about a point (`SphereSensor`), each through the first
hit, and send `trackPoint_changed` and their translation or rotation; with
`autoOffset` a drag carries on from where the last one ended. `axisRotation`
turns a plane or cylinder sensor's own coordinates.

`touchTime` is the sensor's :meth:`~vrml.x3d.timing.Timed.now` unless
`pointerRelease` is given a time.
"""

from __future__ import annotations

import math
from typing import Any, NamedTuple, Optional

import numpy as np
from numpy.typing import ArrayLike

from vrml.x3d import interpolation, timing
from vrml.x3d import nodes as x3d

__all__ = ['POINTING', 'CylinderSensor', 'Hit', 'PlaneSensor', 'Pointing', 'Ray',
           'SphereSensor', 'TouchSensor']


class Hit(NamedTuple):
    """Where the pointer meets the sensor's geometry, in the sensor's coordinates"""

    point: ArrayLike
    normal: Optional[ArrayLike] = None
    texCoord: Optional[ArrayLike] = None


class Ray(NamedTuple):
    """The pointer's bearing, in the sensor's coordinates"""

    origin: ArrayLike
    direction: ArrayLike


def _vector(value: ArrayLike) -> np.ndarray:
    return np.asarray(value, dtype=np.float64).ravel()[:3]


def _turning(rotation: ArrayLike) -> np.ndarray:
    """The column-vector matrix of an X3D rotation (axis, angle)"""
    found = np.asarray(rotation, dtype=np.float64).ravel()
    axis, angle = found[:3], float(found[3])
    length = np.linalg.norm(axis)
    if length == 0 or angle == 0:
        return np.identity(3)
    x, y, z = axis / length
    c, s, t = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


def _clamped(value: float, minimum: float, maximum: float) -> float:
    """`value` within [minimum, maximum], or free where the minimum is past the maximum"""
    if minimum > maximum:
        return value
    return min(max(value, minimum), maximum)


class Pointing(timing.Timed):
    """What every pointing-device sensor does: over, pressed, released"""

    enabled: Any
    isOver: Any
    isActive: Any

    def over(self) -> bool:
        """Whether the pointer was over the sensor's geometry when last told"""
        return bool(self.__dict__.get('_over', False))

    def active(self) -> bool:
        """Whether a press on the sensor's geometry is held"""
        return bool(self.__dict__.get('_active', False))

    def pointerOver(self, hit: Optional[Hit]) -> None:
        """The pointer has moved: onto the sensor's geometry at `hit`, or off it"""
        if not self.enabled:
            return
        over = hit is not None
        if over != self.over():
            self.__dict__['_over'] = over
            self.isOver = over
        if hit is not None:
            self.hit(hit)

    def hit(self, hit: Hit) -> None:
        """The pointer is over the geometry at `hit`"""

    def pointerPress(self, hit: Hit, ray: Ray) -> None:
        """The primary button has gone down with the pointer on the geometry at `hit`"""
        if not self.enabled or self.active():
            return
        self.__dict__['_active'] = True
        self.isActive = True
        self.start(hit, ray)

    def start(self, hit: Hit, ray: Ray) -> None:
        """A press has begun at `hit`"""

    def pointerDrag(self, hit: Optional[Hit], ray: Ray) -> None:
        """The pointer has moved with the button held: over the geometry at `hit` or not"""
        if not self.active():
            return
        if hit is not None:
            self.hit(hit)
        self.drag(ray)

    def drag(self, ray: Ray) -> None:
        """The held pointer's bearing is now `ray`"""

    def pointerRelease(self, over: bool, now: Optional[float] = None) -> None:
        """The button has come up, with the pointer over the geometry or not"""
        if not self.active():
            return
        self.__dict__['_active'] = False
        self.isActive = False
        self.end(over, self.now() if now is None else float(now))

    def end(self, over: bool, now: float) -> None:
        """A press has ended at `now`"""


class TouchSensor(Pointing, x3d.TouchSensor):
    """A click on the geometry, and where the pointer is on it"""

    def hit(self, hit: Hit) -> None:
        self.hitPoint_changed = _vector(hit.point)
        if hit.normal is not None:
            self.hitNormal_changed = _vector(hit.normal)
        if hit.texCoord is not None:
            self.hitTexCoord_changed = np.asarray(hit.texCoord, dtype=np.float64).ravel()[:2]

    def end(self, over: bool, now: float) -> None:
        if over:
            self.touchTime = now


class Dragging(Pointing):
    """A drag sensor: the press's first hit, and the offset a drag ends at"""

    autoOffset: Any

    def turning(self) -> np.ndarray:
        """The column-vector rotation from the sensor's turned coordinates to its own"""
        return _turning(getattr(self, 'axisRotation', (0.0, 0.0, 1.0, 0.0)))

    def into(self, point: ArrayLike) -> np.ndarray:
        """`point` (or a direction) in the sensor's turned coordinates"""
        return np.asarray(self.turning().T @ _vector(point))

    def end(self, _over: bool, _now: float) -> None:
        last = self.__dict__.get('_last')
        if self.autoOffset and last is not None:
            self.offset = last


class PlaneSensor(Dragging, x3d.PlaneSensor):
    """A drag across the plane through the first hit, parallel to z=0"""

    def start(self, hit: Hit, _ray: Ray) -> None:
        self.__dict__.update(_first=self.into(hit.point), _last=None)

    def drag(self, ray: Ray) -> None:
        first = self.__dict__['_first']
        origin, direction = self.into(ray.origin), self.into(ray.direction)
        if abs(direction[2]) < 1e-12:
            return
        track = origin + direction * ((first[2] - origin[2]) / direction[2])
        moved = self.into(self.offset) + track - first
        moved[0] = _clamped(moved[0], self.minPosition[0], self.maxPosition[0])
        moved[1] = _clamped(moved[1], self.minPosition[1], self.maxPosition[1])
        turning = self.turning()
        self.trackPoint_changed = turning @ track
        self.translation_changed = turning @ moved
        self.__dict__['_last'] = self.translation_changed


def _angle_about_y(point: np.ndarray) -> float:
    """The angle a rotation about +y turns (1, 0, 0) through to reach `point`'s direction"""
    return math.atan2(-point[2], point[0])


class CylinderSensor(Dragging, x3d.CylinderSensor):
    """A drag about the y axis: round a cylinder, or across a disk seen along the axis"""

    def start(self, hit: Hit, ray: Ray) -> None:
        first = self.into(hit.point)
        bearing = self.into(ray.direction)
        length = np.linalg.norm(bearing)
        tilt = math.acos(min(1.0, abs(bearing[1]) / length)) if length else math.pi / 2
        self.__dict__.update(_first=first, _disk=tilt < float(self.diskAngle), _last=None,
                             _radius=math.hypot(first[0], first[2]),
                             _bearing=_angle_about_y(first), _turned=0.0)

    def _track(self, origin: np.ndarray, direction: np.ndarray) -> Optional[np.ndarray]:
        first = self.__dict__['_first']
        if self.__dict__['_disk']:
            if abs(direction[1]) < 1e-12:
                return None
            return np.asarray(origin + direction * ((first[1] - origin[1]) / direction[1]))
        radius = self.__dict__['_radius']
        a = direction[0] ** 2 + direction[2] ** 2
        b = 2.0 * (origin[0] * direction[0] + origin[2] * direction[2])
        c = origin[0] ** 2 + origin[2] ** 2 - radius ** 2
        if a < 1e-12:
            return None
        root = b * b - 4.0 * a * c
        if root < 0:
            # The nearest the ray comes to the axis.
            return np.asarray(origin + direction * (-b / (2.0 * a)))
        return np.asarray(origin + direction * ((-b - math.sqrt(root)) / (2.0 * a)))

    def drag(self, ray: Ray) -> None:
        track = self._track(self.into(ray.origin), self.into(ray.direction))
        if track is None:
            return
        # The turn is added up a step at a time, each the shorter way round,
        # so a drag across the half turn carries on rather than jumping back.
        bearing = _angle_about_y(track)
        step = math.remainder(bearing - self.__dict__['_bearing'], 2.0 * math.pi)
        self.__dict__.update(_bearing=bearing, _turned=self.__dict__['_turned'] + step)
        angle = _clamped(float(self.offset) + self.__dict__['_turned'],
                         float(self.minAngle), float(self.maxAngle))
        turning = self.turning()
        self.trackPoint_changed = turning @ track
        self.rotation_changed = np.append(turning @ np.array([0.0, 1.0, 0.0]), angle)
        self.__dict__['_last'] = angle


def _quaternion_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The unit quaternion (x, y, z, w) turning direction `a` onto direction `b`"""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    cross, dot = np.cross(a, b), float(np.dot(a, b))
    if dot < -1.0 + 1e-9:
        axis = np.cross(a, (1.0, 0.0, 0.0))
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, (0.0, 1.0, 0.0))
        axis = axis / np.linalg.norm(axis)
        return np.append(axis, 0.0)
    found = np.append(cross, 1.0 + dot)
    return np.asarray(found / np.linalg.norm(found))


class SphereSensor(Dragging, x3d.SphereSensor):
    """A drag over the sphere about the sensor's origin through the first hit"""

    def start(self, hit: Hit, _ray: Ray) -> None:
        first = _vector(hit.point)
        self.__dict__.update(_first=first, _radius=float(np.linalg.norm(first)), _last=None)

    def drag(self, ray: Ray) -> None:
        radius = self.__dict__['_radius']
        if radius <= 0:
            return
        origin, direction = _vector(ray.origin), _vector(ray.direction)
        direction = direction / np.linalg.norm(direction)
        along = -float(np.dot(origin, direction))
        nearest = origin + direction * along
        gap = radius ** 2 - float(np.dot(nearest, nearest))
        if gap >= 0:
            track = origin + direction * (along - math.sqrt(gap))
        else:
            track = nearest * (radius / np.linalg.norm(nearest))
        turned = interpolation.compose(_quaternion_between(self.__dict__['_first'], track),
                          interpolation.quaternion_of(self.offset))
        self.trackPoint_changed = track
        self.rotation_changed = interpolation.rotation_of(turned)
        self.__dict__['_last'] = self.rotation_changed


#: Each pointing-device sensor class by its X3D name.
POINTING: "dict[str, type]" = {cls.PROTO: cls for cls in (
    CylinderSensor, PlaneSensor, SphereSensor, TouchSensor)}
