"""Routable event base-class for VRML environments"""

class Event( object ):
    """Routable event for VRML environments"""
    def __init__( self ):
        """Initialize the Event object"""
        self.visitedNodes = {}
    def visited (self, key, value = None):
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
    