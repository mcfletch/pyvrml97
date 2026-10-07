"""X3D's LoadSensor, and the load state of the nodes that read a url

A node reading its url records where it has got to with
:func:`set_load_state`: :data:`LOADING`, :data:`LOADED` or :data:`FAILED`;
:func:`load_state` is None for a node that has recorded nothing.

A `LoadSensor` (ISO/IEC 19775-1, 9.4.3) watches its `children`. Whoever keeps
time calls :meth:`LoadSensor.observe`, which reads their states:

- while any is loading, `isActive TRUE` and `progress`, the part of them
  loaded;
- when all have loaded, `progress` 1, `isLoaded TRUE`, `loadTime` and
  `isActive FALSE`;
- when one fails, or `timeOut` (where positive) passes while they load,
  `isLoaded FALSE` and `isActive FALSE`.

A child with no state is not waited for. Once it has reported, the sensor
reports again when a child starts loading again.
"""

from __future__ import annotations

from typing import Any, Final, Optional

from vrml.x3d import nodes as x3d
from vrml.x3d import timing

__all__ = ['FAILED', 'LOADED', 'LOADING', 'LoadSensor', 'load_state', 'set_load_state']

#: The node is reading its url.
LOADING: Final = 'loading'
#: The node has read its url.
LOADED: Final = 'loaded'
#: None of the node's urls could be read.
FAILED: Final = 'failed'


def load_state(node: Any) -> Optional[str]:
    """Where `node` has got to reading its url; None where it has recorded nothing"""
    found: Optional[str] = getattr(node, '__dict__', {}).get('_loadState')
    return found


def set_load_state(node: Any, state: str) -> None:
    """Record where `node` has got to reading its url"""
    node.__dict__['_loadState'] = state


class LoadSensor(timing.Timed, x3d.LoadSensor):
    """A LoadSensor that reports as :meth:`observe` is called"""

    def observe(self, now: Optional[float] = None) -> bool:
        """Report the children's loading at `now`; whether anything was sent"""
        if not self.enabled:
            return False
        states = [state for state in (load_state(child) for child in self.children)
                  if state is not None]
        if not states:
            return False
        now = self.now() if now is None else float(now)
        loading = LOADING in states
        if self.__dict__.get('_reported') and not loading:
            return False
        if FAILED in states:
            return self._finish(False, now)
        if not loading:
            self.progress = 1.0
            return self._finish(True, now)
        if self.__dict__.pop('_reported', False) or '_started' not in self.__dict__:
            self.__dict__['_started'] = now
            self.isActive = True
        self.progress = states.count(LOADED) / len(states)
        timeOut = float(self.timeOut)
        if timeOut > 0 and now - self.__dict__['_started'] > timeOut:
            return self._finish(False, now)
        return True

    def _finish(self, loaded: bool, now: float) -> bool:
        """Report the children loaded, or not"""
        self.isLoaded = loaded
        if loaded:
            self.loadTime = now
        if self.__dict__.pop('_started', None) is not None:
            self.isActive = False
        self.__dict__['_reported'] = True
        return True
