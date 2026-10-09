"""X3D's Sound component timing (ISO/IEC 19775-1, 8.2.4 and 16.4).

Every sound source and processing node is time dependent: it runs from
`startTime` until a later `stopTime`, pausing at `pauseTime` and resuming at
`resumeTime`. An AudioClip's cycle is its duration over its `pitch`, a
BufferAudioSource's its buffer's duration over its rate; the others have no
cycle and run until they are stopped.
"""

import math

import numpy as np
import pytest

from vrml.x3d import sound


def clip(**fields):
    found = sound.AudioClip(**fields)
    found.setDuration(4.0)
    return found


class TestAudioClip:
    def test_a_clip_with_no_duration_does_not_start(self):
        found = sound.AudioClip(loop=True)
        assert found.advance(10.0) is False
        assert found.position() == 0.0

    def test_setting_the_duration_sends_it(self):
        assert clip().duration_changed == 4.0

    def test_a_clip_that_cannot_be_read_reports_no_duration(self):
        found = sound.AudioClip()
        found.setDuration(None)
        assert found.duration_changed == -1.0
        assert found.cycle() == 0.0

    def test_a_looping_clip_plays_round(self):
        found = clip(loop=True)
        assert found.advance(10.0)
        assert found.isActive is True
        assert found.position() == pytest.approx(2.0)
        assert found.elapsedTime == pytest.approx(10.0)

    def test_pitch_shortens_the_cycle(self):
        found = clip(loop=True, pitch=2.0)
        found.advance(3.0)
        assert found.cycle() == pytest.approx(2.0)
        assert found.position() == pytest.approx(2.0)

    def test_pitch_set_while_it_plays_is_ignored(self):
        found = clip(loop=True, pitch=2.0)
        found.advance(1.0)
        found.pitch = 4.0
        found.advance(1.5)
        assert found.playingPitch() == 2.0
        assert found.cycle() == pytest.approx(2.0)

    def test_a_clip_that_does_not_loop_stops_at_its_end(self):
        found = clip(startTime=1.0)
        found.advance(2.0)
        assert found.isActive is True
        found.advance(6.0)
        assert found.isActive is False
        assert found.position() == pytest.approx(4.0)

    def test_a_single_play_that_ended_before_it_was_seen_does_not_start(self):
        found = clip(startTime=1.0)
        assert found.advance(100.0) is False
        assert found.running() is False

    def test_a_paused_clip_holds_its_place(self):
        found = clip(loop=True)
        found.advance(1.0)
        found.pauseTime = 1.5
        found.advance(2.0)
        held = found.position()
        found.advance(3.0)
        assert found.isPaused is True
        assert found.position() == held == pytest.approx(1.5)

    def test_its_start_time_is_kept_while_it_plays(self):
        found = clip(loop=True)
        found.advance(1.0)
        found.startTime = 0.5
        assert found.startTime == 0.0

    def test_a_disabled_clip_stops(self):
        found = clip(loop=True)
        found.advance(1.0)
        found.enabled = False
        found.advance(2.0)
        assert found.isActive is False


class TestEndless:
    """Sources with no cycle, and the processing nodes, run until stopped."""

    @pytest.mark.parametrize('kind', [
        sound.OscillatorSource, sound.MicrophoneSource, sound.StreamAudioSource,
        sound.ListenerPointSource, sound.Gain, sound.Delay, sound.BiquadFilter,
        sound.Convolver, sound.DynamicsCompressor, sound.WaveShaper, sound.Analyser,
    ])
    def test_it_runs_from_its_start_time(self, kind):
        found = kind(startTime=5.0)
        assert found.advance(1.0) is False
        assert found.advance(6.0) is True
        assert found.isActive is True
        assert found.cycle() == math.inf

    def test_it_runs_for_ever(self):
        found = sound.OscillatorSource()
        found.advance(1e9)
        found.advance(2e9)
        assert found.isActive is True
        assert found.elapsedTime == pytest.approx(2e9)

    def test_it_stops_at_its_stop_time(self):
        found = sound.Gain(startTime=1.0, stopTime=3.0)
        found.advance(2.0)
        found.advance(4.0)
        assert found.isActive is False
        assert found.elapsedTime == pytest.approx(2.0)

    def test_it_pauses_and_resumes(self):
        found = sound.OscillatorSource()
        found.advance(1.0)
        found.pauseTime = 2.0
        found.advance(3.0)
        assert found.isPaused is True
        found.resumeTime = 4.0
        found.advance(5.0)
        assert found.isPaused is False
        assert found.elapsedTime == pytest.approx(3.0)

    def test_a_disabled_node_does_not_start(self):
        found = sound.Delay(enabled=False)
        assert found.advance(1.0) is False


class TestBufferAudioSource:
    def test_the_buffer_is_its_channels_one_after_another(self):
        found = sound.BufferAudioSource(buffer=[1, 2, 3, 4, 5, 6], numberOfChannels=2)
        assert np.array_equal(found.samples(), [[1, 2, 3], [4, 5, 6]])

    def test_no_channel_count_is_one_channel(self):
        found = sound.BufferAudioSource(buffer=[0.5, -0.5])
        assert found.samples().shape == (1, 2)

    def test_a_buffer_that_does_not_divide_drops_the_remainder(self):
        found = sound.BufferAudioSource(buffer=[1, 2, 3, 4, 5], numberOfChannels=2)
        assert found.samples().shape == (2, 2)

    def test_setting_the_buffer_sends_its_shape(self):
        found = sound.BufferAudioSource()
        found.setBuffer(frames=22050, channels=2, rate=44100)
        assert found.length == 22050
        assert found.bufferlength == 22050
        assert found.channelCount == 2
        assert found.bufferDuration == pytest.approx(0.5)

    def test_its_cycle_is_its_duration_at_its_rate(self):
        found = sound.BufferAudioSource(playbackRate=2.0, detune=1200.0, loop=True)
        found.setBuffer(frames=44100, channels=1, rate=44100)
        assert found.computedRate() == pytest.approx(4.0)
        assert found.cycle() == pytest.approx(0.25)

    def test_its_position_is_seconds_into_the_buffer(self):
        found = sound.BufferAudioSource(loop=True)
        found.setBuffer(frames=4000, channels=1, rate=1000)
        found.advance(9.0)
        assert found.position() == pytest.approx(1.0)

    def test_a_buffer_played_backwards_starts_at_its_end(self):
        found = sound.BufferAudioSource(playbackRate=-1.0, startTime=1.0)
        found.setBuffer(frames=4000, channels=1, rate=1000)
        found.advance(2.0)
        assert found.position() == pytest.approx(3.0)

    def test_a_buffer_held_at_rate_zero_never_ends(self):
        found = sound.BufferAudioSource(playbackRate=0.0)
        found.setBuffer(frames=100, channels=1, rate=1000)
        assert found.cycle() == math.inf

    def test_an_empty_buffer_does_not_start(self):
        found = sound.BufferAudioSource(loop=True)
        assert found.cycle() == 0.0
        assert found.advance(1.0) is False
