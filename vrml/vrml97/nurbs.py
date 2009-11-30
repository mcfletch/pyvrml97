"""Node definitions for the VRML97 nurbs extension proposal

OpenGLContext only has the most rudimentary of NURBs support,
and still this module doesn't even define many of the NURBs-
related prototypes which you could run across.  I've not
provided the more funky of the nodes, such as the interpolators
and the deformation matrices.
"""
from vrml.vrml97 import nodetypes
from vrml import field, node, fieldtypes

### Trimming curves
class Contour2D( node.Node ):
    """A 2D contour (collection of joined segments)

    children -- a set of polylines and/or curves which are
        joined to form the trimming contour
    """
    PROTO = "Contour2D"
    children = field.newField( 'children', 'MFNode', 1, list)
    
class Polyline2D( node.Node ):
    """A 2D piece-wise-linear polyline"""
    PROTO = "Polyline2D"
    point = field.newField( 'point', 'MFVec2f', 1, list)
class NurbsCurve2D( node.Node ):
    """A 2D nurbs curve normally used for trimming surfaces"""
    PROTO = "NurbsCurve2D"
    knot = field.newField( 'knot', 'MFFloat32', 1, list)
    order = field.newField( 'order', 'SFInt32', 1, 3)
    controlPoint = field.newField( 'controlPoint', 'MFVec2f', 1, list)
    weight = field.newField( 'weight', 'MFFloat32', 1, list)
    tessellation = field.newField( 'tessellation', 'SFInt32', 1, 0)

### Surfaces and Curves
class NurbsCurve( nodetypes.Geometry, node.Node ):
    """A 3D nurbs curve (a curvy line in 3D space)
    """
    PROTO = "NurbsCurve"
    knot = field.newField( 'knot', 'MFFloat32', 1, list)
    order = field.newField( 'order', 'SFInt32', 1, 3)
    controlPoint = field.newField( 'controlPoint', 'MFVec3f', 1, list)
    color = field.newField( 'color', 'MFColor', 1, list)
    weight = field.newField( 'weight', 'MFFloat32', 1, list)
    tessellation = field.newField( 'tessellation', 'SFInt32', 1, 0)

class NurbsSurface( nodetypes.Geometry, node.Node ):
    """A Nurbs surface object"""
    PROTO = "NurbsSurface"
    uDimension = field.newField( 'uDimension', 'SFInt32', 1, 0)
    vDimension = field.newField( 'vDimension', 'SFInt32', 1, 0)
    uKnot = field.newField( 'uKnot', 'MFFloat32', 1, list)
    vKnot = field.newField( 'vKnot', 'MFFloat32', 1, list)
    uOrder = field.newField( 'uOrder', 'SFInt32', 1, 3)
    vOrder = field.newField( 'vOrder', 'SFInt32', 1, 3)
    controlPoint = field.newField( 'controlPoint', 'MFVec3f', 1, list)
    color = field.newField( 'color', 'MFColor', 1, list)
    weight = field.newField( 'weight', 'MFFloat32', 1, list)
    uTessellation = field.newField( 'uTessellation', 'SFInt32', 1, 0)
    vTessellation = field.newField( 'vTessellation', 'SFInt32', 1, 0)
    texCoord = field.newField( 'texCoord', 'SFNode', 1, node.NULL)
    solid = field.newField( 'solid', 'SFBool', 0, 1)
    ccw = field.newField( 'ccw', 'SFBool', 0, 1)

class TrimmedSurface( nodetypes.Geometry, node.Node ):
    """A trimmed Nurbs surface object"""
    PROTO = "TrimmedSurface"
    trimmingContour = field.newField( 'trimmingContour', 'MFNode', 1, list)
    surface = field.newField( 'surface', 'SFNode', 1, node.NULL)

### Unused...
class NurbsGroup( node.Node ):
    """(Unused) holder for multiple nurbs objects"""
    PROTO = "NurbsGroup"
    children = field.newField( 'children', 'MFNode', 1, list)
    tessellationScale = field.newField( 'tessellationScale', 'SFFloat', 1, 1.0)
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    
