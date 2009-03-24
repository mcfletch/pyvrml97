"""Node definitions for a non-standard Programable Shaders extension

Shaders are defined like so:

"""
from vrml.vrml97 import nodetypes
from vrml import field, node, fieldtypes

class ShaderGeometry( node.Node ):
	"""Generic geometry definition for a shader-based renderer
	
	vertices -- X * Y array of vertex values for the data-set 
	vertexDefinition -- string definition of mappings from 
		vertex fields to GLSL attribute definitions 
	uniforms -- Uniform nodes which are bound/updated on the 
		geometry before rendering...
	indices -- index array for rendering geometry 
	offsets -- array of offsets into indices from which to 
		begin each individual render 
	counts -- count of indices to render for each individual
		render
	offsetUniforms -- arrays of (name,value) pairs to assign 
		before each individual render 
	"""
	PROTO = "ShaderGeometry"
	vertices = field.newField( 'vertices','MFFloat', 1, list )
	indices = field.newField( 'indices', 'MFInt32', 1, list )
	offsets = field.newField( 'offsets', 'MFInt32', 1, list )
	attributes = field.newField( 'attributes','MFNode',1,list )
	uniforms = field.newField( 'uniforms','MFNode',1,list)


class FloatUniform( node.Node ):
    """Uniform (variable) binding for a shader
    """
    name = field.newField( 'name', 'SFString', 1, '' )
    # type values, 1f, 2f, 3f, 4f, m2, m3, m4, m2x3,m3x2,m2x4,m4x2,m3x4,m4x3
    value = field.newField( 'value',  'SFArray',  1,  list )

class IntUniform( node.Node ):
	"""Uniform (variable) binding for a shader (integer form)
	"""
	PROTO = "IntUniform"
	name = field.newField( 'name', 'SFString', 1, '' )
	# type values, 1i,2i,3i,4i
	value = field.newField( 'value',  'MFInt32',  1,  list )

class TextureUniform( node.Node ):
	"""Uniform which specifies a texture sampler"""
	PROTO = 'TextureUniform'
	name = field.newField( 'name','SFString', 1, '' )
	value = field.newField( 'value', 'SFNode', 1, node.NULL )

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
	attributes = field.newField( 'attributes',  'MFNode',  1,  list )
	shaders = field.newField( 'shaders',  'MFNode',  1,  list )
	# textures is a set of texture uniforms...
	textures = field.newField( 'textures', 'MFNode', 1, list )

class Shader( node.Node ):
	"""Shader is a programmable substitute for an Appearance node"""
	PROTO = 'Shader'
	#Fields
	material = field.newField( 'material', 'SFNode', 1, node.NULL)
	textures = field.newField( 'textures', 'MFNode',  1,  list )
	objects = field.newField( 'objects',  'MFNode',  1,  list )
	
	implementation = field.newField( 'implementation','SFNode',1,node.NULL)
