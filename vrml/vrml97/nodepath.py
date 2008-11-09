"""Node-paths for VRML97 incl. transform-matrix calculation
"""
from __future__ import generators
from vrml import nodepath
from vrml.vrml97 import transformmatrix, nodetypes
from vrml.arrays import *

class _NodePath( object ):
	"""Path within a VRML97 scenegraph from root to particular node

	Adds transformation-matrix calculation functions
	based on the nodetypes.Transforming node's
	attributes.
	"""
	matrix = None
	parentMatrixInfo = None,0
	def isTransform( self, item ):
		"""Customization Point: determine whether a node is a Transform"""
		return isinstance(item, nodetypes.Transforming)
	def transformMatrix( self ):
		"""Manually generate a transform matrix for this path

		Note: to apply these matrices to a particular coordinate,
		you would do the following:

			p = ones( 4 )
			p[:3] = coordinate
			return dot( p, matrix)

		That is, you use the homogenous coordinate, and
		make it the first item in the dot'ing.
		"""
		if self.matrix is not None:
			return self.matrix
		elif self.parentMatrixInfo[0] is not None:
			matrix,start = self.parentMatrixInfo
			t = nodetypes.Transforming
			for item in super( NodePath,self).__getslice__( start, len(self)):
				if isinstance( item, t ):
					d = item.__dict__
					matrix = transformmatrix.transformMatrix (
						translation = d.get( "translation"),
						rotation = d.get( "rotation"),
						scale = d.get( "scale"),
						scaleOrientation = d.get( "scaleOrientation"),
						center = d.get( "center"),
						parentMatrix = matrix,
					)
			self.matrix = matrix
			return matrix
		matrix = identity(4, 'd')
		for item in self.transformChildren():
			### this isn't quite right, it's Transform-specific,
			### won't work for billboards and the like.
			d = item.__dict__
			matrix = transformmatrix.transformMatrix (
				translation = d.get( "translation"),
				rotation = d.get( "rotation"),
				scale = d.get( "scale"),
				scaleOrientation = d.get( "scaleOrientation"),
				center = d.get( "center"),
				parentMatrix = matrix,
			)
		self.matrix = matrix
		return matrix
		  
	def itransformMatrix( self ):
		"""Manually generate an inverse transform matrix for this path

		See transformMatrix for semantics
		"""
		matrix = identity(4, 'd')
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
		base.parentMatrixInfo = self.matrix,len(self)
		return base

class NodePath( _NodePath, nodepath.NodePath ):
	"""Strong-reference version of VRML97 NodePath"""
class WeakNodePath( _NodePath, nodepath.WeakNodePath ):
	"""Weak-reference version of VRML97 NodePath"""
