"""Node definitions for a non-standard Programable Shaders extension
"""
from vrml.vrml97 import nodetypes
from vrml import field, node, fieldtypes

class ShaderGeometry( nodetypes.Children, nodetypes.Rendering, node.Node ):
    """Generic geometry definition for a shader-based renderer
    
    attributes -- define the attribute pointers which feed the 
        shader, the individual attributes may share a buffer or 
        define one per attribute 
    indices -- if present, node defining index array to be used 
        to index into buffers, will be uploaded to an element 
        buffer
    uniforms -- Uniform nodes which are bound/updated on the 
        shader before rendering this geometry, binds to the 
        shader's location == to the uniform's name.
    slices -- slices of the array to render, if not specified 
        then we'll render the whole data-set
    """
    PROTO = "ShaderGeometry"
    indices = field.newField( 'indices', 'MFInt32', 1, list )
    attributes = field.newField( 'attributes','MFNode',1,list )
    slices = field.newField( 'slices', 'MFNode',1,list )
    uniforms = field.newField( 'uniforms','MFNode',1,list )
    appearance = field.newField( 'appearance', 'SFNode',1,list )

class ShaderSlice( node.Node ):
    """Segment of a shader geometry element to render"""
    offset = field.newField( 'offset', 'SFUInt32',1, -1 )
    count = field.newField( 'count', 'SFUInt32',1, -1 )
    uniforms = field.newField( 'uniforms','MFNode',1,list)

class ShaderAttribute( node.Node ):
    """Attribute (variable) binding for a shader
    """
    name = field.newField( 'name', 'SFString', 1, '' )
    offset = field.newField( 'offset','SFUInt32',1, 0 )
    stride = field.newField( 'stride', 'SFUInt32',1, 0 ) # default to buffer natural stride
    size = field.newField( 'size','SFUInt32',1,3 ) # default num of elements
    dataType = field.newField( 'dataType','SFString', 1, 'FLOAT' )
    # the buffer into which we index...
    buffer = field.newField( 'buffer','SFNode',1,node.NULL )
    isCoord = field.newField( 'isCoord','SFBool',1,False)
    
class ShaderBuffer( node.Node ):
    """Buffer of data into which pointers can be generated"""
    type = field.newField( 'type','SFString', 1, 'ARRAY' )
    usage = field.newField( 'usage','SFString', 1, 'DYNAMIC_DRAW' )
    buffer = field.newField( 'buffer','SFArray32', 1, list )
class ShaderIndexBuffer( ShaderBuffer ):
    """Buffer of data from which indices are generated"""
    type = field.newField( 'type','SFString', 1, 'ELEMENT' )
    usage = field.newField( 'usage','SFString', 1, 'DYNAMIC_DRAW' )
    buffer = field.newField( 'buffer','MFUInt32', 1, list )

class FloatUniform( node.Node ):
    """Uniform (variable) binding for a shader
    
    The FloatUniform is the base class for FloatUniforms,
    that is, there are FloatUniform1f, FloatUniform2f,
    FloatUniformm3x2, etceteras Node-types, but not a
    FloatUniform node-type.
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
class TextureBufferUniform( node.Node ):
    """Uniform which specifies a texture across vbo data"""
    PROTO = 'TextureBufferUniform'
    name = field.newField( 'name','SFString', 1, '' )
    value = field.newField( 'value', 'SFNode', 1, node.NULL )
    format = field.newField( 'format', 'SFString',1,'RGBA32F' )

class GLSLShader( node.Node ):
    """GLSL-based shader node"""
    PROTO = "GLSLShader"
    url = field.newField( 'url', 'MFString', 1, list)
    source = field.newField( 'source','MFString',1, list)
    imports = field.newField( 'imports', 'MFNode', 1, list )
    # type values, VERTEX or FRAGMENT
    type = field.newField( 'type',  'SFString', 1,  'VERTEX' ) 

class GLSLImport( node.Node ):
    """GLSL-base shader source-code import"""
    PROTO = "GLSLImport"
    url = field.newField( 'url', 'MFString', 1, list)
    source = field.newField( 'source','MFString',1, list)

class GLSLObject( node.Node ):
    """GLSL-based shader object (compiled set of shaders)"""
    PROTO = "GLSLObject"
    uniforms = field.newField( 'uniforms',  'MFNode',  1,  list )
    shaders = field.newField( 'shaders',  'MFNode',  1,  list )
    # textures is a set of texture uniforms...
    textures = field.newField( 'textures', 'MFNode', 1, list )

class Shader( node.Node ):
    """Shader is a programmable substitute for an Appearance node"""
    PROTO = 'Shader'
    #Fields
    material = field.newField( 'material', 'SFNode', 1, node.NULL)
    objects = field.newField( 'objects',  'MFNode',  1,  list )
    
    implementation = field.newField( 'implementation','SFNode',1,node.NULL)
