"""Node-paths for VRML97 incl. transform-matrix calculation
"""
from __future__ import generators
from vrml import nodepath
from vrml.cache import CACHE
from vrml.vrml97 import transformmatrix, nodetypes
from vrml.arrays import *
import weakref

class _MatrixHolder( object ):
    def __init__( self, matrix ):
        self.matrix = matrix

class _NodePath( object ):
    """Path within a VRML97 scenegraph from root to particular node

    Adds transformation-matrix calculation functions
    based on the nodetypes.Transforming node's
    attributes.
    """
    parent = None
    children = None
    active = True
    broken = False
    def isTransform( self, item ):
        """Customization Point: determine whether a node is a Transform"""
        return isinstance(item, nodetypes.Transforming)
    def transformMatrix( self, translate=True, scale=True, rotate=True, matrixHolder=False ):
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
        """
        key=('matrix',translate,scale,rotate)
        holder = CACHE.getHolder( self, key=key )
        if holder is None:
            doConnect = True 
            holder = CACHE.holder( self, None, key=key )
            mHolder = None
        else:
            doConnect = False
            mHolder = holder.data
        if mHolder is None:
            matrix = None
            fields = []
            if translate:
                fields.append( 'translation' )
            if scale or rotate:
                fields.append( 'center' )
            if scale:
                fields.append( 'scale' )
                fields.append( 'scaleOrientation' )
            if rotate:
                fields.append( 'rotation' )
            start = 0
            parent = self.parent 
            if parent is not None:
                mHolder = parent.transformMatrix(
                    translate=translate,rotate=rotate,scale=scale,
                    matrixHolder=True
                )
                # holder needs to depend on parentMatrix,
                # as we're going to use it to calculate our 
                # own matrix...
                if doConnect and mHolder is not None:
                    holder.depend( mHolder )
                matrix = mHolder.matrix
                start = len(parent)
            if matrix is None:
                matrix = identity(4, 'f')
            # now calculate delta from parent to self...
            # for each item, we determine our dependencies 
            # based on *all* of the child's transform fields
            # higher-level code will then make our very existence
            # depend on the hierarchic relations between nodes...
            t = nodetypes.Transforming
            for item in super( NodePath,self).__getslice__( start, len(self)):
                if isinstance( item, t ):
                    d = item.__dict__
                    args = dict([(k,d.get(k)) for k in fields] )
                    matrix = transformmatrix.transformMatrix (
                        parentMatrix = matrix,
                        **args
                    )
                    if doConnect:
                        for k in fields:
                            holder.depend( item, k )
            mHolder = _MatrixHolder(matrix)
            holder.set( mHolder )
        if matrixHolder:
            return mHolder
        return mHolder.matrix
#		matrix = identity(4, 'f')
#		for item in self.transformChildren():
#			### this isn't quite right, it's Transform-specific,
#			### won't work for billboards and the like.
#			d = item.__dict__
#			matrix = transformmatrix.transformMatrix (
#				translation = d.get( "translation"),
#				rotation = d.get( "rotation"),
#				scale = d.get( "scale"),
#				scaleOrientation = d.get( "scaleOrientation"),
#				center = d.get( "center"),
#				parentMatrix = matrix,
#			)
#		self.matrix = matrix
#		return matrix
          
    def itransformMatrix( self ):
        """Manually generate an inverse transform matrix for this path

        See transformMatrix for semantics
        """
        matrix = identity(4, 'f')
        for item in self.transformChildren(reverse=1):
            d = item.__dict__
            matrix = transformmatrix.itransformMatrix (
                translation = d.get( "translation"),
                rotation = d.get( "rotation"),
                scale = d.get( "scale"),
                scaleOrientation = d.get( "scaleOrientation"),
                center = d.get( "center"),
                parentMatrix = matrix,
            )
        return matrix
    def transformChildren( self, reverse=0 ):
        """Yield all transforming children"""
        t = nodetypes.Transforming
        if reverse:
            for i in xrange(-1, len(self)-1, -1):
                item = self[i]
                if isinstance(item, t):
                    yield item
                
        else: # forward...
            for item in self:
                if isinstance(item, t):
                    yield item

    def __add__(self, other):
        """Add parent-matrix pre-caching support to nodepaths"""
        base = super( _NodePath, self).__add__( other )
        base.parent = self
        if self.children is None:
            self.children = []
        self.children.append( weakref.ref( base ))
        # watch for other sending events which say that 
        # this relationship is no longer active...
        return base
    def iterchildren( self ):
        """Iterate over child paths which are still live"""
        if self.children is not None:
            for childref in self.children[:]:
                child = childref()
                if child is not None:
                    yield child 
                else:
                    self.children.remove( childref )
    def iterdescendents( self ):
        """Iterate over all descendent paths"""
        for child in self.iterchildren():
            yield child 
            for desc in child.iterchildren():
                yield desc 
    def invalidate( self ):
        """Set this path to be invalid (and all children paths)"""
        self.broken = True 
        for desc in self.iterdescendents( ):
            desc.broken = True 

class NodePath( _NodePath, nodepath.NodePath ):
    """Strong-reference version of VRML97 NodePath"""
class WeakNodePath( _NodePath, nodepath.WeakNodePath ):
    """Weak-reference version of VRML97 NodePath"""
