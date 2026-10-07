"""The time a node's world is at: X3D's browser time, from its scene's clock

A node that stamps or measures time -- a `TimeTrigger`, a follower, a
bindable's `bindTime` -- is :class:`Timed` and asks its :meth:`Timed.now`,
which is :func:`now_for`: the `clock` of the scene the node is rooted in, or
:data:`clock` for a node in no scene with one. An engine whose frames run on
a clock of its own gives its scenes that clock, and may override `now` on
its node classes to use it for a node in no scene.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from vrml import protofunctions

__all__ = ['Timed', 'clock', 'now_for']

#: The time of a node in no scene with a clock, in seconds.
clock: Callable[[], float] = time.time


def now_for(node: Any) -> float:
    """The time, in seconds, of the scene `node` is in"""
    scene_clock = getattr(protofunctions.root(node), 'clock', None)
    return float(scene_clock() if callable(scene_clock) else clock())


class Timed:
    """A node that stamps or measures time"""

    def now(self) -> float:
        """The time, in seconds, this node is at"""
        return now_for(self)
