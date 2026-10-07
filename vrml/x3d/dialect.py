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


class Dialect(node.Node):
    """The differences between one VRML or X3D version and the vocabulary

    An empty `nodeTypes` means the version has every node of the vocabulary.
    """

    PROTO = 'Dialect'
    name = field.newField('name', 'SFString', 1, '')
    version = field.newField('version', 'SFString', 1, '')
    nodeTypes = field.newField('nodeTypes', 'MFString', 1, list)
    renamed = field.newField('renamed', 'MFNode', 1, list, requiredTypes=FieldRename)
    defaults = field.newField('defaults', 'MFNode', 1, list, requiredTypes=FieldDefault)

    def tables(self) -> 'DialectTables':
        """The dialect as lookup tables, for one document's read or write"""
        return DialectTables(self.nodeTypes, self.renamed, self.defaults)


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

    def has_node(self, node_type: str) -> bool:
        """Whether the version has the node type"""
        return not self.nodeTypes or node_type in self.nodeTypes

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
        # 6.28 NavigationInfo: exposedField MFString type ["WALK", "ANY"]
        FieldDefault(nodeType='NavigationInfo', fieldName='type', value='"WALK" "ANY"'),
        # 6.44 SpotLight: exposedField SFFloat beamWidth 1.570796
        FieldDefault(nodeType='SpotLight', fieldName='beamWidth', value='1.570796'),
        # 6.44 SpotLight: exposedField SFFloat cutOffAngle 0.785398
        FieldDefault(nodeType='SpotLight', fieldName='cutOffAngle', value='0.785398'),
    ],
)
