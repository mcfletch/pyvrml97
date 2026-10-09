"""X_ITE's own nodes: the X_ITE component, and the fields it adds to X3D's

X_ITE (https://create3000.github.io/x_ite/) is an X3D browser that declares
nodes beyond X3D 4.1. Most are in a component of its own, `X_ITE`: material
extension nodes that go in a material's `extensions`, `BlendMode` and
`DepthMode` in an `Appearance`, `InstancedShape`, and
`SpecularGlossinessMaterial`. `ImageTextureAtlas` is in Texturing3D. It adds
`extensions` to `PhysicalMaterial` and `blendMode` and `depthMode` to
`Appearance`, which this module's `PhysicalMaterial` and `Appearance` carry.

`VOCABULARY` is X3D's nodes with these laid over them: what the readers
build a document's nodes from and what the writers hold a node's fields to.
A document using them is written with the component statement X_ITE loads
them from (`COMPONENT`); each node names the first X3D version X_ITE
accepts it in (`SINCE`), and VRML97 has none of them.

The names, types, defaults and ranges are X_ITE 16.4.3's: its X3DUOM
extension (`dist/X3DUOM.xml`) and the field definitions of its X_ITE and
Texturing3D components, published under the MIT licence.
"""

from typing import Any

from vrml import field, node
from vrml import fieldtypes  # noqa: F401 registers the field types used below
from vrml.x3d import nodes as x3d

#: The component X_ITE declares its nodes in, and its one level.
COMPONENT = ('X_ITE', 1)


def _texture(name: str) -> "tuple[field.Field, field.Field]":
    """A texture field and its `...Mapping` label, in X3D 4's pattern"""
    return (field.newField(name, 'SFNode', 1, node.NULL),
            field.newField(name + 'Mapping', 'SFString', 1, ''))


class X3DMaterialExtensionNode(x3d.X3DNode):
    """X_ITE abstract node type: a part of a material, in its `extensions`"""

    COMPONENT = COMPONENT
    CONTAINER_FIELD = 'extensions'
    SINCE = '4.0'


class AnisotropyMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_anisotropy"""

    PROTO = 'AnisotropyMaterialExtension'
    anisotropyStrength = field.newField('anisotropyStrength', 'SFFloat', 1, 0.0,
                                        minimum=0.0, maximum=1.0)
    anisotropyRotation = field.newField('anisotropyRotation', 'SFFloat', 1, 0.0,
                                        unitCategory='angle')
    anisotropyTexture, anisotropyTextureMapping = _texture('anisotropyTexture')


class ClearcoatMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_clearcoat"""

    PROTO = 'ClearcoatMaterialExtension'
    clearcoat = field.newField('clearcoat', 'SFFloat', 1, 0.0, minimum=0.0, maximum=1.0)
    clearcoatTexture, clearcoatTextureMapping = _texture('clearcoatTexture')
    clearcoatRoughness = field.newField('clearcoatRoughness', 'SFFloat', 1, 0.0,
                                        minimum=0.0, maximum=1.0)
    clearcoatRoughnessTexture, clearcoatRoughnessTextureMapping = _texture(
        'clearcoatRoughnessTexture')
    clearcoatNormalTexture, clearcoatNormalTextureMapping = _texture('clearcoatNormalTexture')


class DiffuseTransmissionMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_diffuse_transmission"""

    PROTO = 'DiffuseTransmissionMaterialExtension'
    diffuseTransmission = field.newField('diffuseTransmission', 'SFFloat', 1, 0.0,
                                         minimum=0.0, maximum=1.0)
    diffuseTransmissionTexture, diffuseTransmissionTextureMapping = _texture(
        'diffuseTransmissionTexture')
    diffuseTransmissionColor = field.newField('diffuseTransmissionColor', 'SFColor', 1,
                                              [1.0, 1.0, 1.0], minimum=0.0, maximum=1.0)
    diffuseTransmissionColorTexture, diffuseTransmissionColorTextureMapping = _texture(
        'diffuseTransmissionColorTexture')


class DispersionMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_dispersion"""

    PROTO = 'DispersionMaterialExtension'
    dispersion = field.newField('dispersion', 'SFFloat', 1, 0.0, minimum=0.0)


class EmissiveStrengthMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_emissive_strength"""

    PROTO = 'EmissiveStrengthMaterialExtension'
    emissiveStrength = field.newField('emissiveStrength', 'SFFloat', 1, 1.0, minimum=0.0)


class IORMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_ior"""

    PROTO = 'IORMaterialExtension'
    indexOfRefraction = field.newField('indexOfRefraction', 'SFFloat', 1, 1.5, minimum=1.0)


class IridescenceMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_iridescence; thickness in nanometres"""

    PROTO = 'IridescenceMaterialExtension'
    iridescence = field.newField('iridescence', 'SFFloat', 1, 0.0, minimum=0.0, maximum=1.0)
    iridescenceTexture, iridescenceTextureMapping = _texture('iridescenceTexture')
    iridescenceIndexOfRefraction = field.newField('iridescenceIndexOfRefraction', 'SFFloat', 1,
                                                  1.3, minimum=1.0)
    iridescenceThicknessMinimum = field.newField('iridescenceThicknessMinimum', 'SFFloat', 1,
                                                 100.0, minimum=0.0)
    iridescenceThicknessMaximum = field.newField('iridescenceThicknessMaximum', 'SFFloat', 1,
                                                 400.0, minimum=0.0)
    iridescenceThicknessTexture, iridescenceThicknessTextureMapping = _texture(
        'iridescenceThicknessTexture')


class RetroreflectionMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_retroreflection"""

    PROTO = 'RetroreflectionMaterialExtension'
    retroreflection = field.newField('retroreflection', 'SFFloat', 1, 0.0,
                                     minimum=0.0, maximum=1.0)
    retroreflectionTexture, retroreflectionTextureMapping = _texture('retroreflectionTexture')


class SheenMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_sheen"""

    PROTO = 'SheenMaterialExtension'
    sheenColor = field.newField('sheenColor', 'SFColor', 1, [0.0, 0.0, 0.0],
                                minimum=0.0, maximum=1.0)
    sheenColorTexture, sheenColorTextureMapping = _texture('sheenColorTexture')
    sheenRoughness = field.newField('sheenRoughness', 'SFFloat', 1, 0.0,
                                    minimum=0.0, maximum=1.0)
    sheenRoughnessTexture, sheenRoughnessTextureMapping = _texture('sheenRoughnessTexture')


class SpecularMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_specular

    `specularStrength` scales `specularColor`, which may then exceed 1.
    """

    PROTO = 'SpecularMaterialExtension'
    specular = field.newField('specular', 'SFFloat', 1, 1.0, minimum=0.0, maximum=1.0)
    specularTexture, specularTextureMapping = _texture('specularTexture')
    specularColor = field.newField('specularColor', 'SFColor', 1, [1.0, 1.0, 1.0], minimum=0.0)
    specularStrength = field.newField('specularStrength', 'SFFloat', 1, 1.0, minimum=0.0)
    specularColorTexture, specularColorTextureMapping = _texture('specularColorTexture')


class TransmissionMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_transmission"""

    PROTO = 'TransmissionMaterialExtension'
    transmission = field.newField('transmission', 'SFFloat', 1, 0.0, minimum=0.0, maximum=1.0)
    transmissionTexture, transmissionTextureMapping = _texture('transmissionTexture')


class VolumeMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_volume

    `attenuationDistance` stands in for glTF's infinite default, which X3D
    text has no number for.
    """

    PROTO = 'VolumeMaterialExtension'
    thickness = field.newField('thickness', 'SFFloat', 1, 0.0, minimum=0.0)
    thicknessTexture, thicknessTextureMapping = _texture('thicknessTexture')
    attenuationDistance = field.newField('attenuationDistance', 'SFFloat', 1, 1000000.0)
    attenuationColor = field.newField('attenuationColor', 'SFColor', 1, [1.0, 1.0, 1.0],
                                      minimum=0.0, maximum=1.0)


class VolumeScatterMaterialExtension(X3DMaterialExtensionNode):
    """X_ITE component, level 1: glTF's KHR_materials_volume_scatter"""

    PROTO = 'VolumeScatterMaterialExtension'
    scatterAnisotropy = field.newField('scatterAnisotropy', 'SFFloat', 1, 0.0,
                                       minimum=-1.0, maximum=1.0)
    scatterStrength = field.newField('scatterStrength', 'SFFloat', 1, 0.0,
                                     minimum=0.0, maximum=1.0)
    scatterStrengthTexture, scatterStrengthTextureMapping = _texture('scatterStrengthTexture')
    multiscatterColor = field.newField('multiscatterColor', 'SFColor', 1, [0.0, 0.0, 0.0],
                                       minimum=0.0, maximum=1.0)
    multiscatterColorTexture, multiscatterColorTextureMapping = _texture(
        'multiscatterColorTexture')


#: The material extension nodes, in X_ITE's order.
MATERIAL_EXTENSIONS: "tuple[type, ...]" = (
    AnisotropyMaterialExtension, ClearcoatMaterialExtension,
    DiffuseTransmissionMaterialExtension, DispersionMaterialExtension,
    EmissiveStrengthMaterialExtension, IORMaterialExtension, IridescenceMaterialExtension,
    RetroreflectionMaterialExtension, SheenMaterialExtension, SpecularMaterialExtension,
    TransmissionMaterialExtension, VolumeMaterialExtension, VolumeScatterMaterialExtension,
)


class BlendMode(x3d.X3DAppearanceChildNode):
    """X_ITE component, level 1: how an appearance's fragments blend into the frame

    The factors and equations are OpenGL's names for `glBlendFuncSeparate`
    and `glBlendEquationSeparate`, without the `GL_` prefix.
    """

    PROTO = 'BlendMode'
    COMPONENT = COMPONENT
    CONTAINER_FIELD = 'blendMode'
    SINCE = '3.3'
    blendColor = field.newField('blendColor', 'SFColorRGBA', 1, [0.0, 0.0, 0.0, 0.0],
                                minimum=0.0, maximum=1.0)
    sourceColorFactor = field.newField('sourceColorFactor', 'SFString', 1, 'SRC_ALPHA')
    sourceAlphaFactor = field.newField('sourceAlphaFactor', 'SFString', 1, 'ONE')
    destinationColorFactor = field.newField('destinationColorFactor', 'SFString', 1,
                                            'ONE_MINUS_SRC_ALPHA')
    destinationAlphaFactor = field.newField('destinationAlphaFactor', 'SFString', 1,
                                            'ONE_MINUS_SRC_ALPHA')
    colorEquation = field.newField('colorEquation', 'SFString', 1, 'FUNC_ADD')
    alphaEquation = field.newField('alphaEquation', 'SFString', 1, 'FUNC_ADD')


class DepthMode(x3d.X3DAppearanceChildNode):
    """X_ITE component, level 1: an appearance's depth test, writes, range and offset

    `polygonOffset` is (factor, units) for `glPolygonOffset`; `depthFunction`
    is an OpenGL comparison without the `GL_` prefix, `LESS_EQUAL` for
    `GL_LEQUAL`.
    """

    PROTO = 'DepthMode'
    COMPONENT = COMPONENT
    CONTAINER_FIELD = 'depthMode'
    SINCE = '4.0'
    polygonOffset = field.newField('polygonOffset', 'SFVec2f', 1, [0.0, 0.0])
    depthRange = field.newField('depthRange', 'SFVec2f', 1, [0.0, 1.0], minimum=0.0, maximum=1.0)
    depthTest = field.newField('depthTest', 'SFBool', 1, True)
    depthFunction = field.newField('depthFunction', 'SFString', 1, 'LESS_EQUAL', choices=(
        'NEVER', 'LESS', 'EQUAL', 'LESS_EQUAL', 'GREATER', 'NOT_EQUAL', 'GREATER_EQUAL',
        'ALWAYS'))
    depthMask = field.newField('depthMask', 'SFBool', 1, True)


class InstancedShape(x3d.X3DShapeNode):
    """X_ITE component, level 1: one shape drawn at many places

    Instance i is placed as a Transform with the i-th of each list; a list
    shorter than the longest gives its last entry to the instances past its
    end, and an empty one its Transform field's default.
    """

    PROTO = 'InstancedShape'
    COMPONENT = COMPONENT
    CONTAINER_FIELD = 'children'
    SINCE = '4.0'
    translations = field.newField('translations', 'MFVec3f', 1, list, unitCategory='length')
    rotations = field.newField('rotations', 'MFRotation', 1, list)
    scales = field.newField('scales', 'MFVec3f', 1, list)
    scaleOrientations = field.newField('scaleOrientations', 'MFRotation', 1, list)
    centers = field.newField('centers', 'MFVec3f', 1, list, unitCategory='length')
    pointerEvents = field.newField('pointerEvents', 'SFBool', 1, True)


class SpecularGlossinessMaterial(x3d.X3DOneSidedMaterialNode):
    """X_ITE component, level 1: glTF's KHR_materials_pbrSpecularGlossiness"""

    PROTO = 'SpecularGlossinessMaterial'
    COMPONENT = COMPONENT
    CONTAINER_FIELD = 'material'
    SINCE = '4.0'
    diffuseColor = field.newField('diffuseColor', 'SFColor', 1, [1.0, 1.0, 1.0],
                                  minimum=0.0, maximum=1.0)
    diffuseTexture, diffuseTextureMapping = _texture('diffuseTexture')
    specularColor = field.newField('specularColor', 'SFColor', 1, [1.0, 1.0, 1.0],
                                   minimum=0.0, maximum=1.0)
    glossiness = field.newField('glossiness', 'SFFloat', 1, 1.0, minimum=0.0, maximum=1.0)
    specularGlossinessTexture, specularGlossinessTextureMapping = _texture(
        'specularGlossinessTexture')
    emissiveColor = field.newField('emissiveColor', 'SFColor', 1, [0.0, 0.0, 0.0],
                                   minimum=0.0, maximum=1.0)
    emissiveTexture = field.newField('emissiveTexture', 'SFNode', 1, node.NULL)
    occlusionStrength = field.newField('occlusionStrength', 'SFFloat', 1, 1.0,
                                       minimum=0.0, maximum=1.0)
    occlusionTexture, occlusionTextureMapping = _texture('occlusionTexture')
    normalTexture = field.newField('normalTexture', 'SFNode', 1, node.NULL)
    transparency = field.newField('transparency', 'SFFloat', 1, 0.0, minimum=0.0, maximum=1.0)
    extensions = field.newField('extensions', 'MFNode', 1, list)


class ImageTextureAtlas(x3d.X3DTexture3DNode, x3d.X3DUrlObject):
    """Texturing3D component, level 1 (X_ITE): a 3D texture cut from one 2D image

    The image is `slicesOverX` tiles across and `slicesOverY` down, and the
    first `numberOfSlices` of them, left to right along each row from the
    top row down, are the texture's slices from r=0 up.
    """

    PROTO = 'ImageTextureAtlas'
    COMPONENT = ('Texturing3D', 1)
    CONTAINER_FIELD = 'texture'
    SINCE = '4.0'
    slicesOverX = field.newField('slicesOverX', 'SFInt32', 1, 0, minimum=0)
    slicesOverY = field.newField('slicesOverY', 'SFInt32', 1, 0, minimum=0)
    numberOfSlices = field.newField('numberOfSlices', 'SFInt32', 1, 0, minimum=0)
    colorDepth = field.newEvent('colorDepth', 'SFInt32', 1)
    depth = field.newEvent('depth', 'SFInt32', 1)
    height = field.newEvent('height', 'SFInt32', 1)
    width = field.newEvent('width', 'SFInt32', 1)


class PhysicalMaterial(x3d.PhysicalMaterial):
    """X3D's PhysicalMaterial with X_ITE's `extensions`"""

    PROTO = 'PhysicalMaterial'
    extensions = field.newField('extensions', 'MFNode', 1, list)


class Appearance(x3d.Appearance):
    """X3D's Appearance with X_ITE's `blendMode` and `depthMode`"""

    PROTO = 'Appearance'
    blendMode = field.newField('blendMode', 'SFNode', 1, node.NULL)
    depthMode = field.newField('depthMode', 'SFNode', 1, node.NULL)


#: X_ITE's node types, and X3D's that it adds fields to, by name.
NODES: "dict[str, type]" = {str(cls.__dict__['PROTO']): cls for cls in (
    *MATERIAL_EXTENSIONS, BlendMode, DepthMode, InstancedShape, SpecularGlossinessMaterial,
    ImageTextureAtlas, PhysicalMaterial, Appearance,
)}

#: X3D's node types with X_ITE's laid over them, by name.
VOCABULARY: "dict[str, type]" = {**x3d.CONCRETE_NODES, **NODES}

#: X_ITE's own node types: those X3D has no node of the name for.
OWN_TYPES = frozenset(name for name in NODES if name not in x3d.CONCRETE_NODES)


def _declared(type_name: str) -> Any:
    found: Any = NODES[type_name]
    return found


def component_of(type_name: str) -> "tuple[str, int]":
    """The component and level X_ITE's own node type `type_name` is in"""
    name, level = _declared(type_name).COMPONENT
    return str(name), int(level)


def declaration(type_name: str) -> "type | None":
    """The class declaring the node type `type_name`: X3D's, or X_ITE's for its own"""
    found = x3d.CONCRETE_NODES.get(type_name)
    return found if found is not None else NODES.get(type_name)


def _version(text: str) -> "tuple[int, ...]":
    return tuple(int(part) for part in text.split('.'))


def types_in(version: str) -> "frozenset[str]":
    """X_ITE's own node types a document of X3D `version` may hold

    None in VRML97, and all of them for a dialect naming no version.
    """
    if not version:
        return OWN_TYPES
    if _version(version) < (3, 0):
        return frozenset()
    return frozenset(name for name in OWN_TYPES
                     if _version(_declared(name).SINCE) <= _version(version))


_TEXTURES = (x3d.X3DSingleTextureNode,)
for _cls in NODES.values():
    for _name, _field in vars(_cls).items():
        if isinstance(_field, node.SFNode) and _name.endswith('Texture'):
            _field.requiredTypes = _TEXTURES
PhysicalMaterial.extensions.requiredTypes = (X3DMaterialExtensionNode,)
SpecularGlossinessMaterial.extensions.requiredTypes = (X3DMaterialExtensionNode,)
Appearance.blendMode.requiredTypes = (BlendMode,)
Appearance.depthMode.requiredTypes = (DepthMode,)
