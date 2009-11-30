"""Representation and manipulation of scenegraph paths
"""
from vrml import node, weaklist

class NodePath( list ):
    """Path within a scenegraph from root to particular node

    Has minimal operations, most high-level functionality is
    provided by sub-classes such as vrml.vrml97.nodepath and
    OpenGLContext.scenegraph.nodepath
    """
    def __repr__( self ):
        """Code-like representation of the node path

        Note: this doesn't use super for determining
        the base representation, as that might wind up
        creating a name like:
            WeakNodePath( WeakTuple( Node, Node,...))
        """
        return '%s(%s)'%(self.__class__.__name__, list.__repr__( self ))
    def __str__( self ):
        """Simple representation of a node-path for human consumption"""
        return "%s(%s)"%(
            self.__class__.__name__,
            "->".join([
                str( N )
                for N in self
            ]))
    def common (self, other):
        """Return the common root sub-path between ourselves and other

        If there is no common sub-root, returns an empty path
        """
        result = []
        for index in range( min(len(self),len(other))):
            if self [index] is other [index]:
                result.append (self [index])
            else:
                break
        return self.__class__(result)
    def __add__(self, other):
        """Return a new path with other as tail"""
        if isinstance( other, node.Node ):
            other = [other]
        return self.__class__( super(NodePath, self).__add__( other))
    def __getslice__(self, start, stop):
        """Return a new path with our items from start to stop"""
        return self.__class__(super (NodePath, self).__getslice__(start, stop))
    def __eq__( self, other ):
        """Check whether we are equal to another path"""
        if len(self) != len(other):
            return 0
        for index in range(len(self)):
            if self [index] is not other [index]:
                return 0
        return 1

class WeakNodePath( NodePath, weaklist.WeakList ):
    """Node path that uses weak-references to nodes

    You hold strong references to these paths, then
    wrap all uses of them with checks for
    weakref.ReferenceError to check for dead paths.
    """
    
    