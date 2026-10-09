"""X3D's LoadSensor, and the load state of the nodes that read a url

A node reading its url records where it has got to with
:func:`set_load_state`: :data:`LOADING`, :data:`LOADED` or :data:`FAILED`;
:func:`load_state` is None for a node that has recorded nothing. A node
whose state follows from its fields answers it from a ``loadState()``
method instead.

A `LoadSensor` (ISO/IEC 19775-1, 9.4.3) watches its `children`. Whoever keeps
time calls :meth:`LoadSensor.observe`, which reads their states:

- while any is loading, `isActive TRUE` and `progress`, the part of them
  loaded;
- when all have loaded, `progress` 1, `isLoaded TRUE`, `loadTime` and
  `isActive FALSE`;
- when one fails, or `timeOut` (where positive) passes while they load,
  `isLoaded FALSE`, `isActive FALSE` and `progress`, the part loaded;
- with no children, `isLoaded FALSE`, `isActive FALSE` and `progress` 0.

A child with no state is not waited for. Once it has reported, the sensor
reports again when a child starts loading again, or when its children are
set.
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
    answer = getattr(node, 'loadState', None)
    if answer is not None:
        answered: Optional[str] = answer()
        return answered
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
        children = list(self.children)
        watching = self.__dict__.get('_watching')
        if watching is None or len(watching) != len(children) or any(
                was is not now_child for was, now_child in zip(watching, children)):
            self.__dict__['_watching'] = children
            self.__dict__.pop('_reported', None)
        now = self.now() if now is None else float(now)
        if not children:
            if self.__dict__.get('_reported'):
                return False
            self.progress = 0.0
            return self._finish(False, now, ended=True)
        states = [state for state in (load_state(child) for child in children)
                  if state is not None]
        if not states:
            return False
        loading = LOADING in states
        if self.__dict__.get('_reported') and not loading:
            return False
        if FAILED in states:
            self.progress = states.count(LOADED) / len(states)
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

    def _finish(self, loaded: bool, now: float, ended: bool = False) -> bool:
        """Report the children loaded, or not; `ended` sends `isActive FALSE`
        whether or not it was sent TRUE"""
        self.isLoaded = loaded
        if loaded:
            self.loadTime = now
        if self.__dict__.pop('_started', None) is not None or ended:
            self.isActive = False
        self.__dict__['_reported'] = True
        return True
