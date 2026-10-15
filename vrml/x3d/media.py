"""X3D's MovieTexture timing, advanced by whoever keeps time -- no decoding

A MovieTexture (ISO/IEC 19775-1, 18.4.3) runs as a TimeSensor does
(:class:`~vrml.x3d.timesensor.Clocked`): from `startTime`, once through the
movie or round and round where `loop` is true, until `stopTime`, paused at
`pauseTime` and resumed at `resumeTime`, sending `isActive`, `isPaused` and
`elapsedTime`. Its cycle is the movie's duration, which whoever decodes the
movie gives with :meth:`MovieTexture.setDuration`, and it runs at `speed`:
2 twice as fast, a negative speed backwards.

:meth:`MovieTexture.position` is the time into the movie that is shown: the
start before the movie first plays (its end for a negative `speed`), and
where it stopped once it has stopped.
"""

from __future__ import annotations

from vrml.x3d import nodes as x3d
from vrml.x3d import timesensor

__all__ = ['MovieTexture']


class MovieTexture(timesensor.Clocked, x3d.MovieTexture):
    """A MovieTexture that runs as :meth:`advance` is called"""

    PROTO = 'MovieTexture'
    startTime = timesensor.StartTime('startTime', 1, 0.0)

    def setDuration(self, seconds: float) -> None:
        """The movie is `seconds` long; sends `duration_changed`"""
        self.__dict__['_duration'] = float(seconds)
        self.duration_changed = float(seconds)

    def cycle(self) -> float:
        """The movie's duration; 0 until it is known"""
        return float(self.__dict__.get('_duration', 0.0))

    def clockRate(self) -> float:
        """`speed`"""
        return float(self.speed)

    def _send(self, now: float, elapsed: float, fraction: float) -> None:  # noqa: ARG002 - the base method's signature is kept
        self.__dict__['_fraction'] = fraction
        self.elapsedTime = elapsed

    def position(self) -> float:
        """The time into the movie that is shown, in seconds"""
        fraction = self.runFraction()
        if fraction is None:
            fraction = self.__dict__.get('_fraction')
        if fraction is None:
            fraction = 1.0 if self.clockRate() < 0 else 0.0
        return float(fraction) * self.cycle()
