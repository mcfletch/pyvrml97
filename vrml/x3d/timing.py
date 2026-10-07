"""The time a node's world is at: X3D's browser time, from its scene's clock

A node that stamps or measures time -- a `TimeTrigger`, a follower, a
bindable's `bindTime` -- asks :func:`now_for`, which calls the `clock` of the
scene the node is rooted in. An engine whose frames run on a clock of its
own gives its scenes that clock; a node in no scene with one has
:data:`clock`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from vrml import protofunctions

__all__ = ['clock', 'now_for']

#: The time of a node in no scene with a clock, in seconds.
clock: Callable[[], float] = time.time


def now_for(node: Any) -> float:
    """The time, in seconds, of the scene `node` is in"""
    scene_clock = getattr(protofunctions.root(node), 'clock', None)
    return float(scene_clock() if callable(scene_clock) else clock())
