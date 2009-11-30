"""Base VRML97 node prototypes"""
from vrml.vrml97 import nodetypes
from vrml import node, field, fieldtypes
class Anchor( nodetypes.Children, nodetypes.Grouping, node.Node ):
    PROTO = 'Anchor'
    #Fields
    url = field.newField( 'url', 'MFString', 1, list)
    description = field.newField( 'description', 'SFString', 1, '')
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    parameter = field.newField( 'parameter', 'MFString', 1, list)
    children = field.newField( 'children', 'MFNode', 1, list)
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    #Events
    removeChildren = field.newEvent( 'removeChildren', 'MFNode', 0)
    addChildren = field.newEvent( 'addChildren', 'MFNode', 0)

class Appearance( node.Node ):
    PROTO = 'Appearance'
    #Fields
    material = field.newField( 'material', 'SFNode', 1, node.NULL)
    texture = field.newField( 'texture', 'SFNode', 1, node.NULL)
    textureTransform = field.newField( 'textureTransform', 'SFNode', 1, node.NULL)
    #Events
    

class AudioClip( nodetypes.Auditory, nodetypes.TimeDependent, node.Node ):
    PROTO = 'AudioClip'
    #Fields
    stopTime = field.newField( 'stopTime', 'SFTime', 1, 0.0)
    description = field.newField( 'description', 'SFString', 1, '')
    startTime = field.newField( 'startTime', 'SFTime', 1, 0.0)
    pitch = field.newField( 'pitch', 'SFFloat', 1, 1.0)
    url = field.newField( 'url', 'MFString', 1, list)
    loop = field.newField( 'loop', 'SFBool', 1, 0)
    #Events
    duration_changed = field.newEvent( 'duration_changed', 'SFTime', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)

class Background( nodetypes.Children, nodetypes.Background, node.Node ):
    PROTO = 'Background'
    #Fields
    groundAngle = field.newField( 'groundAngle', 'MFFloat', 1, list)
    rightUrl = field.newField( 'rightUrl', 'MFString', 1, list)
    topUrl = field.newField( 'topUrl', 'MFString', 1, list)
    backUrl = field.newField( 'backUrl', 'MFString', 1, list)
    groundColor = field.newField( 'groundColor', 'MFColor', 1, list)
    leftUrl = field.newField( 'leftUrl', 'MFString', 1, list)
    frontUrl = field.newField( 'frontUrl', 'MFString', 1, list)
    bottomUrl = field.newField( 'bottomUrl', 'MFString', 1, list)
    skyColor = field.newField( 'skyColor', 'MFColor', 1, [[0.0, 0.0, 0.0]])
    skyAngle = field.newField( 'skyAngle', 'MFFloat', 1, list)
    #Events
    set_bind = field.newEvent( 'set_bind', 'SFBool', 0)
    isBound = field.newEvent( 'isBound', 'SFBool', 1)

class Billboard( nodetypes.Children, nodetypes.Transforming, node.Node ):
    PROTO = 'Billboard'
    #Fields
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    axisOfRotation = field.newField( 'axisOfRotation', 'SFVec3f', 1, [0.0, 1.0, 0.0])
    children = field.newField( 'children', 'MFNode', 1, list)
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    #Events
    removeChildren = field.newEvent( 'removeChildren', 'MFNode', 0)
    addChildren = field.newEvent( 'addChildren', 'MFNode', 0)

class Box( nodetypes.Geometry, node.Node ):
    PROTO = 'Box'
    #Fields
    size = field.newField( 'size', 'SFVec3f', 0, [2.0, 2.0, 2.0])
    #Events
    

class Collision( nodetypes.Children, nodetypes.Grouping, node.Node ):
    PROTO = 'Collision'
    #Fields
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    collide = field.newField( 'collide', 'SFBool', 1, 1)
    proxy = field.newField( 'proxy', 'SFNode', 0, node.NULL)
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    children = field.newField( 'children', 'MFNode', 1, list)
    #Events
    removeChildren = field.newEvent( 'removeChildren', 'MFNode', 0)
    collideTime = field.newEvent( 'collideTime', 'SFTime', 1)
    addChildren = field.newEvent( 'addChildren', 'MFNode', 0)

class Color( node.Node ):
    PROTO = 'Color'
    #Fields
    color = field.newField( 'color', 'MFColor', 1, list)
    #Events
    

class ColorInterpolator( nodetypes.Children, nodetypes.Interpolator, node.Node ):
    PROTO = 'ColorInterpolator'
    #Fields
    keyValue = field.newField( 'keyValue', 'MFColor', 1, list)
    key = field.newField( 'key', 'MFFloat', 1, list)
    #Events
    set_fraction = field.newEvent( 'set_fraction', 'SFFloat', 0)
    value_changed = field.newEvent( 'value_changed', 'SFColor', 1)

class Cone( nodetypes.Geometry, node.Node ):
    PROTO = 'Cone'
    #Fields
    bottom = field.newField( 'bottom', 'SFBool', 0, 1)
    side = field.newField( 'side', 'SFBool', 0, 1)
    bottomRadius = field.newField( 'bottomRadius', 'SFFloat', 0, 1.0)
    height = field.newField( 'height', 'SFFloat', 0, 2.0)
    #Events
    

class Coordinate( node.Node ):
    PROTO = 'Coordinate'
    #Fields
    point = field.newField( 'point', 'MFVec3f', 1, list)
    #Events
    

class CoordinateInterpolator( nodetypes.Children, nodetypes.Interpolator, node.Node ):
    PROTO = 'CoordinateInterpolator'
    #Fields
    keyValue = field.newField( 'keyValue', 'MFVec3f', 1, list)
    key = field.newField( 'key', 'MFFloat', 1, list)
    #Events
    set_fraction = field.newEvent( 'set_fraction', 'SFFloat', 0)
    value_changed = field.newEvent( 'value_changed', 'MFVec3f', 1)

class Cylinder( nodetypes.Geometry, node.Node ):
    PROTO = 'Cylinder'
    #Fields
    top = field.newField( 'top', 'SFBool', 0, 1)
    bottom = field.newField( 'bottom', 'SFBool', 0, 1)
    radius = field.newField( 'radius', 'SFFloat', 0, 1.0)
    side = field.newField( 'side', 'SFBool', 0, 1)
    height = field.newField( 'height', 'SFFloat', 0, 2.0)
    #Events
    

class CylinderSensor( nodetypes.Children, nodetypes.PointingSensor, node.Node ):
    PROTO = 'CylinderSensor'
    #Fields
    minAngle = field.newField( 'minAngle', 'SFFloat', 1, 0.0)
    offset = field.newField( 'offset', 'SFFloat', 1, 0.0)
    diskAngle = field.newField( 'diskAngle', 'SFFloat', 1, 0.26200000000000001)
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    autoOffset = field.newField( 'autoOffset', 'SFBool', 1, 1)
    maxAngle = field.newField( 'maxAngle', 'SFFloat', 1, -1.0)
    #Events
    rotation_changed = field.newEvent( 'rotation_changed', 'SFRotation', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)
    trackPoint_changed = field.newEvent( 'trackPoint_changed', 'SFVec3f', 1)

class DirectionalLight( nodetypes.Children, nodetypes.Light, node.Node ):
    PROTO = 'DirectionalLight'
    #Fields
    color = field.newField( 'color', 'SFColor', 1, [1.0, 1.0, 1.0])
    on = field.newField( 'on', 'SFBool', 1, 1)
    intensity = field.newField( 'intensity', 'SFFloat', 1, 1.0)
    ambientIntensity = field.newField( 'ambientIntensity', 'SFFloat', 1, 0.0)
    direction = field.newField( 'direction', 'SFVec3f', 1, [0.0, 0.0, -1.0])
    #Events
    

class ElevationGrid( nodetypes.Geometry, node.Node ):
    PROTO = 'ElevationGrid'
    #Fields
    zDimension = field.newField( 'zDimension', 'SFInt32', 0, 0)
    xSpacing = field.newField( 'xSpacing', 'SFFloat', 0, 0.0)
    creaseAngle = field.newField( 'creaseAngle', 'SFFloat', 0, 0.0)
    normal = field.newField( 'normal', 'SFNode', 1, node.NULL)
    solid = field.newField( 'solid', 'SFBool', 0, 1)
    ccw = field.newField( 'ccw', 'SFBool', 0, 1)
    texCoord = field.newField( 'texCoord', 'SFNode', 1, node.NULL)
    height = field.newField( 'height', 'MFFloat', 0, list)
    color = field.newField( 'color', 'SFNode', 1, node.NULL)
    colorPerVertex = field.newField( 'colorPerVertex', 'SFBool', 0, 1)
    xDimension = field.newField( 'xDimension', 'SFInt32', 0, 0)
    zSpacing = field.newField( 'zSpacing', 'SFFloat', 0, 0.0)
    normalPerVertex = field.newField( 'normalPerVertex', 'SFBool', 0, 1)
    #Events
    set_height = field.newEvent( 'set_height', 'MFFloat', 0)

class Extrusion( nodetypes.Geometry, node.Node ):
    PROTO = 'Extrusion'
    #Fields
    beginCap = field.newField( 'beginCap', 'SFBool', 0, 1)
    scale = field.newField( 'scale', 'MFVec2f', 0, [[1.0, 1.0]])
    creaseAngle = field.newField( 'creaseAngle', 'SFFloat', 0, 0.0)
    convex = field.newField( 'convex', 'SFBool', 0, 1)
    spine = field.newField( 'spine', 'MFVec3f', 0, [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    crossSection = field.newField( 'crossSection', 'MFVec2f', 0, [[1.0, 1.0], [1.0, -1.0], [-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]])
    ccw = field.newField( 'ccw', 'SFBool', 0, 1)
    solid = field.newField( 'solid', 'SFBool', 0, 1)
    endCap = field.newField( 'endCap', 'SFBool', 0, 1)
    orientation = field.newField( 'orientation', 'MFRotation', 0, [[0.0, 0.0, 1.0, 0.0]])
    #Events
    set_crossSection = field.newEvent( 'set_crossSection', 'MFVec2f', 0)
    set_orientation = field.newEvent( 'set_orientation', 'MFRotation', 0)
    set_scale = field.newEvent( 'set_scale', 'MFVec2f', 0)
    set_spine = field.newEvent( 'set_spine', 'MFVec3f', 0)

class Fog( nodetypes.Fog, nodetypes.Children, node.Node ):
    PROTO = 'Fog'
    #Fields
    color = field.newField( 'color', 'SFColor', 1, [1.0, 1.0, 1.0])
    visibilityRange = field.newField( 'visibilityRange', 'SFFloat', 1, 0.0)
    fogType = field.newField( 'fogType', 'SFString', 1, 'LINEAR')
    #Events
    set_bind = field.newEvent( 'set_bind', 'SFBool', 0)
    isBound = field.newEvent( 'isBound', 'SFBool', 1)

class FontStyle( node.Node ):
    PROTO = 'FontStyle'
    #Fields
    style = field.newField( 'style', 'SFString', 0, 'PLAIN')
    topToBottom = field.newField( 'topToBottom', 'SFBool', 0, 1)
    family = field.newField( 'family', 'MFString', 0, 'SERIF')
    language = field.newField( 'language', 'SFString', 0, '')
    horizontal = field.newField( 'horizontal', 'SFBool', 0, 1)
    justify = field.newField( 'justify', 'MFString', 0, ['BEGIN'])
    spacing = field.newField( 'spacing', 'SFFloat', 0, 1.0)
    leftToRight = field.newField( 'leftToRight', 'SFBool', 0, 1)
    size = field.newField( 'size', 'SFFloat', 0, 1.0)
    
    #Events
    

class Group( nodetypes.Children, nodetypes.Grouping, node.Node ):
    PROTO = 'Group'
    #Fields
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    children = field.newField( 'children', 'MFNode', 1, list)
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    #Events
    removeChildren = field.newEvent( 'removeChildren', 'MFNode', 0)
    addChildren = field.newEvent( 'addChildren', 'MFNode', 0)

class ImageTexture( nodetypes.Texture, node.Node ):
    PROTO = 'ImageTexture'
    #Fields
    url = field.newField( 'url', 'MFString', 1, list)
    repeatS = field.newField( 'repeatS', 'SFBool', 0, 1)
    repeatT = field.newField( 'repeatT', 'SFBool', 0, 1)
    #Events
    

class IndexedFaceSet( nodetypes.Geometry, node.Node ):
    PROTO = 'IndexedFaceSet'
    #Fields
    colorIndex = field.newField( 'colorIndex', 'MFInt32', 0, list)
    normal = field.newField( 'normal', 'SFNode', 1, node.NULL)
    solid = field.newField( 'solid', 'SFBool', 0, 1)
    ccw = field.newField( 'ccw', 'SFBool', 0, 1)
    coordIndex = field.newField( 'coordIndex', 'MFInt32', 0, list)
    texCoord = field.newField( 'texCoord', 'SFNode', 1, node.NULL)
    normalPerVertex = field.newField( 'normalPerVertex', 'SFBool', 0, 1)
    color = field.newField( 'color', 'SFNode', 1, node.NULL)
    colorPerVertex = field.newField( 'colorPerVertex', 'SFBool', 0, 1)
    coord = field.newField( 'coord', 'SFNode', 1, node.NULL)
    convex = field.newField( 'convex', 'SFBool', 0, 1)
    normalIndex = field.newField( 'normalIndex', 'MFInt32', 0, list)
    texCoordIndex = field.newField( 'texCoordIndex', 'MFInt32', 0, list)
    creaseAngle = field.newField( 'creaseAngle', 'SFFloat', 0, 0.0)
    #Events
    set_coordIndex = field.newEvent( 'set_coordIndex', 'MFInt32', 0)
    set_texCoordIndex = field.newEvent( 'set_texCoordIndex', 'MFInt32', 0)
    set_colorIndex = field.newEvent( 'set_colorIndex', 'MFInt32', 0)
    set_normalIndex = field.newEvent( 'set_normalIndex', 'MFInt32', 0)

class IndexedLineSet( nodetypes.Geometry, node.Node ):
    PROTO = 'IndexedLineSet'
    #Fields
    color = field.newField( 'color', 'SFNode', 1, node.NULL)
    colorPerVertex = field.newField( 'colorPerVertex', 'SFBool', 0, 1)
    colorIndex = field.newField( 'colorIndex', 'MFInt32', 0, list)
    coord = field.newField( 'coord', 'SFNode', 1, node.NULL)
    coordIndex = field.newField( 'coordIndex', 'MFInt32', 0, list)
    #Events
    set_coordIndex = field.newEvent( 'set_coordIndex', 'MFInt32', 0)
    set_colorIndex = field.newEvent( 'set_colorIndex', 'MFInt32', 0)

class Inline( nodetypes.Children, nodetypes.Traversable, node.Node ):
    PROTO = 'Inline'
    #Fields
    url = field.newField( 'url', 'MFString', 1, list)
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    #Events
    

class LOD( nodetypes.Children, nodetypes.Traversable, node.Node ):
    PROTO = 'LOD'
    #Fields
    range = field.newField( 'range', 'MFFloat', 0, list)
    center = field.newField( 'center', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    level = field.newField( 'level', 'MFNode', 1, list)
    #Events
    

class Material( node.Node ):
    PROTO = 'Material'
    #Fields
    specularColor = field.newField( 'specularColor', 'SFColor', 1, [0.0, 0.0, 0.0])
    emissiveColor = field.newField( 'emissiveColor', 'SFColor', 1, [0.0, 0.0, 0.0])
    transparency = field.newField( 'transparency', 'SFFloat', 1, 0.0)
    diffuseColor = field.newField( 'diffuseColor', 'SFColor', 1, [0.80000000000000004, 0.80000000000000004, 0.80000000000000004])
    ambientIntensity = field.newField( 'ambientIntensity', 'SFFloat', 1, 0.20000000000000001)
    shininess = field.newField( 'shininess', 'SFFloat', 1, 0.20000000000000001)
    #Events
    

class MovieTexture( nodetypes.Auditory, nodetypes.Texture, nodetypes.TimeDependent, node.Node ):
    PROTO = 'MovieTexture'
    #Fields
    stopTime = field.newField( 'stopTime', 'SFTime', 1, 0.0)
    startTime = field.newField( 'startTime', 'SFTime', 1, 0.0)
    url = field.newField( 'url', 'MFString', 1, list)
    speed = field.newField( 'speed', 'SFFloat', 1, 1.0)
    repeatS = field.newField( 'repeatS', 'SFBool', 0, 1)
    repeatT = field.newField( 'repeatT', 'SFBool', 0, 1)
    loop = field.newField( 'loop', 'SFBool', 1, 0)
    #Events
    duration_changed = field.newEvent( 'duration_changed', 'SFFloat', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)

class NavigationInfo( nodetypes.Children, nodetypes.NavigationInfo, node.Node ):
    PROTO = 'NavigationInfo'
    #Fields
    speed = field.newField( 'speed', 'SFFloat', 1, 1.0)
    avatarSize = field.newField( 'avatarSize', 'MFFloat', 1, [0.25, 1.6000000000000001, 0.75])
    headlight = field.newField( 'headlight', 'SFBool', 1, 1)
    type = field.newField( 'type', 'MFString', 1, ['WALK'])
    visibilityLimit = field.newField( 'visibilityLimit', 'SFFloat', 1, 0.0)
    #Events
    set_bind = field.newEvent( 'set_bind', 'SFBool', 0)
    isBound = field.newEvent( 'isBound', 'SFBool', 1)

class Normal( node.Node ):
    PROTO = 'Normal'
    #Fields
    vector = field.newField( 'vector', 'MFVec3f', 1, list)
    #Events
    

class NormalInterpolator( nodetypes.Children, nodetypes.Interpolator, node.Node ):
    PROTO = 'NormalInterpolator'
    #Fields
    keyValue = field.newField( 'keyValue', 'MFVec3f', 1, list)
    key = field.newField( 'key', 'MFFloat', 1, list)
    #Events
    set_fraction = field.newEvent( 'set_fraction', 'SFFloat', 0)
    value_changed = field.newEvent( 'value_changed', 'MFVec3f', 1)

class OrientationInterpolator( nodetypes.Children, nodetypes.Interpolator, node.Node ):
    PROTO = 'OrientationInterpolator'
    #Fields
    keyValue = field.newField( 'keyValue', 'MFRotation', 1, list)
    key = field.newField( 'key', 'MFFloat', 1, list)
    #Events
    set_fraction = field.newEvent( 'set_fraction', 'SFFloat', 0)
    value_changed = field.newEvent( 'value_changed', 'SFRotation', 1)

class PixelTexture( nodetypes.Texture, node.Node ):
    PROTO = 'PixelTexture'
    #Fields
    image = field.newField( 'image', 'SFImage', 1, [0, 0, 0])
    repeatS = field.newField( 'repeatS', 'SFBool', 0, 1)
    repeatT = field.newField( 'repeatT', 'SFBool', 0, 1)
    #Events
    

class PlaneSensor( nodetypes.Children, nodetypes.PointingSensor, node.Node ):
    PROTO = 'PlaneSensor'
    #Fields
    maxPosition = field.newField( 'maxPosition', 'SFVec2f', 1, [-1.0, -1.0])
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    autoOffset = field.newField( 'autoOffset', 'SFBool', 1, 1)
    minPosition = field.newField( 'minPosition', 'SFVec2f', 1, [0.0, 0.0])
    offset = field.newField( 'offset', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    #Events
    translation_changed = field.newEvent( 'translation_changed', 'SFVec3f', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)
    trackPoint_changed = field.newEvent( 'trackPoint_changed', 'SFVec3f', 1)

class PointLight( nodetypes.Children, nodetypes.Light, node.Node ):
    PROTO = 'PointLight'
    #Fields
    on = field.newField( 'on', 'SFBool', 1, 1)
    intensity = field.newField( 'intensity', 'SFFloat', 1, 1.0)
    attenuation = field.newField( 'attenuation', 'SFVec3f', 1, [1.0, 0.0, 0.0])
    radius = field.newField( 'radius', 'SFFloat', 1, 100.0)
    location = field.newField( 'location', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    color = field.newField( 'color', 'SFColor', 1, [1.0, 1.0, 1.0])
    ambientIntensity = field.newField( 'ambientIntensity', 'SFFloat', 1, 0.0)
    #Events
    

class PointSet( nodetypes.Geometry, node.Node ):
    PROTO = 'PointSet'
    #Fields
    color = field.newField( 'color', 'SFNode', 1, node.NULL)
    coord = field.newField( 'coord', 'SFNode', 1, node.NULL)
    
    size = field.newField( 'size','SFFloat',1, 1.0 )
    minSize = field.newField( 'minSize','SFFloat',1, 0.0 )
    maxSize = field.newField( 'maxSize','SFFloat',1, 1.0 )
    attenuation = field.newField( 'attenuation','SFVec3f',1,[1.0,0.0,0.0])
    

class PositionInterpolator( nodetypes.Children, nodetypes.Interpolator, node.Node ):
    PROTO = 'PositionInterpolator'
    #Fields
    keyValue = field.newField( 'keyValue', 'MFVec3f', 1, list)
    key = field.newField( 'key', 'MFFloat', 1, list)
    #Events
    set_fraction = field.newEvent( 'set_fraction', 'SFFloat', 0)
    value_changed = field.newEvent( 'value_changed', 'SFVec3f', 1)

class ProximitySensor( nodetypes.Sensor, nodetypes.Children, node.Node ):
    PROTO = 'ProximitySensor'
    #Fields
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    center = field.newField( 'center', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    size = field.newField( 'size', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    #Events
    position_changed = field.newEvent( 'position_changed', 'SFVec3f', 1)
    enterTime = field.newEvent( 'enterTime', 'SFTime', 1)
    exitTime = field.newEvent( 'exitTime', 'SFTime', 1)
    orientation_changed = field.newEvent( 'orientation_changed', 'SFRotation', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)

class ScalarInterpolator( nodetypes.Children, nodetypes.Interpolator, node.Node ):
    PROTO = 'ScalarInterpolator'
    #Fields
    keyValue = field.newField( 'keyValue', 'MFFloat', 1, list)
    key = field.newField( 'key', 'MFFloat', 1, list)
    #Events
    set_fraction = field.newEvent( 'set_fraction', 'SFFloat', 0)
    value_changed = field.newEvent( 'value_changed', 'SFFloat', 1)

class Shape( nodetypes.Children, nodetypes.Rendering, node.Node ):
    PROTO = 'Shape'
    #Fields
    geometry = field.newField( 'geometry', 'SFNode', 1, node.NULL)
    appearance = field.newField( 'appearance', 'SFNode', 1, node.NULL)
    #Events
    

class Sound( nodetypes.Auditory, nodetypes.Children, node.Node ):
    PROTO = 'Sound'
    #Fields
    priority = field.newField( 'priority', 'SFFloat', 1, 0.0)
    minFront = field.newField( 'minFront', 'SFFloat', 1, 1.0)
    intensity = field.newField( 'intensity', 'SFFloat', 1, 1.0)
    location = field.newField( 'location', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    source = field.newField( 'source', 'SFNode', 1, node.NULL)
    maxBack = field.newField( 'maxBack', 'SFFloat', 1, 10.0)
    minBack = field.newField( 'minBack', 'SFFloat', 1, 1.0)
    maxFront = field.newField( 'maxFront', 'SFFloat', 1, 10.0)
    spatialize = field.newField( 'spatialize', 'SFBool', 0, 1)
    direction = field.newField( 'direction', 'SFVec3f', 1, [0.0, 0.0, 1.0])
    #Events
    

class Sphere( nodetypes.Geometry, node.Node ):
    PROTO = 'Sphere'
    #Fields
    radius = field.newField( 'radius', 'SFFloat', 0, 1.0)
    #Events
    

class SphereSensor( nodetypes.Children, nodetypes.PointingSensor, node.Node ):
    PROTO = 'SphereSensor'
    #Fields
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    autoOffset = field.newField( 'autoOffset', 'SFBool', 1, 1)
    offset = field.newField( 'offset', 'SFRotation', 1, [0.0, 1.0, 0.0, 0.0])
    #Events
    rotation_changed = field.newEvent( 'rotation_changed', 'SFRotation', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)
    trackPoint_changed = field.newEvent( 'trackPoint_changed', 'SFVec3f', 1)

class SpotLight( nodetypes.Children, nodetypes.Light, node.Node ):
    PROTO = 'SpotLight'
    #Fields
    on = field.newField( 'on', 'SFBool', 1, 1)
    direction = field.newField( 'direction', 'SFVec3f', 1, [0.0, 0.0, -1.0])
    attenuation = field.newField( 'attenuation', 'SFVec3f', 1, [1.0, 0.0, 0.0])
    radius = field.newField( 'radius', 'SFFloat', 1, 100.0)
    location = field.newField( 'location', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    intensity = field.newField( 'intensity', 'SFFloat', 1, 1.0)
    color = field.newField( 'color', 'SFColor', 1, [1.0, 1.0, 1.0])
    ambientIntensity = field.newField( 'ambientIntensity', 'SFFloat', 1, 0.0)
    beamWidth = field.newField( 'beamWidth', 'SFFloat', 1, 1.5707960000000001)
    cutOffAngle = field.newField( 'cutOffAngle', 'SFFloat', 1, 0.78539800000000004)
    #Events
    

class Switch( nodetypes.Children, nodetypes.Traversable, node.Node ):
    PROTO = 'Switch'
    #Fields
    whichChoice = field.newField( 'whichChoice', 'SFInt32', 1, -1)
    choice = field.newField( 'choice', 'MFNode', 1, list)
    #Events
    

class Text( nodetypes.Geometry, node.Node ):
    PROTO = 'Text'
    #Fields
    length = field.newField( 'length', 'MFFloat', 1, list)
    fontStyle = field.newField( 'fontStyle', 'SFNode', 1, node.NULL)
    string = field.newField( 'string', 'MFString', 1, list)
    maxExtent = field.newField( 'maxExtent', 'SFFloat', 1, 0.0)
    #Events
    

class TextureCoordinate( node.Node ):
    PROTO = 'TextureCoordinate'
    #Fields
    point = field.newField( 'point', 'MFVec2f', 1, list)
    #Events
    

class TextureTransform( node.Node ):
    PROTO = 'TextureTransform'
    #Fields
    rotation = field.newField( 'rotation', 'SFFloat', 1, 0.0)
    scale = field.newField( 'scale', 'SFVec2f', 1, [1.0, 1.0])
    translation = field.newField( 'translation', 'SFVec2f', 1, [0.0, 0.0])
    center = field.newField( 'center', 'SFVec2f', 1, [0.0, 0.0])
    #Events
    

class TimeSensor( nodetypes.Sensor, nodetypes.Children, nodetypes.TimeDependent, node.Node ):
    PROTO = 'TimeSensor'
    #Fields
    cycleInterval = field.newField( 'cycleInterval', 'SFTime', 1, 1.0)
    stopTime = field.newField( 'stopTime', 'SFTime', 1, 0.0)
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    loop = field.newField( 'loop', 'SFBool', 1, 0)
    startTime = field.newField( 'startTime', 'SFTime', 1, 0.0)
    #Events
    fraction_changed = field.newEvent( 'fraction_changed', 'SFFloat', 1)
    cycleTime = field.newEvent( 'cycleTime', 'SFTime', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)
    time = field.newEvent( 'time', 'SFTime', 1)

class TouchSensor( nodetypes.Children, nodetypes.PointingSensor, node.Node ):
    PROTO = 'TouchSensor'
    #Fields
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    #Events
    isOver = field.newEvent( 'isOver', 'SFBool', 1)
    hitTexCoord_changed = field.newEvent( 'hitTexCoord_changed', 'SFVec2f', 1)
    hitNormal_changed = field.newEvent( 'hitNormal_changed', 'SFVec3f', 1)
    hitPoint_changed = field.newEvent( 'hitPoint_changed', 'SFVec3f', 1)
    touchTime = field.newEvent( 'touchTime', 'SFTime', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)

class Transform( nodetypes.Children, nodetypes.Transforming, node.Node ):
    PROTO = 'Transform'
    #Fields
    scale = field.newField( 'scale', 'SFVec3f', 1, [1.0, 1.0, 1.0])
    center = field.newField( 'center', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    bboxCenter = field.newField( 'bboxCenter', 'SFVec3f', 0, [0.0, 0.0, 0.0])
    translation = field.newField( 'translation', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    scaleOrientation = field.newField( 'scaleOrientation', 'SFRotation', 1, [0.0, 0.0, 1.0, 0.0])
    rotation = field.newField( 'rotation', 'SFRotation', 1, [0.0, 0.0, 1.0, 0.0])
    bboxSize = field.newField( 'bboxSize', 'SFVec3f', 0, [-1.0, -1.0, -1.0])
    children = field.newField( 'children', 'MFNode', 1, list)
    #Events
    removeChildren = field.newEvent( 'removeChildren', 'MFNode', 0)
    addChildren = field.newEvent( 'addChildren', 'MFNode', 0)

class Viewpoint( nodetypes.Children, nodetypes.Viewpoint, node.Node ):
    PROTO = 'Viewpoint'
    #Fields
    jump = field.newField( 'jump', 'SFBool', 1, 1)
    position = field.newField( 'position', 'SFVec3f', 1, [0.0, 0.0, 10.0])
    fieldOfView = field.newField( 'fieldOfView', 'SFFloat', 1, 0.78539800000000004)
    orientation = field.newField( 'orientation', 'SFRotation', 1, [0.0, 0.0, 1.0, 0.0])
    description = field.newField( 'description', 'SFString', 0, '')
    #Events
    set_bind = field.newEvent( 'set_bind', 'SFBool', 0)
    bindTime = field.newEvent( 'bindTime', 'SFTime', 1)
    isBound = field.newEvent( 'isBound', 'SFBool', 1)

class VisibilitySensor( nodetypes.Sensor, nodetypes.Children, node.Node ):
    PROTO = 'VisibilitySensor'
    #Fields
    enabled = field.newField( 'enabled', 'SFBool', 1, 1)
    center = field.newField( 'center', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    size = field.newField( 'size', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    #Events
    exitTime = field.newEvent( 'exitTime', 'SFTime', 1)
    enterTime = field.newEvent( 'enterTime', 'SFTime', 1)
    isActive = field.newEvent( 'isActive', 'SFBool', 1)

class WorldInfo( nodetypes.Children, node.Node ):
    PROTO = 'WorldInfo'
    #Fields
    info = field.newField( 'info', 'MFString', 0, list)
    title = field.newField( 'title', 'SFString', 0, '')
    #Events
    
# clean up namespace
del field, node, nodetypes