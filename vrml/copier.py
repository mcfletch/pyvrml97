"""Object representing node-copying pass"""

from typing import Any, Dict, Optional


class Copier( object ):
    """An object representing a node-copying pass"""

    #: Source node -> its copy, for the nodes reached more than once.  Built on
    #: first use, since a graph with no sharing never needs it.
    useNodes: Dict[Any, Any]

    def __init__(
        self,
        shareProtos: int = 1,
        instantiation: int = 0,
    ) -> None:
        """Instantiate the copier object

        # share prototypes, we don't currently support not doing this!
        shareProtos -- whether to try to share prototypes between source
            and copied nodes
        instantiation -- whether this is a prototype-instantiation copy
        baseNode -- baseNode for prototype instantiations, this is the
            node whose sub-scenegraph is being built by the copier
        """
        self.shareProtos, self.instantiation = shareProtos, instantiation
    def use( self, clientNode: Any, newNode: Optional[Any] = None ) -> Optional[Any]:
        """See whether (or register that) we have a USE for this (source) clientNode"""
        if not hasattr( self, 'useNodes'):
            self.useNodes = {}
        if newNode is not None:
            self.useNodes[ clientNode ] = newNode
            return None
        return self.useNodes.get( clientNode )
