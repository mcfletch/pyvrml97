"""Node-paths for VRML97 incl. transform-matrix calculation
"""
from typing import Any, Iterator, List, Optional, TYPE_CHECKING
from vrml import nodepath
from vrml.cache import CACHE
from vrml.vrml97 import transformmatrix, nodetypes
from vrml.arrays import *
import weakref

if TYPE_CHECKING:
    #: What `_NodePath` needs of the path beside it.  It is one half of a path
    #: type -- it adds transform-matrix caching, and `nodepath.NodePath` or
    #: `nodepath.WeakNodePath` is the list the nodes themselves live in --
    #: so the caching code indexes and iterates its own host.  `object` at run
    #: time, leaving the mix-in the base it always had.
    _PathHost = List[Any]
else:
    _PathHost = object


class _NodePath( _PathHost ):
    """Path within a VRML97 scenegraph from root to particular node

    Adds transformation-matrix calculation functions
    based on the nodetypes.Transforming node's
    attributes.
    """
    parent: Optional[Any] = None
    #: Weak references to the paths extending this one, so invalidating a
    #: transform can reach the whole subtree.  None until there is one.
    children: Optional[List[Any]] = None
    active = True
    broken = False

    def transformMatrix( self, translate: bool=True, scale: bool=True, rotate: bool=True, matrixHolder: bool=False, inverse: bool=False ) -> Any:
        """Calculate (and cache) a transform matrix for this path

        Calculates our transformMatrix from our parent's transform
        and the set of nodes between our parent and ourself.  Normally
        that should be a *single* node or *none* in most cases.

        translate -- if true, include translations in the matrix
        scale -- if true, include scales in the matrix
        rotate -- if true, include rotations in the matrix

        Note: to apply these matrices to a particular coordinate,
        you would do the following:

            p = ones( 4 )
            p[:3] = coordinate
            return dot( p, matrix)

        That is, you use the homogenous coordinate, and
        make it the first item in the dot'ing.

        The matrix is kept in the cache until one of the transforms above it
        changes, and the same array is answered until then. A path whose
        own nodes do not transform answers its parent's array. Each path
        depends on its parent path's matrix and on its own transforms' local
        matrices (:meth:`vrml.cache.CacheHolder.depend_holder`), so moving a
        transform clears the paths below it and no others, and working one
        out again costs one product per path rather than one per transform
        above it.
        """
        key=(['matrix','inverse_matrix'][int(bool(inverse))],translate,scale,rotate)
        # The paths from this one up to the nearest with its matrix in hand.
        todo = []
        path: Any = self
        base = None
        while True:
            holder = CACHE.getHolder( path, key=key )
            if holder is not None and holder.data is not None:
                base = holder.data
                break
            todo.append( (path, holder) )
            parent = path.parent
            if parent is None or len(parent) >= len(path):
                break
            path = parent
        for path, holder in reversed( todo ):
            base = path._extendMatrix( base, holder, key, translate, scale, rotate, inverse )
        return base

    def _extendMatrix( self, base: Any, holder: Any, key: Any, translate: bool,
                       scale: bool, rotate: bool, inverse: bool ) -> Any:
        """Work out this path's matrix from ``base``, its parent's

        ``base`` is None for a path with no parent, which is worked out from
        its first node. ``holder`` is this path's holder, or None where it
        has never had one: then it is made, and told what it depends on.
        """
        doConnect = holder is None
        if doConnect:
            holder = CACHE.holder( self, None, key=key )
        start = 0
        if base is not None:
            parent = self.parent
            assert parent is not None, 'a base matrix is its parent path\'s'
            start = len(parent)
            if doConnect:
                source = CACHE.getHolder( parent, key=key )
                holder.depend_holder( source )
                holder.depend( source )
        local = []
        t = nodetypes.Transforming
        for index in range( start, len(self) ):
            item = self[index]
            if isinstance( item, t ):
                child_holder = item.localMatrices( translate=translate, scale=scale, rotate=rotate )
                if doConnect:
                    holder.depend_holder( child_holder )
                    holder.depend( child_holder )
                local.append( child_holder.data[inverse] )
        if inverse:
            local.reverse()
        own = transformmatrix.compressMatrices( *local )
        if own is None:
            matrix = base
        elif base is None:
            matrix = own
        elif inverse:
            matrix = dot( base, own )
        else:
            matrix = dot( own, base )
        if matrix is None:
            matrix = identity(4, dtype='f')
        holder.data = matrix
        return matrix
    def transformChildren( self, reverse: int=0 ) -> "Iterator[Any]":
        """Yield all transforming children"""
        t = nodetypes.Transforming
        if reverse:
            for i in range(len(self)-1,-1, -1):
                item = self[i]
                if isinstance(item, t):
                    yield item

        else: # forward...
            for item in self:
                if isinstance(item, t):
                    yield item

    def __add__(self, other: Any) -> Any:
        """Add parent-matrix pre-caching support to nodepaths"""
        base = super( _NodePath, self).__add__( other )
        base.parent = self       # type: ignore[attr-defined]
        if self.children is None:
            self.children = []
        self.children.append( weakref.ref( base ))
        # watch for other sending events which say that
        # this relationship is no longer active...
        return base
    def iterchildren( self ) -> "Iterator[Any]":
        """Iterate over child paths which are still live"""
        if self.children is not None:
            for childref in self.children[:]:
                child = childref()
                if child is not None:
                    yield child
                else:
                    self.children.remove( childref )
    def iterdescendents( self ) -> "Iterator[Any]":
        """Iterate over all descendent paths, depth-first

        Every generation, not merely children and grandchildren.
        :meth:`invalidate` is what makes the difference load-bearing: a
        descendent it cannot reach keeps ``broken`` False, and a renderer
        that maintains its draw set by dropping invalidated paths goes on
        drawing a subtree that has been detached from the scenegraph.

        Iterative rather than recursive because a path is as deep as the
        scenegraph under it, which is content and not something this can
        bound.
        """
        todo = list( self.iterchildren() )
        while todo:
            child = todo.pop( 0 )
            yield child
            todo[:0] = list( child.iterchildren() )
    def invalidate( self ) -> None:
        """Set this path to be invalid (and every path below it)"""
        self.broken = True
        for desc in self.iterdescendents( ):
            desc.broken = True

class NodePath( _NodePath, nodepath.NodePath ):
    """Strong-reference version of VRML97 NodePath"""
class WeakNodePath( _NodePath, nodepath.WeakNodePath ):
    """Weak-reference version of VRML97 NodePath"""
