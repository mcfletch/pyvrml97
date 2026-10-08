"""X3D's MovieTexture timing (ISO/IEC 19775-1, 8.4 and 18.4.3).

A MovieTexture runs as a TimeSensor does, its cycle the movie's duration and
its rate `speed`; `position()` is the time into the movie that is shown.
"""

import pytest

from vrml.x3d import media


def movie(**fields):
    found = media.MovieTexture(**fields)
    found.setDuration(4.0)
    return found


def test_a_movie_with_no_duration_shows_its_start():
    found = media.MovieTexture(loop=True)
    assert found.advance(10.0) is False
    assert found.position() == 0.0


def test_setting_the_duration_sends_it():
    assert movie().duration_changed == 4.0


def test_a_looping_movie_plays_round():
    found = movie(loop=True)
    assert found.advance(10.0)
    assert found.isActive is True
    assert found.position() == pytest.approx(2.0)
    assert found.elapsedTime == pytest.approx(10.0)


def test_speed_is_how_fast_it_plays():
    found = movie(loop=True, speed=2.0)
    found.advance(3.0)
    assert found.position() == pytest.approx(2.0)


def test_a_movie_that_ends_keeps_its_last_frame():
    found = movie(startTime=1.0)
    found.advance(2.0)
    assert found.position() == pytest.approx(1.0)
    found.advance(10.0)
    assert found.isActive is False
    assert found.position() == pytest.approx(4.0)


def test_a_movie_played_backwards_shows_its_end_before_it_starts():
    found = movie(speed=-1.0, startTime=100.0)
    found.advance(50.0)
    assert found.position() == pytest.approx(4.0)


def test_a_movie_played_backwards_runs_from_its_end():
    found = movie(speed=-1.0, startTime=1.0)
    found.advance(2.0)
    assert found.position() == pytest.approx(3.0)


def test_a_paused_movie_holds_its_frame():
    found = movie(loop=True, startTime=0.0)
    found.advance(1.0)
    found.pauseTime = 1.5
    found.advance(2.0)
    held = found.position()
    found.advance(3.0)
    assert found.isPaused is True
    assert found.position() == held == pytest.approx(1.5)


def test_its_start_time_is_kept_while_it_plays():
    found = movie(loop=True)
    found.advance(1.0)
    found.startTime = 0.5
    assert found.startTime == 0.0


def test_it_is_the_runtimes_movie_texture():
    from vrml.x3d import runtime  # noqa: PLC0415 the registry, asked of here alone
    assert runtime.PROTOTYPES['MovieTexture'] is media.MovieTexture
