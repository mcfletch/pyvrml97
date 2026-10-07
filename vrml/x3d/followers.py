"""X3D's followers: values that move toward a destination over time -- NumPy only

A chaser reaches each destination `duration` seconds after it is set: its
value is where it started plus each change of destination applied along a
smooth step, `(1 - cos(pi x)) / 2` of the way at `x` of the duration, so a
destination set while it is moving carries on from where it is. A damper
approaches its destination through `order` first-order filters in series,
each closing on the one before by `1 - exp(-dt / tau)` of the gap over a step
of `dt` seconds, and comes to rest within `tolerance` (an automatic one where
that is negative). Rotations are chased and damped as quaternions.

Nothing here keeps time. :meth:`Follower.advance` takes the time, moves the
value and sends it, and answers whether the follower is still moving;
`set_destination` stamps a change with :meth:`~vrml.x3d.timing.Timed.now`,
the time of the follower's scene. :meth:`Follower.wake` is called when a
follower starts to move, for whoever ticks it to begin.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np

from vrml.x3d import interpolation, timing
from vrml.x3d import nodes as x3d

__all__ = ['FOLLOWERS', 'Chaser', 'ColorChaser', 'ColorDamper', 'CoordinateChaser',
           'CoordinateDamper', 'Damper', 'Follower', 'OrientationChaser', 'OrientationDamper',
           'PositionChaser', 'PositionChaser2D', 'PositionDamper', 'PositionDamper2D',
           'ScalarChaser', 'ScalarDamper', 'TexCoordChaser2D', 'TexCoordDamper2D']

_IDENTITY = np.array([0.0, 0.0, 0.0, 1.0])


def _step(x: float) -> float:
    """The smooth step a chaser takes: 0 before, 1 after, cosine-eased between"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return (1.0 - math.cos(math.pi * x)) / 2.0


def _compose(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The quaternion turning by `b` and then by `a`"""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def _inverse(q: np.ndarray) -> np.ndarray:
    return np.array([-q[0], -q[1], -q[2], q[3]])


class Follower(timing.Timed):
    """What every follower does: start from its initial fields, retarget, advance

    A subclass gives the arithmetic of its kind of motion; :attr:`rotation`
    says the values are rotations, and :attr:`scalar` that each is one number.
    """

    rotation: ClassVar[bool] = False
    scalar: ClassVar[bool] = False

    initialValue: Any
    initialDestination: Any
    value_changed: Any
    isActive: Any

    # The values as the arithmetic holds them.

    def _held(self, value: Any) -> np.ndarray:
        if self.rotation:
            return interpolation.quaternion_of(np.asarray(value, np.float64).ravel()[:4])
        return np.array(value, dtype=np.float64)

    def _sent(self, value: np.ndarray) -> Any:
        if self.rotation:
            return interpolation.rotation_of(value)
        return float(value) if self.scalar else value

    def _ready(self) -> None:
        """Start from the initial fields, the first time the follower is used"""
        if '_state' in self.__dict__:
            return
        self.__dict__['_state'] = True
        self._reset(self._held(self.initialValue))
        destination = self._held(self.initialDestination)
        if not self._same(destination, self._current()):
            self._retarget(destination, self.now())

    def _same(self, a: np.ndarray, b: np.ndarray) -> bool:
        if self.rotation:
            return abs(float(np.dot(a, b))) > 1.0 - 1e-9
        return bool(a.shape == b.shape and np.allclose(a, b))

    # What a subclass gives.

    def _reset(self, value: np.ndarray) -> None:
        raise NotImplementedError

    def _current(self) -> np.ndarray:
        raise NotImplementedError

    def _retarget(self, destination: np.ndarray, now: float) -> None:
        raise NotImplementedError

    def _advance(self, now: float) -> bool:
        raise NotImplementedError

    # The events.

    def moving(self) -> bool:
        """Whether the value is still moving toward its destination"""
        return bool(self.__dict__.get('_moving', False))

    def _moved(self, moving: bool) -> None:
        if moving != self.moving():
            self.__dict__['_moving'] = moving
            self.isActive = moving
            if moving:
                self.wake()

    def wake(self) -> None:
        """The follower has started to move: whoever ticks it begins to"""

    def on_set_destination(self, value: Any) -> None:
        self._ready()
        self._retarget(self._held(value), self.now())
        self._moved(True)

    def on_set_value(self, value: Any) -> None:
        self._ready()
        held = self._held(value)
        self._reset(held)
        self.value_changed = self._sent(held)
        self._moved(False)

    def advance(self, now: float) -> bool:
        """Move to where the follower is at `now`, send it; whether it is still moving"""
        self._ready()
        moving = self._advance(float(now))
        self.value_changed = self._sent(self._current())
        self._moved(moving)
        return moving


class Chaser(Follower):
    """A chaser: each destination reached `duration` seconds after it is set"""

    duration: Any

    def _reset(self, value: np.ndarray) -> None:
        self.__dict__.update(_base=value, _destination=value, _changes=[], _value=value)

    def _current(self) -> np.ndarray:
        found: np.ndarray = self.__dict__['_value']
        return found

    def _retarget(self, destination: np.ndarray, now: float) -> None:
        last = self.__dict__['_destination']
        change = (_compose(destination, _inverse(last)) if self.rotation
                  else destination - last)
        self.__dict__['_changes'].append((now, change))
        self.__dict__['_destination'] = destination

    def _advance(self, now: float) -> bool:
        duration = max(float(self.duration), 1e-9)
        base = self.__dict__['_base']
        pending = []
        for start, change in self.__dict__['_changes']:
            if now - start >= duration:
                base = _compose(change, base) if self.rotation else base + change
            else:
                pending.append((start, change))
        value = base
        for start, change in pending:
            share = _step((now - start) / duration)
            value = (_compose(interpolation.slerp(_IDENTITY, change, share), value) if self.rotation
                     else value + change * share)
        self.__dict__.update(_base=base, _changes=pending, _value=value)
        return bool(pending)


class Damper(Follower):
    """A damper: `order` first-order filters of time constant `tau` in series"""

    order: Any
    tau: Any
    tolerance: Any

    def _reset(self, value: np.ndarray) -> None:
        self.__dict__.update(_stages=[value] * max(int(self.order), 1), _destination=value,
                             _last=None)

    def _current(self) -> np.ndarray:
        if int(self.order) <= 0:
            found: np.ndarray = self.__dict__['_destination']
            return found
        last: np.ndarray = self.__dict__['_stages'][-1]
        return last

    def _retarget(self, destination: np.ndarray, now: float) -> None:
        if self.__dict__.get('_last') is None:
            self.__dict__['_last'] = now
        self.__dict__['_destination'] = destination

    def _near(self, value: np.ndarray, destination: np.ndarray) -> bool:
        tolerance = float(self.tolerance)
        if self.rotation:
            gap = 2.0 * math.acos(min(1.0, abs(float(np.dot(value, destination)))))
            return gap <= (tolerance if tolerance >= 0 else 1e-4)
        gap = float(np.max(np.abs(value - destination))) if value.size else 0.0
        scale = float(np.max(np.abs(destination))) if destination.size else 0.0
        return gap <= (tolerance if tolerance >= 0 else 1e-4 * max(1.0, scale))

    def _advance(self, now: float) -> bool:
        destination = self.__dict__['_destination']
        if int(self.order) <= 0:
            self.__dict__['_stages'] = [destination]
            return False
        last = self.__dict__.get('_last')
        step = 0.0 if last is None else max(now - last, 0.0)
        self.__dict__['_last'] = now
        tau = float(self.tau)
        keep = math.exp(-step / tau) if tau > 0 else 0.0
        stages = []
        target = destination
        for stage in self.__dict__['_stages']:
            moved = (interpolation.slerp(target, stage, keep) if self.rotation
                     else target + (stage - target) * keep)
            stages.append(moved)
            target = moved
        if self._near(stages[-1], destination):
            stages = [destination] * len(stages)
            self.__dict__['_stages'] = stages
            return False
        self.__dict__['_stages'] = stages
        return True


class ColorChaser(Chaser, x3d.ColorChaser):
    """A colour chased to its destination"""


class ColorDamper(Damper, x3d.ColorDamper):
    """A colour damped toward its destination"""


class CoordinateChaser(Chaser, x3d.CoordinateChaser):
    """Points chased to their destinations"""


class CoordinateDamper(Damper, x3d.CoordinateDamper):
    """Points damped toward their destinations"""


class OrientationChaser(Chaser, x3d.OrientationChaser):
    """A rotation chased to its destination"""

    rotation = True


class OrientationDamper(Damper, x3d.OrientationDamper):
    """A rotation damped toward its destination"""

    rotation = True


class PositionChaser(Chaser, x3d.PositionChaser):
    """A position chased to its destination"""


class PositionDamper(Damper, x3d.PositionDamper):
    """A position damped toward its destination"""


class PositionChaser2D(Chaser, x3d.PositionChaser2D):
    """A 2D position chased to its destination"""


class PositionDamper2D(Damper, x3d.PositionDamper2D):
    """A 2D position damped toward its destination"""


class ScalarChaser(Chaser, x3d.ScalarChaser):
    """A number chased to its destination"""

    scalar = True


class ScalarDamper(Damper, x3d.ScalarDamper):
    """A number damped toward its destination"""

    scalar = True


class TexCoordChaser2D(Chaser, x3d.TexCoordChaser2D):
    """Texture coordinates chased to their destinations"""


class TexCoordDamper2D(Damper, x3d.TexCoordDamper2D):
    """Texture coordinates damped toward their destinations"""


#: Each follower class by its X3D name.
FOLLOWERS: "dict[str, type]" = {cls.PROTO: cls for cls in (
    ColorChaser, ColorDamper, CoordinateChaser, CoordinateDamper, OrientationChaser,
    OrientationDamper, PositionChaser, PositionDamper, PositionChaser2D, PositionDamper2D,
    ScalarChaser, ScalarDamper, TexCoordChaser2D, TexCoordDamper2D,
)}
