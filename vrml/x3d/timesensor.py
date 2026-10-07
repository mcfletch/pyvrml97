"""X3D's TimeSensor, advanced by whoever keeps time -- no clock of its own

The sensor (ISO/IEC 19775-1, 8.4.1) runs from `startTime` for one
`cycleInterval`, or cycle after cycle where `loop` is true, until `stopTime`
where that is later than `startTime`. :meth:`TimeSensor.advance` takes the
time and sends what the sensor sends then:

- `isActive` as it starts and stops; a sensor whose single cycle ended before
  it was first advanced does not start.
- `cycleTime` at the start of each cycle, the first included.
- `fraction_changed` (the part of the current cycle gone by, 1 at the end of a
  single cycle), `time` and `elapsedTime` (the time it has run, pauses left
  out) while it runs.
- `isPaused` as it pauses at `pauseTime` and resumes at `resumeTime`, each
  taking effect when it is the later of the two and has passed. Nothing else
  is sent while it is paused. :meth:`TimeSensor.pause` and
  :meth:`TimeSensor.resume` set those fields to the sensor's time.

`startTime`, `cycleInterval` and `loop` are read as it starts; changing them
while it runs changes nothing until it starts again. A sensor that is not
`enabled` stops.

:attr:`TimeSensor.rate`, which is not an X3D field, is how fast the cycles
run against the clock: 2 runs them at twice the speed, 0 holds them, and a
negative rate runs them backwards. A change of rate carries on from where
the cycle is. `elapsedTime` stays the clock time the sensor has run.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Optional

from vrml.x3d import nodes as x3d
from vrml.x3d import timing

__all__ = ['Run', 'TimeSensor']


@dataclasses.dataclass
class Run:
    """One run of a sensor: the fields it started with, and how far it has got"""

    start: float
    cycle: float
    loop: bool
    #: The clock time accounted for so far.
    last: float
    #: The cycle time run, in seconds: the clock time at the sensor's rate.
    progress: float = 0.0
    #: The clock time run, pauses left out.
    ran: float = 0.0
    #: When the pause in progress began, or None.
    pausedAt: Optional[float] = None
    #: The cycle last begun.
    count: int = -1

    def account(self, now: float, rate: float) -> None:
        """Run on to clock time `now` at `rate`"""
        step = now - self.last
        self.progress += step * rate
        self.ran += step
        self.last = now


class TimeSensor(timing.Timed, x3d.TimeSensor):
    """A TimeSensor that runs as :meth:`advance` is called"""

    #: How fast the cycles run against the clock; not an X3D field.
    rate: float = 1.0

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
        if not self.enabled or float(self.cycleInterval) <= 0 or now < start:
            return False
        if stop > start and now >= stop:
            return False
        if not self.loop and now >= start + float(self.cycleInterval):
            return False
        return self.__dict__.get('_ended') != start

    def advance(self, now: float) -> bool:
        """Send what the sensor sends at `now`; whether it sent anything"""
        now = float(now)
        if not self.running():
            if not self._starts(now):
                return False
            start = float(self.startTime)
            self.__dict__['_run'] = Run(start, float(self.cycleInterval), bool(self.loop), start)
            self.isActive = True
        run: Run = self.__dict__['_run']
        if not self.enabled:
            return self._stop(now, run, None)
        stop = float(self.stopTime)
        if stop > run.start and now >= stop:
            return self._stop(stop, run, None)
        if self._pausing(now, run):
            return True
        if run.pausedAt is not None:
            return False
        run.account(now, float(self.rate))
        if not run.loop and not 0.0 <= run.progress < run.cycle:
            return self._stop(now, run, 1.0 if run.progress > 0 else 0.0)
        count = int(math.floor(run.progress / run.cycle))
        if count != run.count:
            run.count = count
            self.cycleTime = now
        self._send(now, run.ran, run.progress / run.cycle - count)
        return True

    def _pausing(self, now: float, run: Run) -> bool:
        """Pause or resume as `pauseTime` and `resumeTime` say; whether either happened"""
        pause, resume = float(self.pauseTime), float(self.resumeTime)
        if run.pausedAt is None and pause > resume and run.start < pause <= now:
            run.account(max(pause, run.last), float(self.rate))
            run.pausedAt = pause
            self.isPaused = True
            return True
        if run.pausedAt is not None and resume > pause and resume <= now:
            run.last = max(resume, run.last)
            run.pausedAt = None
            self.isPaused = False
        return False

    def _send(self, now: float, elapsed: float, fraction: float) -> None:
        self.fraction_changed = fraction
        self.time = now
        self.elapsedTime = elapsed

    def _stop(self, now: float, run: Run, fraction: Optional[float]) -> bool:
        """Stop at `now`, sending `fraction` (or the running one) as the last"""
        if run.pausedAt is None:
            run.account(max(now, run.last), float(self.rate))
            if fraction is None:
                fraction = run.progress / run.cycle - math.floor(run.progress / run.cycle)
            self._send(now, run.ran, fraction)
        del self.__dict__['_run']
        self.__dict__['_ended'] = run.start
        self.isActive = False
        return True
