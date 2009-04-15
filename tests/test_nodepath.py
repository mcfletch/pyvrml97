import unittest
from vrml.vrml97 import nodepath
from vrml.vrml97.basenodes import Transform
from vrml.arrays import allclose, array

class TestNodePath( unittest.TestCase ):
	def setUp( self ):
		self.empty = nodepath.NodePath()
		self.first_child = self.empty + [ Transform( translation=(1,0,0) ) ]
		self.second_child = self.first_child + [ Transform( translation=(1,0,0) ) ]
	def test_empty_matrix( self ):
		m = self.empty.transformMatrix()
		assert allclose( 
			m,
			array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],'f')
		), m
	def test_second_child( self ):
		m = self.second_child.transformMatrix()
		assert allclose( 
			m,
			array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[2,0,0,1]],'f')
		), m
	def test_change_translation( self ):
		m = self.second_child.transformMatrix()
		self.first_child[-1].translation = (-1,0,0)
		m2 = self.second_child.transformMatrix()
		assert allclose( 
			m2,
			array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],'f')
		), m2
		
