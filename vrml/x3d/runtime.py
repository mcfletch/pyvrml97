"""X3D's event utilities, sequencers, interpolators and key sensors, with their behaviour

The declarations in `vrml.x3d.nodes` carry fields only. The classes here add
what each node sends for what it receives: setting an inputOnly event on a
node calls its `on_<event>` method, and the outputs that method sets are
forwarded along routes as any field change is. Nothing here draws or reads a
device; :class:`KeySensor` is told of keys by whoever has a keyboard.

`PROTOTYPES` maps each X3D name to its class here, to pass as a reader's
`prototypes=` (merged with an engine's own). A `TimeTrigger` sends the time
of its scene (:meth:`~vrml.x3d.timing.Timed.now`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from vrml.x3d import followers, interpolation, loadsensor, pointing, sensors, timesensor, timing
from vrml.x3d import nodes as x3d

__all__ = ['ACTION_KEYS', 'MODIFIER_KEYS', 'PROTOTYPES']

#: The action keys X3D numbers (ISO/IEC 19775-1, 21.4.1).
ACTION_KEYS = {
    **{'F%d' % number: number for number in range(1, 13)},
    'HOME': 13, 'END': 14, 'PGUP': 15, 'PGDN': 16,
    'UP': 17, 'DOWN': 18, 'LEFT': 19, 'RIGHT': 20,
}
#: The modifier keys, and the output each sets while it is held.
MODIFIER_KEYS = {'SHIFT': 'shiftKey', 'CONTROL': 'controlKey', 'ALT': 'altKey'}


class BooleanFilter(x3d.BooleanFilter):
    """Sends true on `inputTrue`, false on `inputFalse`, and its negation on `inputNegate`"""

    def on_set_boolean(self, value: Any) -> None:
        if value:
            self.inputTrue = True
        else:
            self.inputFalse = False
        self.inputNegate = not value


class BooleanToggle(x3d.BooleanToggle):
    """Flips `toggle` for each true it receives"""

    def on_set_boolean(self, value: Any) -> None:
        if value:
            self.toggle = not self.toggle


class BooleanTrigger(x3d.BooleanTrigger):
    """Sends true for each time it receives"""

    def on_set_triggerTime(self, _time: Any) -> None:
        self.triggerTrue = True


class IntegerTrigger(x3d.IntegerTrigger):
    """Sends `integerKey` for each true it receives"""

    def on_set_boolean(self, value: Any) -> None:
        if value:
            self.triggerValue = self.integerKey


class TimeTrigger(timing.Timed, x3d.TimeTrigger):
    """Sends the time of its scene (:meth:`now`) for each boolean it receives"""

    def on_set_boolean(self, _value: Any) -> None:
        self.triggerTime = self.now()


class Sequencer:
    """What both sequencers do: the value of the last key a fraction has reached

    `next` and `previous` step to the next or previous key, wrapping at the
    ends. A value is sent when the key chosen changes.
    """

    key: Any
    keyValue: Any
    value_changed: Any
    #: What a key's value is sent as.
    sent: Callable[[Any], Any] = staticmethod(lambda value: value)

    def _choose(self, index: int) -> None:
        if index != self.__dict__.get('_chosen'):
            self.__dict__['_chosen'] = index
            self.value_changed = self.sent(self.keyValue[index])

    def _count(self) -> int:
        return min(len(self.key), len(self.keyValue))

    def on_set_fraction(self, value: Any) -> None:
        count = self._count()
        if not count:
            return
        index = 0
        for position in range(count):
            if float(self.key[position]) <= float(value):
                index = position
        self._choose(index)

    def _step(self, by: int) -> None:
        count = self._count()
        if count:
            self._choose((self.__dict__.get('_chosen', 0) + by) % count)

    def on_next(self, value: Any) -> None:
        if value:
            self._step(1)

    def on_previous(self, value: Any) -> None:
        if value:
            self._step(-1)


class BooleanSequencer(Sequencer, x3d.BooleanSequencer):
    """A boolean for each key"""

    sent = staticmethod(bool)


class IntegerSequencer(Sequencer, x3d.IntegerSequencer):
    """An integer for each key"""

    sent = staticmethod(int)


class KeySensor(x3d.KeySensor):
    """The keys pressed and released while it is enabled

    `keyDown` and `keyUp` take a key's name: one character for a printable
    key, a name in :data:`ACTION_KEYS` or :data:`MODIFIER_KEYS` for the
    others. `isActive` is true while any key is held.
    """

    def _held(self) -> "set[str]":
        found: "set[str]" = self.__dict__.setdefault('_keysHeld', set())
        return found

    def keyDown(self, name: str) -> None:
        """A key pressed"""
        if not self.enabled:
            return
        held = self._held()
        if not held:
            self.isActive = True
        held.add(name)
        if name in MODIFIER_KEYS:
            setattr(self, MODIFIER_KEYS[name], True)
        elif name in ACTION_KEYS:
            self.actionKeyPress = ACTION_KEYS[name]
        else:
            self.keyPress = name

    def keyUp(self, name: str) -> None:
        """A key released"""
        if not self.enabled:
            return
        held = self._held()
        held.discard(name)
        if name in MODIFIER_KEYS:
            setattr(self, MODIFIER_KEYS[name], False)
        elif name in ACTION_KEYS:
            self.actionKeyRelease = ACTION_KEYS[name]
        else:
            self.keyRelease = name
        if not held:
            self.isActive = False


class StringSensor(x3d.StringSensor):
    """Text typed while it is enabled

    `typed` takes one character: a return ('\\n') ends the text, sending it
    as `finalText`; a backspace ('\\b') removes the last character where
    `deletionAllowed`; any other is added to `enteredText`. `isActive` is
    true from the first character to the return.
    """

    def _text(self) -> str:
        return str(self.__dict__.get('_typedText', ''))

    def typed(self, character: str) -> None:
        """A character typed"""
        if not self.enabled:
            return
        text = self._text()
        if character == '\n':
            if text or self.__dict__.get('isActive'):
                self.finalText = text
                self.__dict__['_typedText'] = ''
                self.enteredText = ''
                self.isActive = False
            return
        if character == '\b':
            if self.deletionAllowed and text:
                text = text[:-1]
            else:
                return
        else:
            if not self.__dict__.get('isActive'):
                self.isActive = True
            text += character
        self.__dict__['_typedText'] = text
        self.enteredText = text


class Interpolated:
    """An interpolator: `value_changed` is :meth:`evaluate` of each fraction it receives"""

    key: Any
    keyValue: Any
    value_changed: Any

    def evaluate(self, fraction: float) -> Any:
        """The value at `fraction`"""
        raise NotImplementedError('%s must evaluate its keys' % type(self).__name__)

    def on_set_fraction(self, value: Any) -> None:
        if len(self.key) and len(self.keyValue):
            self.value_changed = self.evaluate(float(value))


class PositionInterpolator2D(Interpolated, x3d.PositionInterpolator2D):
    """A 2D position, straight between keys"""

    def evaluate(self, fraction: float) -> Any:
        return interpolation.linear(self.key, self.keyValue, fraction)


class CoordinateInterpolator2D(Interpolated, x3d.CoordinateInterpolator2D):
    """A run of 2D points per key, straight between keys"""

    def evaluate(self, fraction: float) -> Any:
        per_key = max(len(self.keyValue) // len(self.key), 1)
        return interpolation.linear(self.key, self.keyValue[:per_key * len(self.key)],
                                    fraction, per_key=per_key)


class Splined(Interpolated):
    """A spline interpolator: X3D's Hermite spline through `keyValue`"""

    closed: Any
    keyVelocity: Any
    normalizeVelocity: Any

    def evaluate(self, fraction: float) -> Any:
        return interpolation.spline(self.key, self.keyValue, fraction, closed=bool(self.closed),
                                    velocities=self.keyVelocity,
                                    normalize=bool(self.normalizeVelocity))


class SplinePositionInterpolator(Splined, x3d.SplinePositionInterpolator):
    """A position on a spline through the key values"""


class SplinePositionInterpolator2D(Splined, x3d.SplinePositionInterpolator2D):
    """A 2D position on a spline through the key values"""


class SplineScalarInterpolator(Splined, x3d.SplineScalarInterpolator):
    """A number on a spline through the key values"""

    def evaluate(self, fraction: float) -> Any:
        return float(super().evaluate(fraction))


class SquadOrientationInterpolator(Interpolated, x3d.SquadOrientationInterpolator):
    """A rotation by spherical cubic interpolation of the key rotations"""

    def evaluate(self, fraction: float) -> Any:
        return interpolation.squad(self.key, self.keyValue, fraction)


class EaseInEaseOut(x3d.EaseInEaseOut):
    """A fraction eased out of and into each key (:func:`~vrml.x3d.interpolation.ease`)"""

    def on_set_fraction(self, value: Any) -> None:
        self.modifiedFraction_changed = interpolation.ease(self.key, self.easeInEaseOut, value)


#: Each class here by its X3D name.
PROTOTYPES: "dict[str, type]" = {
    cls.PROTO: cls for cls in (
        BooleanFilter, BooleanToggle, BooleanTrigger, IntegerTrigger, TimeTrigger,
        BooleanSequencer, IntegerSequencer, KeySensor, StringSensor,
        PositionInterpolator2D, CoordinateInterpolator2D, SplinePositionInterpolator,
        SplinePositionInterpolator2D, SplineScalarInterpolator, SquadOrientationInterpolator,
        EaseInEaseOut,
    )
}
PROTOTYPES.update(followers.FOLLOWERS)
PROTOTYPES.update(sensors.SENSORS)
PROTOTYPES.update(pointing.POINTING)
PROTOTYPES['TimeSensor'] = timesensor.TimeSensor
PROTOTYPES['LoadSensor'] = loadsensor.LoadSensor
