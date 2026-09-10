"""Routable event base-class for VRML environments"""

from typing import Any, Dict, Optional


class Event( object ):
    """Routable event for VRML environments"""

    def __init__( self ) -> None:
        """Initialize the Event object"""
        self.visitedNodes: Dict[Any, Any] = {}

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
