"""X3D's Sound component timing, advanced by whoever keeps time

Every sound source and processing node (ISO/IEC 19775-1, 16.3.6 and 16.3.7)
is time dependent (8.2.4): it runs from `startTime` until a `stopTime` later
than it, pauses at `pauseTime` and resumes at `resumeTime`, and sends
`isActive`, `isPaused` and `elapsedTime`, as a TimeSensor does
(:class:`~vrml.x3d.timesensor.Clocked`). A node that is not `enabled` stops.

- :class:`AudioClip` runs for its duration over its `pitch`, once or round
  and round where `loop` is true. Whoever decodes the clip gives the duration
  with :meth:`AudioClip.setDuration`; until then it does not start. A `pitch`
  set while the clip plays takes effect when it next starts (16.4.1).
- :class:`BufferAudioSource` runs for its buffer's duration over its rate,
  `playbackRate` times ``2 ** (detune / 1200)``. Its `buffer` holds its
  channels one after another (:meth:`BufferAudioSource.samples`); whoever
  holds the samples gives their shape with :meth:`BufferAudioSource.setBuffer`.
- The other sources and the processing nodes have no cycle: each runs until
  it is stopped.

`position()` is the time into the clip or buffer that is playing, in seconds.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

from vrml.x3d import nodes as x3d
from vrml.x3d import timesensor

__all__ = [
    'Analyser', 'AudioClip', 'BiquadFilter', 'BufferAudioSource', 'Convolver', 'Delay',
    'DynamicsCompressor', 'Gain', 'ListenerPointSource', 'MicrophoneSource',
    'OscillatorSource', 'Running', 'StreamAudioSource', 'WaveShaper',
]


class Running(timesensor.Clocked):
    """A sound node that runs from `startTime` until it is stopped"""

    enabled: Any
    elapsedTime: Any

    def cycle(self) -> float:
        """No cycle: the node runs until `stopTime` or until it is disabled"""
        return math.inf

    def clockEnabled(self) -> bool:
        """`enabled`"""
        return bool(self.enabled)

    def _send(self, _now: float, elapsed: float, fraction: float) -> None:
        self.__dict__['_fraction'] = fraction
        self.elapsedTime = elapsed

    def playedFraction(self) -> float:
        """The part of the cycle gone by: running, or where the node stopped"""
        fraction = self.runFraction()
        if fraction is None:
            fraction = self.__dict__.get('_fraction', 0.0)
        return float(fraction)


class Unlooped:
    """A node with no `loop` field runs once: until it is stopped"""

    loop = False


class AudioClip(Running, x3d.AudioClip):
    """An AudioClip that runs as :meth:`advance` is called"""

    PROTO = 'AudioClip'
    startTime = timesensor.StartTime('startTime', 1, 0.0)

    def setDuration(self, seconds: Optional[float]) -> None:
        """The clip is `seconds` long, or None where it cannot be read; sends `duration_changed`

        X3D reports a duration that is not available as -1.
        """
        known = float(seconds) if seconds is not None and seconds > 0 else 0.0
        self.__dict__['_duration'] = known
        self.duration_changed = known if seconds is not None else -1.0

    def duration(self) -> float:
        """The clip's length in seconds at its own speed; 0 until it is known"""
        return float(self.__dict__.get('_duration', 0.0))

    def playingPitch(self) -> float:
        """The `pitch` the clip plays at: the one it had when it last started"""
        return float(self.__dict__.get('_pitch', self.pitch))

    def advance(self, now: float) -> bool:
        if not self.running():
            self.__dict__['_pitch'] = float(self.pitch)
        return super().advance(now)

    def cycle(self) -> float:
        """The duration over the pitch; 0 until the duration is known"""
        pitch = self.playingPitch()
        return self.duration() / pitch if pitch > 0 else 0.0

    def position(self) -> float:
        """The time into the clip that is playing, in seconds of the clip"""
        return self.playedFraction() * self.duration()


class BufferAudioSource(Running, x3d.BufferAudioSource):
    """A BufferAudioSource that runs as :meth:`advance` is called"""

    PROTO = 'BufferAudioSource'
    startTime = timesensor.StartTime('startTime', 1, 0.0)

    def samples(self) -> NDArray[np.float32]:
        """`buffer` as ``(channels, frames)``: each channel's samples follow the last's

        `numberOfChannels` 0 is one channel; samples past the last whole
        frame are dropped.
        """
        data = np.asarray(self.buffer, dtype=np.float32).reshape(-1)
        channels = max(1, int(self.numberOfChannels))
        frames = data.shape[0] // channels
        return data[:frames * channels].reshape(channels, frames)

    def setBuffer(self, frames: int, channels: int, rate: float) -> None:
        """The samples are `frames` long in `channels` channels at `rate` a second

        Sends `length`, `bufferlength`, `channelCount` and `bufferDuration`.
        """
        frames = max(0, int(frames))
        duration = frames / float(rate) if rate > 0 else 0.0
        self.__dict__['_duration'] = duration
        self.length = frames
        self.bufferlength = frames
        self.channelCount = max(0, int(channels))
        self.bufferDuration = duration

    def duration(self) -> float:
        """The buffer's length in seconds at its own speed; 0 until it is known"""
        return float(self.__dict__.get('_duration', 0.0))

    def computedRate(self) -> float:
        """`playbackRate` times ``2 ** (detune / 1200)``"""
        return float(self.playbackRate) * 2.0 ** (float(self.detune) / 1200.0)

    def cycle(self) -> float:
        """The duration over the rate; for ever at rate 0, and 0 with no samples"""
        duration = self.duration()
        if duration <= 0:
            return 0.0
        rate = abs(self.computedRate())
        return duration / rate if rate > 0 else math.inf

    def position(self) -> float:
        """The time into the buffer that is playing, in seconds of the buffer"""
        cycle = self.cycle()
        if not math.isfinite(cycle):
            return 0.0
        gone = self.playedFraction() * self.duration()
        return self.duration() - gone if self.computedRate() < 0 else gone


class OscillatorSource(Running, x3d.OscillatorSource, Unlooped):
    """An OscillatorSource that runs as :meth:`advance` is called"""

    PROTO = 'OscillatorSource'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class MicrophoneSource(Running, x3d.MicrophoneSource, Unlooped):
    """A MicrophoneSource that runs as :meth:`advance` is called"""

    PROTO = 'MicrophoneSource'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class StreamAudioSource(Running, x3d.StreamAudioSource, Unlooped):
    """A StreamAudioSource that runs as :meth:`advance` is called"""

    PROTO = 'StreamAudioSource'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class ListenerPointSource(Running, x3d.ListenerPointSource, Unlooped):
    """A ListenerPointSource that runs as :meth:`advance` is called"""

    PROTO = 'ListenerPointSource'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class Gain(Running, x3d.Gain, Unlooped):
    """A Gain that runs as :meth:`advance` is called"""

    PROTO = 'Gain'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class Delay(Running, x3d.Delay, Unlooped):
    """A Delay that runs as :meth:`advance` is called"""

    PROTO = 'Delay'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class BiquadFilter(Running, x3d.BiquadFilter, Unlooped):
    """A BiquadFilter that runs as :meth:`advance` is called"""

    PROTO = 'BiquadFilter'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class Convolver(Running, x3d.Convolver, Unlooped):
    """A Convolver that runs as :meth:`advance` is called"""

    PROTO = 'Convolver'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class DynamicsCompressor(Running, x3d.DynamicsCompressor, Unlooped):
    """A DynamicsCompressor that runs as :meth:`advance` is called"""

    PROTO = 'DynamicsCompressor'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class WaveShaper(Running, x3d.WaveShaper, Unlooped):
    """A WaveShaper that runs as :meth:`advance` is called"""

    PROTO = 'WaveShaper'
    startTime = timesensor.StartTime('startTime', 1, 0.0)


class Analyser(Running, x3d.Analyser, Unlooped):
    """An Analyser that runs as :meth:`advance` is called"""

    PROTO = 'Analyser'
    startTime = timesensor.StartTime('startTime', 1, 0.0)
