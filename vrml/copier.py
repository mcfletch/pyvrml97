"""Object representing node-copying pass"""

class Copier( object ):
    """An object representing a node-copying pass"""
    def __init__(
        self,
        shareProtos = 1,
        instantiation=0,
    ):
        """Instantiate the copier object

        # share prototypes, we don't currently support not doing this!
        shareProtos -- whether to try to share prototypes between source
            and copied nodes
        instantiation -- whether this is a prototype-instantiation copy
        baseNode -- baseNode for prototype instantiations, this is the
            node whose sub-scenegraph is being built by the copier
        """
        self.shareProtos, self.instantiation = shareProtos, instantiation
    def use( self, clientNode, newNode=None ):
        """See whether (or register that) we have a USE for this (source) clientNode"""
        if not hasattr( self, 'useNodes'):
            self.useNodes = {}
        if newNode is not None:
            self.useNodes[ clientNode ] = newNode
        else:
            return self.useNodes.get( clientNode )