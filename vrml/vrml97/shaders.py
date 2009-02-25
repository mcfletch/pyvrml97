"""Node definitions for a non-standard Programable Shaders extension

Shaders are defined like so:

"""
from vrml.vrml97 import nodetypes
from vrml import field, node, fieldtypes

class FloatUniform( node.Node ):
	"""Uniform (variable) binding for a shader
	"""
	PROTO = "FloatUniform"
	name = field.newField( 'name', 'SFString', 1, '' )
	# type values, 1f, 2f, 3f, 4f, m2, m3, m4, m2x3,m3x2,m2x4,m4x2,m3x4,m4x3
	type = field.newField( 'type',  'SFString', 1,  '1f' )
	value = field.newField( 'value',  'MFFloat',  1,  list )
class IntUniform( node.Node ):
	"""Uniform (variable) binding for a shader (integer form)
	"""
	PROTO = "IntUniform"
	name = field.newField( 'name', 'SFString', 1, '' )
	# type values, 1i,2i,3i,4i
	type = field.newField( 'type',  'SFString', 1,  '1f' )
	value = field.newField( 'value',  'MFInt32',  1,  list )

class GLSLShader( node.Node ):
	"""GLSL-based shader node"""
	PROTO = "GLSLShader"
	url = field.newField( 'url', 'MFString', 1, list)
	source = field.newField( 'source','MFString',1, list)
	# type values, VERTEX or FRAGMENT
	type = field.newField( 'type',  'SFString', 1,  'VERTEX' ) 

class GLSLObject( node.Node ):
	"""GLSL-based shader object (compiled set of shaders)"""
	PROTO = "GLSLObject"
	uniforms = field.newField( 'uniforms',  'MFNode',  1,  list )
	shaders = field.newField( 'shaders',  'MFNode',  1,  list )

class Shader( node.Node ):
	"""Shader is a programmable substitute for an Appearance node"""
	PROTO = 'Shader'
	#Fields
	material = field.newField( 'material', 'SFNode', 1, node.NULL)
	textures = field.newField( 'textures', 'MFNode',  1,  list )
	objects = field.newField( 'objects',  'MFNode',  1,  list )
