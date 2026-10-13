"""Routable event base-class for VRML environments

An :class:`Event` is one cascade: the routes a change sets going, and the
changes they make in turn, each field reached at most once
(ISO/IEC 19775-1, 4.4.8.3). :func:`current` is the cascade being forwarded
on this thread, so a change made inside it -- a node's handler sending its
outputs -- carries on the same cascade rather than starting another.
"""

import contextlib
import contextvars
from collections.abc import Generator
from typing import Any, Optional

from pydispatch import dispatcher

#: The cascade being forwarded, or None between cascades.
_CURRENT: "contextvars.ContextVar[Optional[Event]]" = contextvars.ContextVar(
    'vrml_event_cascade', default=None)


def current() -> "Optional[Event]":
    """The cascade being forwarded on this thread, or None"""
    return _CURRENT.get()


@contextlib.contextmanager
def forwarding(event: "Event") -> Generator["Event"]:
    """Make `event` the :func:`current` cascade within the block"""
    token = _CURRENT.set(event)
    try:
        yield event
    finally:
        _CURRENT.reset(token)


def announce(signal: Any, sender: Any, **named: Any) -> Any:
    """Send `signal` from `sender` within the cascade under way, or a new one

    A field's change goes on along every route from it in one cascade, so
    routes that part and meet again reach the field where they meet once.
    """
    if _CURRENT.get() is not None:
        return dispatcher.send(signal, sender, **named)
    # Set and reset by hand rather than through `forwarding`: this runs for
    # every field set, and the context manager would be most of its cost.
    token = _CURRENT.set(Event())
    try:
        return dispatcher.send(signal, sender, **named)
    finally:
        _CURRENT.reset(token)


class Event( object ):
    """Routable event for VRML environments"""

    def __init__( self ) -> None:
        """Initialize the Event object"""
        self.visitedNodes: dict[Any, Any] = {}

    def visited (self, key: Any, value: Optional[Any] = None) -> Optional[Any]:
        """Check for or register visitation of the given key

        key -- an opaque hashable value, normally the node and
            field/event as a tuple.
        value -- if provided, sets the current value, otherwise
            signals that the current value should be returned

        return value: previous key value (possibly None)
        """
        if value is None:
            return self.visitedNodes.get(key)
        else:
            previousValue = self.visitedNodes.get(key)
            self.visitedNodes[key] = value
            return previousValue
