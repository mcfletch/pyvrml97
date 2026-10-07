"""Dialects: how a VRML or X3D version differs from the X3D 4.1 vocabulary

A document is read into the one vocabulary in `vrml.x3d.nodes`. Its version
is a `Dialect`: the node types that version has, the fields it names
differently (`FieldRename`) and the defaults it gives differently
(`FieldDefault`). A reader renames and sets those defaults as it builds; a
writer renames back, omits values equal to the target's defaults, and
refuses nodes the target lacks.

Dialects are nodes, so they copy, write out and can be extended. The X3D
dialects are generated (`vrml.x3d.dialects`); VRML97's is here.
"""

from collections.abc import Iterable
from typing import Any

from vrml import field, node, protofunctions
from vrml import fieldtypes  # noqa: F401 registers the field types used below
from vrml.x3d import codecs
from vrml.x3d import nodes as x3d


class FieldRename(node.Node):
    """A field a version names differently from the vocabulary"""

    PROTO = 'FieldRename'
    nodeType = field.newField('nodeType', 'SFString', 1, '')
    old = field.newField('old', 'SFString', 1, '')
    current = field.newField('current', 'SFString', 1, '')


class FieldDefault(node.Node):
    """A field a version gives a different default

    `value` is the default as X3D XML attribute text, decoded with the named
    field's own codec, so one node type serves every field type.
    """

    PROTO = 'FieldDefault'
    nodeType = field.newField('nodeType', 'SFString', 1, '')
    fieldName = field.newField('fieldName', 'SFString', 1, '')
    value = field.newField('value', 'SFString', 1, '')

    def decoded(self) -> Any:
        """The default as the field holds it

        Raises KeyError for an unknown node type and AttributeError for a
        field the node type does not have.
        """
        declared = protofunctions.getField(x3d.CONCRETE_NODES[self.nodeType], self.fieldName)
        return declared.coerce(codecs.decode(declared.typeName(), self.value))


class AbsentFields(node.Node):
    """Fields and events of a vocabulary node type that a version lacks"""

    PROTO = 'AbsentFields'
    nodeType = field.newField('nodeType', 'SFString', 1, '')
    fields = field.newField('fields', 'MFString', 1, list)


class Dialect(node.Node):
    """The differences between one VRML or X3D version and the vocabulary

    An empty `nodeTypes` means the version has every node of the vocabulary.
    `absent` names, by their vocabulary names, the fields of the version's
    node types that it does not have.
    """

    PROTO = 'Dialect'
    name = field.newField('name', 'SFString', 1, '')
    version = field.newField('version', 'SFString', 1, '')
    nodeTypes = field.newField('nodeTypes', 'MFString', 1, list)
    renamed = field.newField('renamed', 'MFNode', 1, list, requiredTypes=FieldRename)
    defaults = field.newField('defaults', 'MFNode', 1, list, requiredTypes=FieldDefault)
    absent = field.newField('absent', 'MFNode', 1, list, requiredTypes=AbsentFields)

    def tables(self) -> 'DialectTables':
        """The dialect as lookup tables, for one document's read or write"""
        return DialectTables(self.nodeTypes, self.renamed, self.defaults, self.absent)


class DialectTables:
    """A dialect's renames and defaults by node type, decoded once

    Made for each document read or written, so that a dialect edited
    between documents is seen by the next one.
    """

    def __init__(
        self,
        nodeTypes: Iterable[str],
        renamed: Iterable[FieldRename],
        defaults: Iterable[FieldDefault],
        absent: Iterable[AbsentFields] = (),
    ) -> None:
        self.nodeTypes = frozenset(nodeTypes)
        self.renames = {(item.nodeType, item.old): item.current for item in renamed}
        self.reverse = {(node_type, current): old
                        for (node_type, old), current in self.renames.items()}
        self._defaults: "dict[str, list[tuple[str, Any]]]" = {}
        for item in defaults:
            self._defaults.setdefault(item.nodeType, []).append(
                (item.fieldName, item.decoded())
            )
        self.absent: "dict[str, frozenset[str]]" = {
            item.nodeType: frozenset(item.fields) for item in absent
        }

    def has_node(self, node_type: str) -> bool:
        """Whether the version has the node type"""
        return not self.nodeTypes or node_type in self.nodeTypes

    def has_field(self, node_type: str, name: str) -> bool:
        """Whether the version's node type has the vocabulary's field `name`"""
        return name not in self.absent.get(node_type, ())

    def current_name(self, node_type: str, name: str) -> str:
        """The vocabulary's name for a field the version calls `name`"""
        return self.renames.get((node_type, name), name)

    def dialect_name(self, node_type: str, name: str) -> str:
        """The version's name for the vocabulary's field `name`"""
        return self.reverse.get((node_type, name), name)

    def defaults(self, node_type: str) -> "list[tuple[str, Any]]":
        """(field name, value) for each field the version defaults differently"""
        return self._defaults.get(node_type, [])


#: VRML97, ISO/IEC 14772-1:1997, against X3D 4.1. Clause numbers are those
#: of ISO/IEC 14772-1 section 6, "Node reference".
VRML97 = Dialect(
    name='VRML97',
    version='2.0',
    nodeTypes=[
        'Anchor', 'Appearance', 'AudioClip', 'Background', 'Billboard', 'Box',
        'Collision', 'Color', 'ColorInterpolator', 'Cone', 'Coordinate',
        'CoordinateInterpolator', 'Cylinder', 'CylinderSensor',
        'DirectionalLight', 'ElevationGrid', 'Extrusion', 'Fog', 'FontStyle',
        'Group', 'ImageTexture', 'IndexedFaceSet', 'IndexedLineSet', 'Inline',
        'LOD', 'Material', 'MovieTexture', 'NavigationInfo', 'Normal',
        'NormalInterpolator', 'OrientationInterpolator', 'PixelTexture',
        'PlaneSensor', 'PointLight', 'PointSet', 'PositionInterpolator',
        'ProximitySensor', 'ScalarInterpolator', 'Script', 'Shape', 'Sound',
        'Sphere', 'SphereSensor', 'SpotLight', 'Switch', 'Text',
        'TextureCoordinate', 'TextureTransform', 'TimeSensor', 'TouchSensor',
        'Transform', 'Viewpoint', 'VisibilitySensor', 'WorldInfo',
    ],
    renamed=[
        # 6.7 Collision: exposedField SFBool collide TRUE
        FieldRename(nodeType='Collision', old='collide', current='enabled'),
        # 6.25 LOD: exposedField MFNode level []
        FieldRename(nodeType='LOD', old='level', current='children'),
        # 6.45 Switch: exposedField MFNode choice []
        FieldRename(nodeType='Switch', old='choice', current='children'),
    ],
    defaults=[
        # 6.14 CylinderSensor: exposedField SFFloat diskAngle 0.262
        FieldDefault(nodeType='CylinderSensor', fieldName='diskAngle', value='0.262'),
        # 6.16 DirectionalLight: illuminates only the objects descended from
        # its parent grouping node, which is X3D's global FALSE
        FieldDefault(nodeType='DirectionalLight', fieldName='global', value='FALSE'),
        # 6.28 NavigationInfo: exposedField MFString type ["WALK", "ANY"]
        FieldDefault(nodeType='NavigationInfo', fieldName='type', value='"WALK" "ANY"'),
        # 6.44 SpotLight: exposedField SFFloat beamWidth 1.570796
        FieldDefault(nodeType='SpotLight', fieldName='beamWidth', value='1.570796'),
        # 6.44 SpotLight: exposedField SFFloat cutOffAngle 0.785398
        FieldDefault(nodeType='SpotLight', fieldName='cutOffAngle', value='0.785398'),
    ],
    # The fields of each node's clause in section 6 that X3D 4.1 adds to.
    absent=[
        AbsentFields(nodeType='Anchor', fields=[
            'autoRefresh', 'autoRefreshTimeLimit', 'bboxDisplay', 'load', 'metadata',
            'visible',
        ]),
        AbsentFields(nodeType='Appearance', fields=[
            'acousticProperties', 'alphaCutoff', 'alphaMode', 'backMaterial',
            'fillProperties', 'lineProperties', 'metadata', 'pointProperties', 'shaders',
        ]),
        AbsentFields(nodeType='AudioClip', fields=[
            'autoRefresh', 'autoRefreshTimeLimit', 'elapsedTime', 'enabled', 'gain',
            'isPaused', 'load', 'metadata', 'pauseTime', 'resumeTime',
        ]),
        AbsentFields(nodeType='Background', fields=[
            'bindTime', 'metadata', 'transparency',
        ]),
        AbsentFields(nodeType='Billboard', fields=['bboxDisplay', 'metadata', 'visible']),
        AbsentFields(nodeType='Box', fields=['metadata', 'solid']),
        AbsentFields(nodeType='Collision', fields=[
            'bboxDisplay', 'description', 'isActive', 'metadata', 'visible',
        ]),
        AbsentFields(nodeType='Color', fields=['metadata']),
        AbsentFields(nodeType='ColorInterpolator', fields=['metadata']),
        AbsentFields(nodeType='Cone', fields=['metadata', 'solid']),
        AbsentFields(nodeType='Coordinate', fields=['metadata']),
        AbsentFields(nodeType='CoordinateInterpolator', fields=['metadata']),
        AbsentFields(nodeType='Cylinder', fields=['metadata', 'solid']),
        AbsentFields(nodeType='CylinderSensor', fields=[
            'axisRotation', 'description', 'isOver', 'metadata',
        ]),
        AbsentFields(nodeType='DirectionalLight', fields=[
            'global', 'metadata', 'shadowIntensity', 'shadows',
        ]),
        AbsentFields(nodeType='ElevationGrid', fields=['attrib', 'fogCoord', 'metadata']),
        AbsentFields(nodeType='Extrusion', fields=['metadata']),
        AbsentFields(nodeType='Fog', fields=['bindTime', 'metadata']),
        AbsentFields(nodeType='FontStyle', fields=['metadata']),
        AbsentFields(nodeType='Group', fields=['bboxDisplay', 'metadata', 'visible']),
        AbsentFields(nodeType='ImageTexture', fields=[
            'autoRefresh', 'autoRefreshTimeLimit', 'colorDepth', 'description', 'height',
            'load', 'metadata', 'textureProperties', 'width',
        ]),
        AbsentFields(nodeType='IndexedFaceSet', fields=[
            'attrib', 'fogCoord', 'metadata', 'tangent',
        ]),
        AbsentFields(nodeType='IndexedLineSet', fields=[
            'attrib', 'fogCoord', 'metadata', 'normal',
        ]),
        AbsentFields(nodeType='Inline', fields=[
            'autoRefresh', 'autoRefreshTimeLimit', 'bboxDisplay', 'description', 'global',
            'load', 'metadata', 'visible',
        ]),
        AbsentFields(nodeType='LOD', fields=[
            'addChildren', 'bboxCenter', 'bboxDisplay', 'bboxSize', 'forceTransitions',
            'level_changed', 'metadata', 'removeChildren', 'visible',
        ]),
        AbsentFields(nodeType='Material', fields=[
            'ambientTexture', 'ambientTextureMapping', 'diffuseTexture',
            'diffuseTextureMapping', 'emissiveTexture', 'emissiveTextureMapping',
            'metadata', 'normalScale', 'normalTexture', 'normalTextureMapping',
            'occlusionStrength', 'occlusionTexture', 'occlusionTextureMapping',
            'shininessTexture', 'shininessTextureMapping', 'specularTexture',
            'specularTextureMapping',
        ]),
        AbsentFields(nodeType='MovieTexture', fields=[
            'autoRefresh', 'autoRefreshTimeLimit', 'colorDepth', 'description',
            'elapsedTime', 'enabled', 'gain', 'hasSound', 'height', 'isPaused', 'load',
            'metadata', 'pauseTime', 'pitch', 'resumeTime', 'textureProperties', 'width',
        ]),
        AbsentFields(nodeType='NavigationInfo', fields=[
            'bindTime', 'metadata', 'transitionComplete', 'transitionTime', 'transitionType',
        ]),
        AbsentFields(nodeType='Normal', fields=['metadata']),
        AbsentFields(nodeType='NormalInterpolator', fields=['metadata']),
        AbsentFields(nodeType='OrientationInterpolator', fields=['metadata']),
        AbsentFields(nodeType='PixelTexture', fields=[
            'description', 'metadata', 'textureProperties',
        ]),
        AbsentFields(nodeType='PlaneSensor', fields=[
            'axisRotation', 'description', 'isOver', 'metadata',
        ]),
        AbsentFields(nodeType='PointLight', fields=[
            'global', 'metadata', 'shadowIntensity', 'shadows',
        ]),
        AbsentFields(nodeType='PointSet', fields=[
            'attrib', 'fogCoord', 'metadata', 'normal',
        ]),
        AbsentFields(nodeType='PositionInterpolator', fields=['metadata']),
        AbsentFields(nodeType='ProximitySensor', fields=[
            'centerOfRotation_changed', 'description', 'metadata',
        ]),
        AbsentFields(nodeType='ScalarInterpolator', fields=['metadata']),
        AbsentFields(nodeType='Script', fields=[
            'autoRefresh', 'autoRefreshTimeLimit', 'description', 'load', 'metadata',
            'sourceCode',
        ]),
        AbsentFields(nodeType='Shape', fields=[
            'bboxCenter', 'bboxDisplay', 'bboxSize', 'castShadow', 'metadata', 'visible',
        ]),
        AbsentFields(nodeType='Sound', fields=['description', 'enabled', 'metadata']),
        AbsentFields(nodeType='Sphere', fields=['metadata', 'solid']),
        AbsentFields(nodeType='SphereSensor', fields=['description', 'isOver', 'metadata']),
        AbsentFields(nodeType='SpotLight', fields=[
            'global', 'metadata', 'shadowIntensity', 'shadows',
        ]),
        AbsentFields(nodeType='Switch', fields=[
            'addChildren', 'bboxCenter', 'bboxDisplay', 'bboxSize', 'metadata',
            'removeChildren', 'visible',
        ]),
        AbsentFields(nodeType='Text', fields=[
            'lineBounds', 'metadata', 'origin', 'solid', 'textBounds',
        ]),
        AbsentFields(nodeType='TextureCoordinate', fields=['mapping', 'metadata']),
        AbsentFields(nodeType='TextureTransform', fields=['mapping', 'metadata']),
        AbsentFields(nodeType='TimeSensor', fields=[
            'description', 'elapsedTime', 'isPaused', 'metadata', 'pauseTime', 'resumeTime',
        ]),
        AbsentFields(nodeType='TouchSensor', fields=['description', 'metadata']),
        AbsentFields(nodeType='Transform', fields=['bboxDisplay', 'metadata', 'visible']),
        AbsentFields(nodeType='Viewpoint', fields=[
            'centerOfRotation', 'farDistance', 'metadata', 'navigationInfo', 'nearDistance',
            'retainUserOffsets', 'viewAll',
        ]),
        AbsentFields(nodeType='VisibilitySensor', fields=['description', 'metadata']),
        AbsentFields(nodeType='WorldInfo', fields=['metadata']),
    ],
)


_DECLARED_DEFAULTS: "dict[type, list[tuple[str, Any]]]" = {}


def declared_defaults(cls: type, type_name: str) -> "list[tuple[str, Any]]":
    """(field, X3D default) for each field whose default `cls` gives otherwise

    An engine's class may default a field as suits a node made in code; a
    node a document builds has the X3D declaration's default for a field the
    document leaves out. Node-valued fields are not compared.
    """
    found = _DECLARED_DEFAULTS.get(cls)
    if found is None:
        found = []
        declaration = x3d.CONCRETE_NODES.get(type_name)
        if (declaration is not None and cls is not declaration
                and not issubclass(cls, node.PrototypedNode)):
            for declared in protofunctions.getFields(declaration):
                if declared.name.startswith(' ') or isinstance(declared, (node.SFNode, node.MFNode)):
                    continue
                try:
                    own = protofunctions.getField(cls, declared.name)
                except AttributeError:
                    continue
                if own is declared or not isinstance(own, field.Field):
                    continue
                default = declared.coerce(declared.getDefault())
                if not codecs.same(own.coerce(own.getDefault()), default):
                    found.append((declared.name, default))
        _DECLARED_DEFAULTS[cls] = found
    return found
