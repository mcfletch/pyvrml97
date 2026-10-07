"""The X3D Fast Infoset vocabulary (ISO/IEC 19776-3, Annex A)

What a compressed binary X3D document's indexes refer to: the element and
attribute names of tables A.2 and A.3, the attribute values of table A.4,
and the encoding algorithms of table A.5. `specs/x3d/fast-infoset.md`
records where each table comes from and the points below.

Web3D's own `.x3db` files, which name `urn:web3d:x3d:fi-vocabulary-3.2`,
number attribute names as table A.3 does up to 53 and as one more than it
does from 57: their vocabulary has one name more, among indexes 54 to 56,
which no edition publishes. The attribute names a document adds are
numbered from 1026, so that table has 1025 entries; none of the files refers
to one past the published names. `attribute_names()` numbers them as the
files do, with the entries no edition names unknown (None). The same
numbering is used for every URI below: no published file numbers one
otherwise.

The same files write some values a second time under other names (a meta's
content as `key`, an Anchor's url as `load` and `visible`); a reader reports
those as values its field does not take.

Of the X3D encoding algorithms, the files use one, delta-zlib integers, at
index 34 where table A.5 places it at 33, and in a layout that differs from
the text of 5.5.2; `delta_zlib_integers` reads that layout. The others are
named in the vocabulary and arrive undecoded.
"""

import zlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from vrml.x3d.fastinfoset import FastInfosetError, Vocabulary

__all__ = ['VOCABULARIES', 'vocabulary', 'attribute_names', 'delta_zlib_integers']

#: Table A.2 (3.3 edition), from index 1.
ELEMENT_NAMES = (
    'Shape', 'Appearance', 'Material', 'IndexedFaceSet', 'ProtoInstance', 'Transform',
    'ImageTexture', 'TextureTransform', 'Coordinate', 'Normal', 'Color', 'ColorRGBA',
    'TextureCoordinate', 'ROUTE', 'fieldValue', 'Group', 'LOD', 'Switch', 'Script',
    'IndexedTriangleFanSet', 'IndexedTriangleSet', 'IndexedTriangleStripSet',
    'MultiTexture', 'MultiTextureCoordinate', 'MultiTextureTransform', 'IndexedLineSet',
    'PointSet', 'StaticGroup', 'Sphere', 'Box', 'Cone', 'Anchor', 'Arc2D', 'ArcClose2D',
    'AudioClip', 'Background', 'Billboard', 'BooleanFilter', 'BooleanSequencer',
    'BooleanToggle', 'BooleanTrigger', 'Circle2D', 'Collision', 'ColorInterpolator',
    'Contour2D', 'ContourPolyline2D', 'CoordinateDouble', 'CoordinateInterpolator',
    'CoordinateInterpolator2D', 'Cylinder', 'CylinderSensor', 'DirectionalLight',
    'Disk2D', 'EXPORT', 'ElevationGrid', 'EspduTransform', 'ExternProtoDeclare',
    'Extrusion', 'FillProperties', 'Fog', 'FontStyle', 'GeoCoordinate',
    'GeoElevationGrid', 'GeoLOD', 'GeoLocation', 'GeoMetadata', 'GeoOrigin',
    'GeoPositionInterpolator', 'GeoTouchSensor', 'GeoViewpoint', 'HAnimDisplacer',
    'HAnimHumanoid', 'HAnimJoint', 'HAnimSegment', 'HAnimSite', 'IMPORT', 'IS',
    'Inline', 'IntegerSequencer', 'IntegerTrigger', 'KeySensor', 'LineProperties',
    'LineSet', 'LoadSensor', 'MetadataDouble', 'MetadataFloat', 'MetadataInteger',
    'MetadataSet', 'MetadataString', 'MovieTexture', 'NavigationInfo',
    'NormalInterpolator', 'NurbsCurve', 'NurbsCurve2D', 'NurbsOrientationInterpolator',
    'NurbsPatchSurface', 'NurbsPositionInterpolator', 'NurbsSet',
    'NurbsSurfaceInterpolator', 'NurbsSweptSurface', 'NurbsSwungSurface',
    'NurbsTextureCoordinate', 'NurbsTrimmedSurface', 'OrientationInterpolator',
    'PixelTexture', 'PlaneSensor', 'PointLight', 'Polyline2D', 'Polypoint2D',
    'PositionInterpolator', 'PositionInterpolator2D', 'ProtoBody', 'ProtoDeclare',
    'ProtoInterface', 'ProximitySensor', 'ReceiverPdu', 'Rectangle2D',
    'ScalarInterpolator', 'Scene', 'SignalPdu', 'Sound', 'SphereSensor', 'SpotLight',
    'StringSensor', 'Text', 'TextureBackground', 'TextureCoordinateGenerator',
    'TimeSensor', 'TimeTrigger', 'TouchSensor', 'TransmitterPdu', 'TriangleFanSet',
    'TriangleSet', 'TriangleSet2D', 'TriangleStripSet', 'Viewpoint', 'VisibilitySensor',
    'WorldInfo', 'X3D', 'component', 'connect', 'field', 'head', 'humanoidBodyType',
    'meta', 'CADAssembly', 'CADFace', 'CADLayer', 'CADPart', 'ComposedCubeMapTexture',
    'ComposedShader', 'ComposedTexture3D', 'FloatVertexAttribute', 'FogCoordinate',
    'GeneratedCubeMapTexture', 'ImageCubeMapTexture', 'ImageTexture3D',
    'IndexedQuadSet', 'LocalFog', 'Matrix3VertexAttribute', 'Matrix4VertexAttribute',
    'PackagedShader', 'PixelTexture3D', 'ProgramShader', 'QuadSet', 'ShaderPart',
    'ShaderProgram', 'TextureCoordinate3D', 'TextureCoordinate4D', 'TextureTransform3D',
    'TextureTransformMatrix3D', 'BallJoint', 'BoundedPhysicsModel', 'ClipPlane',
    'CollidableOffset', 'CollidableShape', 'CollisionCollection', 'CollisionSensor',
    'CollisionSpace', 'ColorDamper', 'ConeEmitter', 'Contact', 'CoordinateDamper',
    'DISEntityManager', 'DISEntityTypeMapping', 'DoubleAxisHingeJoint', 'EaseInEaseOut',
    'ExplosionEmitter', 'ForcePhysicsModel', 'GeoProximitySensor', 'GeoTransform',
    'Layer', 'LayerSet', 'Layout', 'LayoutGroup', 'LayoutLayer', 'LinePickSensor',
    'MotorJoint', 'OrientationChaser', 'OrientationDamper', 'OrthoViewpoint',
    'ParticleSystem', 'PickableGroup', 'PointEmitter', 'PointPickSensor',
    'PolylineEmitter', 'PositionChaser', 'PositionChaser2D', 'PositionDamper',
    'PositionDamper2D', 'PrimitivePickSensor', 'RigidBody', 'RigidBodyCollection',
    'ScalarChaser', 'ScreenFontStyle', 'ScreenGroup', 'SingleAxisHingeJoint',
    'SliderJoint', 'SplinePositionInterpolator', 'SplinePositionInterpolator2D',
    'SplineScalarInterpolator', 'SquadOrientationInterpolator', 'SurfaceEmitter',
    'TexCoordDamper2D', 'TextureProperties', 'TransformSensor', 'TwoSidedMaterial',
    'UniversalJoint', 'ViewpointGroup', 'Viewport', 'VolumeEmitter', 'VolumePickSensor',
    'WindPhysicsModel', 'BlendedVolumeStyle', 'BoundaryEnhancementVolumeStyle',
    'CartoonVolumeStyle', 'ComposedVolumeStyle', 'EdgeEnhancementVolumeStyle',
    'IsoSurfaceVolumeData', 'MetadataBoolean', 'OpacityMapVolumeStyle',
    'ProjectionVolumeStyle', 'SegmentedVolumeData', 'ShadedVolumeStyle',
    'SilhouetteEnhancementVolumeStyle', 'ToneMappedVolumeStyle', 'VolumeData',
    'ColorChaser', 'CoordinateChaser', 'ScalarDamper', 'TexCoordChaser2D', 'unit',
)

#: Table A.3 (3.3 edition) as published, from index 1.
ATTRIBUTE_NAMES = (
    'DEF', 'USE', 'containerField', 'fromNode', 'fromField', 'toNode', 'toField',
    'name', 'value', 'color', 'colorIndex', 'coordIndex', 'texCoordIndex',
    'normalIndex', 'colorPerVertex', 'normalPerVertex', 'rotation', 'scale', 'center',
    'scaleOrientation', 'translation', 'url', 'repeatS', 'repeatT', 'point', 'vector',
    'range', 'ambientIntensity', 'diffuseColor', 'emissiveColor', 'shininess',
    'specularColor', 'transparency', 'whichChoice', 'index', 'mode', 'source',
    'function', 'alpha', 'vertexCount', 'radius', 'size', 'height', 'solid', 'ccw',
    'key', 'keyValue', 'enabled', 'direction', 'position', 'orientation', 'bboxCenter',
    'bboxSize', 'AS', 'InlineDEF', 'accessType', 'actionKeyPress', 'actionKeyRelease',
    'address', 'altKey', 'antennaLocation', 'antennaPatternLength',
    'antennaPatternType', 'applicationID', 'articulationParameterArray',
    'articulationParameterChangeIndicatorArray', 'articulationParameterCount',
    'articulationParameterDesignatorArray', 'articulationParameterIdPartAttachedArray',
    'articulationParameterTypeArray', 'attenuation', 'autoOffset', 'avatarSize',
    'axisOfRotation', 'backUrl', 'beamWidth', 'beginCap', 'bindTime', 'bottom',
    'bottomRadius', 'bottomUrl', 'centerOfMass', 'centerOfRotation', 'child1Url',
    'child2Url', 'child3Url', 'child4Url', 'class', 'closureType', 'collideTime',
    'content', 'controlKey', 'controlPoint', 'convex', 'coordinateSystem', 'copyright',
    'creaseAngle', 'crossSection', 'cryptoKeyID', 'cryptoSystem', 'cutOffAngle',
    'cycleInterval', 'cycleTime', 'data', 'dataFormat', 'dataLength', 'dataUrl', 'date',
    'deadReckoning', 'deletionAllowed', 'description', 'detonateTime', 'dir',
    'directOutput', 'diskAngle', 'displacements', 'documentation', 'elapsedTime',
    'ellipsoid', 'encodingScheme', 'endAngle', 'endCap', 'enterTime', 'enteredText',
    'entityCategory', 'entityCountry', 'entityDomain', 'entityExtra', 'entityID',
    'entityKind', 'entitySpecific', 'entitySubCategory', 'exitTime', 'extent', 'family',
    'fanCount', 'fieldOfView', 'filled', 'finalText', 'fireMissionIndex', 'fired1',
    'fired2', 'firedTime', 'firingRange', 'firingRate', 'fogType', 'forceID',
    'frequency', 'frontUrl', 'fuse', 'geoCoords', 'geoGridOrigin', 'geoSystem',
    'groundAngle', 'groundColor', 'hatchColor', 'hatchStyle', 'hatched', 'headlight',
    'horizontal', 'horizontalDatum', 'http-equiv', 'image', 'importedDEF', 'info',
    'innerRadius', 'inputFalse', 'inputNegate', 'inputSource', 'inputTrue',
    'integerKey', 'intensity', 'jump', 'justify', 'keyPress', 'keyRelease', 'knot',
    'lang', 'language', 'leftToRight', 'leftUrl', 'length',
    'lengthOfModulationParameters', 'level', 'limitOrientation', 'lineSegments',
    'linearAcceleration', 'linearVelocity', 'linetype', 'linewidthScaleFactor',
    'llimit', 'load', 'loadTime', 'localDEF', 'location', 'loop', 'marking', 'mass',
    'maxAngle', 'maxBack', 'maxExtent', 'maxFront', 'maxPosition', 'metadataFormat',
    'minAngle', 'minBack', 'minFront', 'minPosition', 'modulationTypeDetail',
    'modulationTypeMajor', 'modulationTypeSpreadSpectrum', 'modulationTypeSystem',
    'momentsOfInertia', 'multicastRelayHost', 'multicastRelayPort',
    'munitionApplicationID', 'munitionEndPoint', 'munitionEntityID', 'munitionQuantity',
    'munitionSiteID', 'munitionStartPoint', 'mustEvaluate', 'navType', 'networkMode',
    'next', 'nodeField', 'offset', 'on', 'order', 'originator', 'outerRadius',
    'parameter', 'pauseTime', 'pitch', 'points', 'port', 'power', 'previous',
    'priority', 'profile', 'progress', 'protoField', 'radioEntityTypeCategory',
    'radioEntityTypeCountry', 'radioEntityTypeDomain', 'radioEntityTypeKind',
    'radioEntityTypeNomenclature', 'radioEntityTypeNomenclatureVersion', 'radioID',
    'readInterval', 'receivedPower', 'receiverState', 'reference',
    'relativeAntennaLocation', 'resolution', 'resumeTime', 'rightUrl', 'rootUrl',
    'rotateYUp', 'rtpHeaderExpected', 'sampleRate', 'samples', 'shiftKey', 'side',
    'siteID', 'skinCoordIndex', 'skinCoordWeight', 'skyAngle', 'skyColor', 'spacing',
    'spatialize', 'speed', 'speedFactor', 'spine', 'startAngle', 'startTime',
    'stiffness', 'stopTime', 'string', 'stripCount', 'style', 'summary', 'tdlType',
    'tessellation', 'tessellationScale', 'time', 'timeOut', 'timestamp', 'title',
    'toggle', 'top', 'topToBottom', 'topUrl', 'touchTime', 'transmitFrequencyBandwidth',
    'transmitState', 'transmitterApplicationID', 'transmitterEntityID',
    'transmitterRadioID', 'transmitterSiteID', 'transparent', 'triggerTime',
    'triggerTrue', 'triggerValue', 'type', 'uDimension', 'uKnot', 'uOrder',
    'uTessellation', 'ulimit', 'vDimension', 'vKnot', 'vOrder', 'vTessellation',
    'version', 'verticalDatum', 'vertices', 'visibilityLimit', 'visibilityRange',
    'warhead', 'weight', 'whichGeometry', 'writeInterval', 'xDimension', 'xSpacing',
    'yScale', 'zDimension', 'zSpacing', 'visible', 'repeatR', 'texture', 'back',
    'front', 'left', 'right', 'parts', 'isSelected', 'isValid', 'numComponents',
    'depth', 'update', 'fogCoord', 'texCoord', 'activate', 'programs', 'matrix',
    'anchorPoint', 'body1', 'body2', 'forceOutput', 'body1AnchorPoint',
    'body2AnchorPoint', 'plane', 'appliedParameters', 'bounce', 'frictionCoefficients',
    'minBounceSpeed', 'slipFactors', 'softnessConstantForceMix',
    'softnessErrorCorrection', 'surfaceSpeed', 'isActive', 'useGeometry',
    'set_destination', 'set_value', 'tau', 'tolerance', 'value_changed',
    'initialDestination', 'initialValue', 'angle', 'variation', 'surfaceArea',
    'frictionDirection', 'slipCoefficients', 'category', 'country', 'domain', 'extra',
    'kind', 'specific', 'subcategory', 'axis1', 'axis2', 'desiredAngularVelocity1',
    'desiredAngularVelocity2', 'maxAngle1', 'maxTorque1', 'maxTorque2', 'minAngle1',
    'stopBounce1', 'stopConstantForceMix1', 'stopErrorCorrection1',
    'suspensionErrorCorrection', 'suspensionForce', 'body1Axis', 'body2Axis',
    'hinge1Angle', 'hinge1AngleRate', 'hinge2Angle', 'hinge2AngleRate', 'set_fraction',
    'easeInEaseOut', 'modifiedFraction_changed', 'force', 'geoCenter',
    'centerOfRotation_changed', 'geoCoord_changed', 'orientation_changed',
    'position_changed', 'isPickable', 'viewport', 'activeLayer', 'align', 'offsetUnits',
    'scaleMode', 'sizeUnits', 'layout', 'objectType', 'pickedNormal', 'pickedPoint',
    'pickedTextureCoordinate', 'intersectionType', 'sortOrder', 'axis1Angle',
    'axis1Torque', 'axis2Angle', 'axis2Torque', 'axis3Angle', 'axis3Torque',
    'enabledAxies', 'motor1Axis', 'motor2Axis', 'motor3Axis', 'stop1Bounce',
    'stop1ErrorCorrection', 'stop2Bounce', 'stop2ErrorCorrection', 'stop3Bounce',
    'stop3ErrorCorrection', 'motor1Angle', 'motor1AngleRate', 'motor2Angle',
    'motor2AngleRate', 'motor3Angle', 'motor3AngleRate', 'autoCalc', 'duration',
    'retainUserOffsets', 'isBound', 'appearance', 'createParticles',
    'lifetimeVariation', 'maxParticles', 'particleLifetime', 'particleSize', 'colorKey',
    'geometryType', 'texCoordKey', 'pickable', 'angularDampingFactor',
    'angularVelocity', 'autoDamp', 'autoDisable', 'disableAngularSpeed',
    'disableLinearSpeed', 'disableTime', 'finiteRotationAxis', 'fixed', 'forces',
    'inertia', 'linearDampingFactor', 'torques', 'useFiniteRotation', 'useGlobalForce',
    'constantForceMix', 'constantSurfaceThickness', 'errorCorrection', 'iterations',
    'maxCorrectionSpeed', 'preferAccuracy', 'pointSize', 'stopBounce',
    'stopErrorCorrection', 'angleRate', 'maxSeparation', 'minSeparation', 'separation',
    'separationRate', 'closed', 'keyVelocity', 'normalizeVelocity', 'surface',
    'anisotropicDegree', 'borderColor', 'borderWidth', 'boundaryModeS', 'boundaryModeT',
    'boundaryModeR', 'magnificationFilter', 'minificationFilter', 'textureCompression',
    'texturePriority', 'generateMipMaps', 'targetObject', 'backAmbientIntensity',
    'backDiffuseColor', 'backEmissiveColor', 'backShininess', 'backSpecularColor',
    'separateBackColor', 'displayed', 'clipBoundary', 'internal', 'gustiness',
    'turbulence', 'unitCategory', 'unitName', 'unitConversionFactor', 'weightConstant1',
    'weightConstant2', 'weightFunction1', 'weightFunction2', 'boundaryOpacity',
    'opacityFactor', 'retainedOpacity', 'colorSteps', 'orthogonalColor',
    'parallelColor', 'ordered', 'edgeColor', 'gradientThreshold', 'contourStepSize',
    'dimensions', 'surfaceTolerance', 'surfaceValues', 'intensityThreshold',
    'segmentEnabled', 'lighting', 'shadows', 'phaseFunction',
    'silhouetteBoundaryOpacity', 'silhouetteRetainedOpacity', 'silhouetteSharpness',
    'coolColor', 'warmColor',
)

#: Table A.4.
ATTRIBUTE_VALUES = ('false', 'true')

#: Table A.5: the X3D encoding algorithms, by the index it gives them.
ALGORITHM_NAMES = {
    32: 'encoder://web3d.org/QuantizedFloatArrayEncoder',
    33: 'encoder://web3d.org/DeltazlibIntArrayEncoder',
    34: 'encoder://web3d.org/QuantizedzlibFloatArrayEncoder',
    35: 'encoder://web3d.org/zlibFloatArrayEncoder',
    36: 'encoder://web3d.org/QuantizedDoubleArrayEncoder',
    37: 'encoder://web3d.org/zlibDoubleArrayEncoder',
    38: 'encoder://web3d.org/QuantizedzlibDoubleArrayEncoder',
    39: 'encoder://web3d.org/RangeIntArrayEncoder',
}

#: The index Web3D's files write delta-zlib integers at.
DELTA_ZLIB_INDEX = 34

#: The most integers a delta-zlib value may hold: 2 GiB of them inflated.
MAX_INTEGERS = 2 ** 29

#: The size of the attribute name table, after which a document's own names
#: are numbered.
ATTRIBUTE_TABLE_SIZE = 1025

@dataclass(frozen=True)
class Edition:
    """How long an edition's name tables are, and its entries that differ
    from the 3.3 tables, by index"""

    elements: int
    attributes: int
    element: "Mapping[int, str]" = field(default_factory=dict)
    attribute: "Mapping[int, str]" = field(default_factory=dict)


EDITIONS = {
    '3.2': Edition(233, 516, {224: 'TexCoordDamper'}, {350: 'mustOutput'}),
    '3.3': Edition(252, 546),
}


def element_names(edition: str) -> "list[Optional[str]]":
    """Table A.2 of `edition`, '3.2' or '3.3'"""
    found = EDITIONS[edition]
    names: "list[Optional[str]]" = list(ELEMENT_NAMES[:found.elements])
    for index, name in found.element.items():
        names[index - 1] = name
    return names


def attribute_names(edition: str) -> "list[Optional[str]]":
    """Table A.3 of `edition` as Web3D's files number it, ATTRIBUTE_TABLE_SIZE long"""
    found = EDITIONS[edition]
    published: "list[Optional[str]]" = list(ATTRIBUTE_NAMES[:found.attributes])
    for index, name in found.attribute.items():
        published[index - 1] = name
    names = published[:53] + [None, None, None] + published[55:]
    return names + [None] * (ATTRIBUTE_TABLE_SIZE - len(names))


def delta_zlib_integers(octets: bytes) -> Any:
    """Integers as Web3D's files write them with delta-zlib

    A 32-bit big-endian count, a span octet, and a zlib stream of that many
    32-bit big-endian integers, each one more than the difference from the
    integer `span` places before it (the value itself for the first `span`,
    and for every one where the span is 0).
    """
    if len(octets) < 5:
        raise FastInfosetError('A delta-zlib value of %d octets' % len(octets))
    count = int.from_bytes(octets[:4], 'big')
    span = octets[4]
    if count > MAX_INTEGERS:
        raise FastInfosetError('A delta-zlib value of %d integers' % count)
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(octets[5:], 4 * count)
    except zlib.error as error:
        raise FastInfosetError('A delta-zlib value: %s' % error) from None
    if len(raw) != 4 * count or inflater.unconsumed_tail:
        raise FastInfosetError('A delta-zlib value is not %d integers' % count)
    values = np.frombuffer(raw, dtype='>i4').astype(np.int64) - 1
    if span:
        for start in range(min(span, count)):
            values[start::span] = np.cumsum(values[start::span])
    return values


def vocabulary(edition: str) -> "Callable[[], Vocabulary]":
    """A function making the vocabulary of `edition` afresh"""
    def make() -> Vocabulary:
        made = Vocabulary(
            element_names=element_names(edition),
            attribute_names=attribute_names(edition),
            attribute_values=list(ATTRIBUTE_VALUES),
            algorithm_names=dict(ALGORITHM_NAMES),
            next_algorithm=max(ALGORITHM_NAMES) + 1,
        )
        made.algorithms[DELTA_ZLIB_INDEX] = delta_zlib_integers
        return made
    return make


#: The external vocabularies an X3D document may name, by URI.
VOCABULARIES = {
    'urn:web3d:x3d:fi-vocabulary-3.2': vocabulary('3.2'),
    'urn:web3d:x3d:fi-vocabulary-3.3': vocabulary('3.3'),
    'urn:web3d:x3d:fi-vocabulary-4.0': vocabulary('3.3'),
}
