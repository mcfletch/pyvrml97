"""X3D's TimeSensor, advanced by whoever keeps time

The sensor (ISO/IEC 19775-1, 8.4.1) runs from `startTime` for one
`cycleInterval`, or cycle after cycle where `loop` is true, until `stopTime`
where that is later than `startTime`. :meth:`TimeSensor.advance` takes the
time and sends what the sensor sends then:

- `isActive` as it starts and stops; a sensor whose single cycle ended before
  it was first advanced does not start.
- `cycleTime`, the time the cycle under way began, when an advance finds a
  new cycle under way, the first included; one, however many cycles passed
  since the last advance.
- `fraction_changed` (the part of the current cycle gone by; 1 where a cycle
  has just ended), `time` and `elapsedTime` (the time it has run, pauses left
  out) while it runs. The last it sends are at the time it stopped: the end
  of its last cycle, or `stopTime`.
- `isPaused` as it pauses at `pauseTime` and resumes at `resumeTime`, each
  taking effect when it is the later of the two and has passed. Nothing else
  is sent while it is paused. :meth:`TimeSensor.pause` and
  :meth:`TimeSensor.resume` set those fields to the sensor's time.

While it runs, a `startTime` set is dropped (8.2.4.4). `loop` and
`cycleInterval` are read at each advance: with `loop` false it stops at the
end of the cycle under way, and a new `cycleInterval` carries the cycle on
from the time it has run, completing it where that is already longer. A
`stopTime` set between `startTime` and now stops it at `stopTime`. A sensor
that is not `enabled` stops.

:attr:`TimeSensor.rate`, which is not an X3D field, is how fast the cycles
run against the clock: 2 runs them at twice the speed, 0 holds them, and a
negative rate runs them backwards. A change of rate carries on from where
the cycle is. `elapsedTime` stays the clock time the sensor has run.

:class:`Clocked` is that behaviour for any time-dependent node, given its
cycle, its rate and what it sends; a MovieTexture's is the movie's duration
and its `speed` (:mod:`vrml.x3d.media`).
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any, Optional

from vrml import fieldtypes
from vrml.x3d import nodes as x3d
from vrml.x3d import timing

__all__ = ['Clocked', 'Run', 'StartTime', 'TimeSensor']


@dataclasses.dataclass
class Run:
    """One run of a sensor: when it started, and how far it has got"""

    start: float
    #: The clock time accounted for so far.
    last: float
    #: The cycle time run, in seconds: the clock time at the sensor's rate.
    progress: float = 0.0
    #: The clock time run, pauses left out.
    ran: float = 0.0
    #: The cycle time at which the cycle under way began.
    began: float = 0.0
    #: The rate the cycle time last ran at.
    rate: float = 1.0
    #: When the pause in progress began, or None.
    pausedAt: Optional[float] = None
    #: Whether a `cycleTime` has been sent.
    counted: bool = False

    def account(self, now: float, rate: float) -> None:
        """Run on to clock time `now` at `rate`"""
        step = now - self.last
        self.progress += step * rate
        self.ran += step
        self.last = now
        self.rate = rate

    def clock(self, progress: float) -> float:
        """The clock time at which the run reached cycle time `progress`"""
        if not self.rate:
            return self.last
        return self.last - (self.progress - progress) / self.rate


class StartTime(fieldtypes.SFTime):
    """`startTime`, which keeps its value while the node runs (8.2.4.4)"""

    fieldType = 'SFTime'

    def __set__(self, client: Any, value: Any) -> None:
        if not client.running():
            super().__set__(client, value)

    def fset(self, client: Any, value: Any, notify: bool = True) -> Any:
        if client.running():
            return self.fget(client)
        return super().fset(client, value, notify)


class Clocked(timing.Timed):
    """A time-dependent node that runs as :meth:`advance` is called

    A subclass gives its cycle (:meth:`cycle`), how fast it runs
    (:meth:`clockRate`), whether it may run (:meth:`clockEnabled`), and
    what it sends as a cycle begins (:meth:`_cycleBegan`) and as it runs
    (:meth:`_send`).
    """

    startTime: Any
    stopTime: Any
    pauseTime: Any
    resumeTime: Any
    loop: Any
    isActive: Any
    isPaused: Any

    def cycle(self) -> float:
        """The length of one cycle, in seconds of cycle time"""
        raise NotImplementedError('%s must give its cycle' % type(self).__name__)

    def clockRate(self) -> float:
        """How fast the cycles run against the clock"""
        return 1.0

    def clockEnabled(self) -> bool:
        """Whether the node may run"""
        return True

    def _cycleBegan(self, when: float) -> None:
        """A cycle began at clock time `when`"""

    def running(self) -> bool:
        """Whether the sensor is active"""
        return '_run' in self.__dict__

    def paused(self) -> bool:
        """Whether the sensor is active and paused"""
        run = self.__dict__.get('_run')
        return run is not None and run.pausedAt is not None

    def pause(self, now: Optional[float] = None) -> None:
        """Pause the sensor at `now` (its :meth:`now` where None): `pauseTime` is set to it"""
        self.pauseTime = self.now() if now is None else float(now)

    def resume(self, now: Optional[float] = None) -> None:
        """Resume the sensor at `now` (its :meth:`now` where None): `resumeTime` is set to it"""
        self.resumeTime = self.now() if now is None else float(now)

    def _starts(self, now: float) -> bool:
        """Whether the sensor would start at `now`"""
        start, stop = float(self.startTime), float(self.stopTime)
        if not self.clockEnabled() or self.cycle() <= 0 or now < start:
            return False
        if stop > start and now >= stop:
            return False
        if not self.loop and now >= start + self.cycle() / max(abs(self.clockRate()), 1e-12):
            return False
        return self.__dict__.get('_ended') != start

    def advance(self, now: float) -> bool:
        """Send what the sensor sends at `now`; whether it sent anything"""
        now = float(now)
        if not self.running():
            if not self._starts(now):
                return False
            start = float(self.startTime)
            begun = Run(start, start)
            if self.clockRate() < 0:
                # Run backwards, the first cycle begins at its end.
                begun.began = -self.cycle()
            self.__dict__['_run'] = begun
            self.isActive = True
        run: Run = self.__dict__['_run']
        if not self.clockEnabled():
            return self._stop(now, run, None)
        stop = float(self.stopTime)
        if stop > run.start and now >= stop:
            return self._stop(stop, run, None)
        if self._pausing(now, run):
            return True
        if run.pausedAt is not None:
            return False
        run.account(now, self.clockRate())
        cycle = self.cycle()
        under_way = run.began if run.counted else None
        ended = False
        gone = run.progress - run.began
        if cycle > 0 and (gone > cycle or (gone == cycle and run.rate >= 0)):
            if not self.loop:
                return self._stop(run.clock(run.began + cycle), run, 1.0)
            # Every cycle passed since the last advance at once, however many
            # a jump of the clock skipped.
            run.began += cycle * math.floor((run.progress - run.began) / cycle)
            ended = True
        if cycle > 0 and run.progress < run.began:
            if not self.loop:
                return self._stop(run.clock(run.began), run, 0.0)
            run.began -= cycle * math.ceil((run.began - run.progress) / cycle)
        if run.began != under_way:
            # One cycleTime for the cycle under way, however many have passed
            # since the last advance; a cycle run backwards begins at its end.
            run.counted = True
            self._cycleBegan(run.clock(run.began if run.rate >= 0 else run.began + cycle))
        fraction = (run.progress - run.began) / cycle if cycle > 0 else 0.0
        if fraction == 0.0 and ended:
            fraction = 1.0
        self._send(now, run.ran, fraction)
        return True

    def runFraction(self) -> Optional[float]:
        """The part of the cycle under way gone by, as far as the run has been accounted; None when not running"""
        run = self.__dict__.get('_run')
        if run is None:
            return None
        cycle = self.cycle()
        if cycle <= 0:
            return 0.0
        gone = (run.progress - run.began) / cycle
        if self.loop:
            return gone % 1.0 if gone > 1.0 else max(gone, 0.0)
        return min(max(gone, 0.0), 1.0)

    def _pausing(self, now: float, run: Run) -> bool:
        """Pause or resume as `pauseTime` and `resumeTime` say; whether either happened"""
        pause, resume = float(self.pauseTime), float(self.resumeTime)
        if run.pausedAt is None and pause > resume and run.start < pause <= now:
            run.account(max(pause, run.last), self.clockRate())
            run.pausedAt = pause
            self.isPaused = True
            return True
        if run.pausedAt is not None and resume > pause and resume <= now:
            run.last = max(resume, run.last)
            run.pausedAt = None
            self.isPaused = False
        return False

    def _send(self, now: float, elapsed: float, fraction: float) -> None:
        """Send what the node sends while it runs: `fraction` of the cycle gone by at `now`"""
        raise NotImplementedError('%s must send what it sends' % type(self).__name__)

    def _stop(self, now: float, run: Run, fraction: Optional[float]) -> bool:
        """Stop at clock time `now`, sending `fraction` (or the running one) as the last"""
        if run.pausedAt is None:
            if now >= run.last:
                run.account(now, self.clockRate())
                ran = run.ran
            else:
                ran = run.ran - (run.last - now)
            if fraction is None:
                cycle = self.cycle()
                fraction = (run.progress - run.began) / cycle % 1.0 if cycle > 0 else 0.0
            self._send(now, ran, fraction)
        del self.__dict__['_run']
        self.__dict__['_ended'] = run.start
        self.isActive = False
        return True


class TimeSensor(Clocked, x3d.TimeSensor):
    """A TimeSensor that runs as :meth:`advance` is called"""

    startTime = StartTime('startTime', 1, 0.0)
    #: How fast the cycles run against the clock; not an X3D field.
    rate: float = 1.0

    def cycle(self) -> float:
        """`cycleInterval`"""
        return float(self.cycleInterval)

    def clockRate(self) -> float:
        """:attr:`rate`"""
        return float(self.rate)

    def clockEnabled(self) -> bool:
        """`enabled`"""
        return bool(self.enabled)

    def _cycleBegan(self, when: float) -> None:
        self.cycleTime = when

    def _send(self, now: float, elapsed: float, fraction: float) -> None:
        self.fraction_changed = fraction
        self.time = now
        self.elapsedTime = elapsed
