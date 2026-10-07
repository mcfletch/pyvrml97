#!/usr/bin/env python3
"""Generate the X3D declarations from Web3D's X3D Unified Object Model

    tools/generate_x3d.py              write vrml/x3d/nodes.py, nodes.pyi, dialects.py
    tools/generate_x3d.py --check      regenerate into a temporary directory and
                                       compare with the checked-in modules
    tools/generate_x3d.py --report     print the version differences the
                                       dialects cannot record

The X3DUOM files are downloaded from Web3D's public Subversion repository at a
pinned revision, cached in the user's cache directory, and checked against
their SHA-256 digests on every run. Moving to a newer X3DUOM is a change to
`SOURCES` in a reviewed commit, a regeneration, and a reviewed diff.

Anything in the X3DUOM this generator does not know how to map is an error:
an unknown field type, field attribute, base type or node type.
"""

import argparse
import dataclasses
import difflib
import hashlib
import keyword
import os
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ElementTree
from collections.abc import Sequence
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from vrml import field, node  # noqa: E402 the checkout this tool generates for
from vrml import fieldtypes  # noqa: E402, F401 registers the field types newField reads
from vrml.vrml97 import nodetypes  # noqa: E402
from vrml.x3d import behaviours, codecs  # noqa: E402

#: Web3D's x3d Subversion repository revision the X3DUOM files are read at.
REVISION = 40303
URL = ('https://sourceforge.net/p/x3d/code/%d/tree/www.web3d.org/'
       'specifications/X3dUnifiedObjectModel-%s.xml?format=raw')
#: Each X3D version's X3DUOM, by its SHA-256 digest at `REVISION`. 4.1 is the
#: vocabulary; the others are read for the differences the dialects record.
SOURCES = {
    '4.1': 'e11beae36eadcfc5b165a6d0ddd87fe8f2b4288761f765d55de25521c0c902e4',
    '4.0': '51a02e414fee63ec58fd590dbc9d05b2acc3a32aa470241e04b39acdf40067bd',
    '3.3': '6d9561c4398512e9a891e1221667b6a11994c20979aa4bbcabc21cbf056c0eae',
    '3.2': 'e59b0be2157079df805512b4f1beeffec0f804413c8173ae9d1cf8523d36cef2',
    '3.1': '5076304754099d155021ea9d4cabb6b3420fb77a494bdfdb4e91bfe45042fad9',
    '3.0': 'a934b08394e9e40b7e3430a0004d1f46b88b384cfeda8ff959b9fa70913c83a9',
}
VOCABULARY = '4.1'

OUTPUT = os.path.join(ROOT, 'vrml', 'x3d')

#: Attributes of the XML encoding that are not fields: `DEF` is pyvrml97's
#: own, and the rest are statements' or the encoding's.
NOT_FIELDS = frozenset(('DEF', 'USE', 'IS', 'class', 'id', 'style'))

#: The XML statements. Older X3DUOM files list them among the concrete
#: nodes, and a field whose values are statements (a Script's `field`
#: children) is the XML form of a declaration, which the builder reads.
STATEMENTS = frozenset((
    'X3D', 'head', 'Scene', 'meta', 'component', 'unit', 'ROUTE', 'IS',
    'connect', 'field', 'fieldValue', 'ProtoDeclare', 'ProtoInterface',
    'ProtoBody', 'ExternProtoDeclare', 'ProtoInstance', 'IMPORT', 'EXPORT',
))


def is_encoding_attribute(element: Any) -> bool:
    """Whether an X3DUOM field is an attribute of the XML encoding

    `style` is also a field of FontStyle and ScreenFontStyle, where it
    carries the font style choices.
    """
    name = element.get('name')
    if name == 'style' and element.get('simpleType'):
        return False
    return name in NOT_FIELDS


#: Abstract types the X3DUOM lists among the node types that are the
#: interfaces of fields and statements; they declare no node.
NOT_NODE_TYPES = frozenset(('X3DField', 'X3DArrayField', 'X3DStatement'))


#: X3DUOM field types that are not X3D field types, mapped to the one the
#: specification declares for the field.
TYPE_SUBSTITUTES = {'xs:NMTOKEN': 'SFString'}

#: Every attribute an X3DUOM field element may carry. Those that describe
#: prose or the XML Schema (`description`, `baseType`) are read and not used.
FIELD_ATTRIBUTES = frozenset((
    'name', 'type', 'accessType', 'default', 'description', 'inheritedFrom',
    'baseType', 'acceptableNodeTypes', 'minInclusive', 'maxInclusive',
    'minExclusive', 'maxExclusive', 'additionalEnumerationValuesAllowed',
    'simpleType', 'synonym', 'use',
))
FIELD_CHILDREN = frozenset(('enumeration', 'componentInfo'))

#: The pyvrml97 marker type each X3D type also is, so that the engine's
#: existing `isinstance` checks hold for every generated node.
MARKERS = {
    'X3DChildNode': 'Children',
    'X3DGroupingNode': 'Grouping',
    'X3DShapeNode': 'Rendering',
    'X3DGeometryNode': 'Geometry',
    'X3DTextureNode': 'Texture',
    'X3DSensorNode': 'Sensor',
    'X3DPointingDeviceSensorNode': 'PointingSensor',
    'X3DBindableNode': 'Bindable',
    'X3DBackgroundNode': 'Background',
    'X3DViewpointNode': 'Viewpoint',
    'NavigationInfo': 'NavigationInfo',
    'Fog': 'Fog',
    'X3DLightNode': 'Light',
    'X3DInterpolatorNode': 'Interpolator',
    'X3DTimeDependentNode': 'TimeDependent',
    'X3DSoundNode': 'Auditory',
    'Transform': 'Transforming',
    'Billboard': 'Transforming',
    'Inline': 'Traversable',
}

#: Mix-ins from `vrml.x3d.behaviours` a declaration takes as its first bases.
BEHAVIOURS = {
    'Transform': ('LocalMatrices',),
    'X3DBindableNode': ('Bindable',),
}

#: Names fields had before X3D 4.1 that the X3DUOM does not record as a
#: synonym, confirmed against the specifications: VRML97 (ISO/IEC 14772-1)
#: 6.7, 6.25 and 6.45, and X3D 3.3 (ISO/IEC 19775-1:2013) 35.4.1 and 35.4.2.
#: Each becomes an alias on the node.
RENAMES = {
    'Collision': {'collide': 'enabled'},
    'LOD': {'level': 'children'},
    'Switch': {'choice': 'children'},
    'Layer': {'isPickable': 'pickable'},
    'LayoutLayer': {'isPickable': 'pickable'},
}

#: The unit category (ISO/IEC 19775-1, 4.3.6, Tables 4.2 and 4.3) of each
#: field whose value the specification describes as a length, angle, mass,
#: force or a unit derived from them, by the type that declares the field.
#: The X3DUOM does not record units. Every SFRotation and MFRotation field is
#: in the angle category as well; its angle is scaled.
UNIT_CATEGORIES: "dict[str, dict[str, str]]" = {
    'X3DBoundedObject': {'bboxCenter': 'length', 'bboxSize': 'length'},
    'X3DGroupingNode': {'bboxCenter': 'length', 'bboxSize': 'length'},
    'X3DShapeNode': {'bboxCenter': 'length', 'bboxSize': 'length'},
    'Transform': {'translation': 'length', 'center': 'length'},
    'HAnimHumanoid': {'translation': 'length', 'center': 'length'},
    'HAnimJoint': {'translation': 'length', 'center': 'length'},
    'HAnimSite': {'translation': 'length', 'center': 'length'},
    'HAnimSegment': {'centerOfMass': 'length', 'mass': 'mass'},
    'Viewpoint': {'centerOfRotation': 'length', 'position': 'length',
                  'fieldOfView': 'angle'},
    'OrthoViewpoint': {'centerOfRotation': 'length', 'position': 'length',
                       'fieldOfView': 'length'},
    'NavigationInfo': {'avatarSize': 'length', 'visibilityLimit': 'length',
                       'speed': 'speed'},
    'LOD': {'center': 'length', 'range': 'length'},
    'Coordinate': {'point': 'length'},
    'CoordinateDouble': {'point': 'length'},
    'Box': {'size': 'length'},
    'Cone': {'bottomRadius': 'length', 'height': 'length'},
    'Cylinder': {'radius': 'length', 'height': 'length'},
    'Sphere': {'radius': 'length'},
    'ElevationGrid': {'xSpacing': 'length', 'zSpacing': 'length',
                      'height': 'length', 'creaseAngle': 'angle'},
    'Extrusion': {'spine': 'length', 'crossSection': 'length', 'creaseAngle': 'angle'},
    'IndexedFaceSet': {'creaseAngle': 'angle'},
    'Arc2D': {'radius': 'length', 'startAngle': 'angle', 'endAngle': 'angle'},
    'ArcClose2D': {'radius': 'length', 'startAngle': 'angle', 'endAngle': 'angle'},
    'Circle2D': {'radius': 'length'},
    'Disk2D': {'innerRadius': 'length', 'outerRadius': 'length'},
    'Polyline2D': {'lineSegments': 'length'},
    'Polypoint2D': {'point': 'length'},
    'Rectangle2D': {'size': 'length'},
    'TriangleSet2D': {'vertices': 'length'},
    'Text': {'length': 'length', 'maxExtent': 'length'},
    'FontStyle': {'size': 'length'},
    'PointLight': {'location': 'length', 'radius': 'length'},
    'SpotLight': {'location': 'length', 'radius': 'length',
                  'beamWidth': 'angle', 'cutOffAngle': 'angle'},
    'Sound': {'location': 'length', 'minBack': 'length', 'minFront': 'length',
              'maxBack': 'length', 'maxFront': 'length'},
    'X3DFogObject': {'visibilityRange': 'length'},
    'Background': {'skyAngle': 'angle', 'groundAngle': 'angle'},
    'TextureBackground': {'skyAngle': 'angle', 'groundAngle': 'angle'},
    'ProximitySensor': {'center': 'length', 'size': 'length'},
    'VisibilitySensor': {'center': 'length', 'size': 'length'},
    'TransformSensor': {'center': 'length', 'size': 'length'},
    'PlaneSensor': {'offset': 'length', 'minPosition': 'length',
                    'maxPosition': 'length'},
    'CylinderSensor': {'diskAngle': 'angle', 'minAngle': 'angle',
                       'maxAngle': 'angle', 'offset': 'angle'},
    'PositionInterpolator': {'keyValue': 'length'},
    'PositionInterpolator2D': {'keyValue': 'length'},
    'CoordinateInterpolator': {'keyValue': 'length'},
    'CoordinateInterpolator2D': {'keyValue': 'length'},
    'SplinePositionInterpolator': {'keyValue': 'length'},
    'SplinePositionInterpolator2D': {'keyValue': 'length'},
    'TextureTransform': {'rotation': 'angle'},
    'RigidBody': {'mass': 'mass', 'position': 'length', 'centerOfMass': 'length',
                  'linearVelocity': 'speed', 'angularVelocity': 'angular_velocity',
                  'forces': 'force'},
    'RigidBodyCollection': {'gravity': 'acceleration',
                            'contactSurfaceThickness': 'length',
                            'maxCorrectionSpeed': 'speed'},
    'CollisionCollection': {'minBounceSpeed': 'speed', 'surfaceSpeed': 'speed'},
    'Contact': {'minBounceSpeed': 'speed', 'surfaceSpeed': 'speed',
                'position': 'length'},
    'BallJoint': {'anchorPoint': 'length'},
    'DoubleAxisHingeJoint': {'anchorPoint': 'length', 'minAngle1': 'angle',
                             'maxAngle1': 'angle',
                             'desiredAngularVelocity1': 'angular_velocity',
                             'desiredAngularVelocity2': 'angular_velocity'},
    'SingleAxisHingeJoint': {'anchorPoint': 'length', 'minAngle': 'angle',
                             'maxAngle': 'angle'},
    'UniversalJoint': {'anchorPoint': 'length'},
    'SliderJoint': {'minSeparation': 'length', 'maxSeparation': 'length',
                    'sliderForce': 'force'},
    'MotorJoint': {'axis1Angle': 'angle', 'axis2Angle': 'angle', 'axis3Angle': 'angle'},
    'ParticleSystem': {'particleSize': 'length'},
    'X3DParticleEmitterNode': {'speed': 'speed', 'mass': 'mass', 'surfaceArea': 'area'},
    'ConeEmitter': {'position': 'length', 'angle': 'angle'},
    'ExplosionEmitter': {'position': 'length'},
    'PointEmitter': {'position': 'length'},
    'ForcePhysicsModel': {'force': 'force'},
    'WindPhysicsModel': {'speed': 'speed'},
}

#: The unit categories of ISO/IEC 19775-1 Tables 4.2 and 4.3.
UNIT_CATEGORY_NAMES = frozenset((
    'angle', 'force', 'length', 'mass',
    'acceleration', 'angular_velocity', 'area', 'speed', 'volume',
))

#: The attributes of `node.Node` and its prototype machinery a field must not
#: take the name of.
RESERVED = frozenset((
    'copy', 'toString', 'PROTO', 'externalURL', 'rootSceneGraph', 'scenegraph',
    'instantiate', 'renderedChildren', 'COMPONENT', 'CONTAINER_FIELD',
))


class GenerationError(Exception):
    """The X3DUOM says something this generator does not map"""


def cache_directory() -> str:
    """Where downloaded X3DUOM files are kept between runs"""
    base = os.environ.get('XDG_CACHE_HOME') or os.environ.get('LOCALAPPDATA')
    if not base:
        base = os.path.join(os.path.expanduser('~'), '.cache')
    return os.path.join(base, 'pyvrml97', 'x3duom', str(REVISION))


def fetch(version: str) -> bytes:
    """The X3DUOM file for `version`, downloaded once and checked by digest"""
    digest = SOURCES[version]
    path = os.path.join(cache_directory(), 'X3dUnifiedObjectModel-%s.xml' % version)
    if os.path.exists(path):
        with open(path, 'rb') as stream:
            data = stream.read()
        if hashlib.sha256(data).hexdigest() == digest:
            return data
    url = URL % (REVISION, version)
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 URL is the https constant above
        data = response.read()
    found = hashlib.sha256(data).hexdigest()
    if found != digest:
        raise GenerationError(
            'X3DUOM %s from %s has SHA-256 %s, expected %s' % (version, url, found, digest)
        )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    staging = path + '.part'
    with open(staging, 'wb') as stream:
        stream.write(data)
    os.replace(staging, path)
    return data


@dataclasses.dataclass(frozen=True)
class FieldSpec:
    """One field of one X3D type, as the X3DUOM declares it"""

    name: str
    type: str
    access: str
    default: "str | None"
    acceptable: "tuple[str, ...]"
    minimum: "str | None"
    minimumExclusive: bool
    maximum: "str | None"
    maximumExclusive: bool
    choices: "tuple[str, ...]"
    choicesOpen: bool
    synonym: str
    unitCategory: str = ''

    @property
    def is_event(self) -> bool:
        return self.access in ('inputOnly', 'outputOnly')

    def interface(self) -> "tuple[Any, ...]":
        """What a declaration says, for comparing two of them"""
        return (
            self.type, self.access, default_literal(self), self.acceptable,
            self.minimum, self.minimumExclusive, self.maximum,
            self.maximumExclusive, self.choices, self.choicesOpen,
            self.unitCategory,
        )


@dataclasses.dataclass
class TypeSpec:
    """One X3D object type, abstract node type or concrete node"""

    name: str
    kind: str
    bases: "tuple[str, ...]"
    fields: "list[FieldSpec]"
    component: "tuple[str, int]"
    container: str
    url: str


class Model:
    """The types of one X3DUOM file, by name"""

    def __init__(self, data: bytes) -> None:
        root = ElementTree.fromstring(data)
        self.version = root.get('version') or ''
        self.types: "dict[str, TypeSpec]" = {}
        self.field_types: "dict[str, dict[str, str]]" = {}
        section = root.find('FieldTypes')
        if section is not None:
            for element in section:
                self.field_types[element.get('type') or ''] = dict(element.attrib)
        for section_name, kind in (
            ('AbstractObjectTypes', 'object'),
            ('AbstractNodeTypes', 'abstract'),
            ('ConcreteNodes', 'concrete'),
        ):
            section = root.find(section_name)
            if section is None:
                continue
            for element in section:
                if element.get('name') in NOT_NODE_TYPES | STATEMENTS:
                    continue
                spec = self._type(element, kind)
                self.types[spec.name] = spec

    def _type(self, element: Any, kind: str) -> TypeSpec:
        name = element.get('name')
        interface = element.find('InterfaceDefinition')
        bases = tuple(
            item.get('baseType') for item in interface
            if item.tag in ('Inheritance', 'AdditionalInheritance')
        )
        component = interface.find('componentInfo')
        container = interface.find('containerField')
        # A field whose values are statements (a Script's `field` children)
        # is the XML form of a declaration, which the builder reads.
        fields = [
            self._with_unit(name, item, self._field(name, item))
            for item in interface.findall('field')
            if not is_encoding_attribute(item)
            and not set((item.get('acceptableNodeTypes') or '').split('|')) & STATEMENTS
        ]
        return TypeSpec(
            name=name,
            kind=kind,
            bases=bases,
            fields=fields,
            component=(
                (component.get('name'), int(component.get('level')))
                if component is not None else ('', 0)
            ),
            container=container.get('default') if container is not None else '',
            url=interface.get('specificationUrl') or '',
        )

    @staticmethod
    def _with_unit(owner: str, element: Any, spec: FieldSpec) -> FieldSpec:
        """The field with the unit category UNIT_CATEGORIES gives it"""
        declarer = element.get('inheritedFrom') or owner
        category = (UNIT_CATEGORIES.get(owner, {}).get(spec.name)
                    or UNIT_CATEGORIES.get(declarer, {}).get(spec.name))
        if not category and spec.type in ('SFRotation', 'MFRotation'):
            category = 'angle'
        if not category:
            return spec
        return dataclasses.replace(spec, unitCategory=category)

    def _field(self, owner: str, element: Any) -> FieldSpec:
        unknown = set(element.attrib) - FIELD_ATTRIBUTES
        if unknown:
            raise GenerationError('%s.%s has unknown attributes %s'
                                  % (owner, element.get('name'), sorted(unknown)))
        children = {child.tag for child in element} - FIELD_CHILDREN
        if children:
            raise GenerationError('%s.%s has unknown elements %s'
                                  % (owner, element.get('name'), sorted(children)))
        type_name = element.get('type')
        type_name = TYPE_SUBSTITUTES.get(type_name, type_name)
        if type_name not in field.baseFieldTypes:
            raise GenerationError('%s.%s has type %s, which pyvrml97 does not declare'
                                  % (owner, element.get('name'), type_name))
        minimum = element.get('minInclusive')
        minimum_exclusive = element.get('minExclusive')
        maximum = element.get('maxInclusive')
        maximum_exclusive = element.get('maxExclusive')
        default = element.get('default')
        if default is None and not type_name.startswith('MF') and type_name != 'SFNode':
            default = self.field_types[type_name].get('defaultValue', '')
        return FieldSpec(
            name=element.get('name'),
            type=type_name,
            access=element.get('accessType'),
            default=default,
            acceptable=tuple((element.get('acceptableNodeTypes') or '').split('|'))
            if element.get('acceptableNodeTypes') else (),
            minimum=minimum if minimum is not None else minimum_exclusive,
            minimumExclusive=minimum_exclusive is not None,
            maximum=maximum if maximum is not None else maximum_exclusive,
            maximumExclusive=maximum_exclusive is not None,
            choices=enumeration(type_name, element),
            choicesOpen=element.get('additionalEnumerationValuesAllowed', 'true') != 'false',
            synonym=element.get('synonym') or '',
        )


def enumeration(type_name: str, element: Any) -> "tuple[str, ...]":
    """A field's enumerated values

    For an MFString field the X3DUOM lists whole values in their XML text
    form (`"MIDDLE" "BEGIN"`); the choices are the strings they are made of.
    """
    values = [child.get('value') or '' for child in element.findall('enumeration')]
    if type_name != 'MFString':
        return tuple(values)
    strings: "list[str]" = []
    for value in values:
        decoded = codecs.decode('MFString', value) if value.lstrip().startswith('"') else [value]
        strings.extend(item for item in decoded if item not in strings)
    return tuple(strings)


def default_literal(spec: FieldSpec) -> str:
    """The Python literal for a field's default, decoded with the XML codec"""
    if spec.type == 'SFNode':
        if spec.default not in (None, '', 'NULL'):
            raise GenerationError('SFNode %s defaults to %r' % (spec.name, spec.default))
        return 'node.NULL'
    if spec.type == 'MFNode':
        return 'list'
    text = spec.default
    if text is None:
        return 'list'
    value = codecs.decode(spec.type, text)
    if spec.type == 'SFBool':
        return repr(value)
    if spec.type == 'SFInt32':
        return repr(int(value))
    if spec.type in ('SFString',):
        return repr(value)
    if spec.type == 'MFString':
        return repr(value) if value else 'list'
    if spec.type == 'MFBool':
        return repr(value) if value else 'list'
    if spec.type in codecs.SCALAR_FLOAT_TYPES:
        return repr(float(text.strip()))
    if spec.type in codecs.INTEGER_LIST_TYPES:
        return '[%s]' % ', '.join(str(int(item)) for item in value) if len(value) else 'list'
    tokens = text.replace(',', ' ').split()
    if not tokens:
        return 'list'
    return '[%s]' % ', '.join(repr(float(token)) for token in tokens)


def topological(types: "dict[str, TypeSpec]") -> "list[TypeSpec]":
    """Types ordered so that each follows its bases, and by name otherwise"""
    done: "set[str]" = set()
    order: "list[TypeSpec]" = []

    def visit(name: str, path: "tuple[str, ...]") -> None:
        if name in done:
            return
        if name in path:
            raise GenerationError('Inheritance cycle: %s' % ' -> '.join(path + (name,)))
        if name not in types:
            raise GenerationError('%s inherits from %s, which is not declared'
                                  % (path[-1] if path else '?', name))
        for base in types[name].bases:
            visit(base, path + (name,))
        done.add(name)
        order.append(types[name])

    for kind in ('object', 'abstract', 'concrete'):
        for name in sorted(n for n, spec in types.items() if spec.kind == kind):
            visit(name, ())
    return order


class Vocabulary:
    """The classes to generate: bases, own fields and aliases of each type"""

    def __init__(self, model: Model) -> None:
        self.model = model
        self.order = topological(model.types)
        self.bases: "dict[str, tuple[str, ...]]" = {}
        self.declared: "dict[str, list[FieldSpec]]" = {}
        self.aliases: "dict[str, list[tuple[str, str]]]" = {}
        self.classes: "dict[str, type]" = {}
        self.mro: "dict[str, list[str]]" = {}
        for spec in self.order:
            self._plan(spec)
        for type_name, units in UNIT_CATEGORIES.items():
            for field_name, category in units.items():
                found = self.resolve(type_name, field_name) if type_name in self.declared else None
                if found is None:
                    raise GenerationError('UNIT_CATEGORIES names %s.%s, which is not a field'
                                          % (type_name, field_name))
                if category not in UNIT_CATEGORY_NAMES:
                    raise GenerationError('%s.%s has unknown unit category %s'
                                          % (type_name, field_name, category))
        for type_name, renames in RENAMES.items():
            for old, new in renames.items():
                if not self.resolve(type_name, new):
                    raise GenerationError('%s has no field %s to alias as %s'
                                          % (type_name, new, old))
                self.aliases.setdefault(type_name, []).append((old, new))

    def _plan(self, spec: TypeSpec) -> None:
        # The marker comes before the X3D bases, so that `node.Node` follows
        # it, as in the engine's own `(nodetypes.Geometry, node.Node)`
        # classes, and an implementation may mix both in.
        bases = tuple('behaviours.' + mixin for mixin in BEHAVIOURS.get(spec.name, ()))
        if spec.name in MARKERS:
            bases += ('nodetypes.' + MARKERS[spec.name],)
        bases += spec.bases
        if spec.name == 'X3DNode':
            bases += ('node.Node',)
        # A base that is an ancestor of another listed base adds nothing, and
        # Python cannot order it before its descendant (LayoutGroup lists
        # X3DNode beside X3DGroupingNode).
        bases = tuple(
            base for base in bases
            if not any(
                other != base and issubclass(self._python(other), self._python(base))
                for other in bases
            )
        )
        self.bases[spec.name] = bases
        python_bases = tuple(self._python(base) for base in bases) or (object,)
        try:
            cls = type(spec.name, python_bases, {})
        except TypeError as error:
            raise GenerationError('No consistent order for %s%r: %s'
                                  % (spec.name, bases, error)) from error
        self.classes[spec.name] = cls
        self.mro[spec.name] = [
            klass.__name__ for klass in cls.__mro__[1:]
            if self.classes.get(klass.__name__) is klass
        ]
        own = []
        listed = set()
        for item in spec.fields:
            listed.add(item.name)
            self._check_name(spec.name, item.name)
            inherited = self.resolve_from_bases(spec.name, item.name)
            if inherited is None or inherited.interface() != item.interface():
                own.append(item)
            if item.synonym:
                self._check_name(spec.name, item.synonym)
                self.aliases.setdefault(spec.name, []).append((item.synonym, item.name))
        self.declared[spec.name] = sorted(own, key=lambda item: item.name)
        for base in self.mro[spec.name]:
            for item in self.declared[base]:
                if item.name not in listed:
                    raise GenerationError('%s inherits %s from %s, which the X3DUOM '
                                          'does not list for it' % (spec.name, item.name, base))

    def _python(self, base: str) -> type:
        if base.startswith('behaviours.'):
            return getattr(behaviours, base.split('.', 1)[1])
        if base.startswith('nodetypes.'):
            return getattr(nodetypes, base.split('.', 1)[1])
        if base == 'node.Node':
            return node.Node
        return self.classes[base]

    def _check_name(self, owner: str, name: str) -> None:
        if name in RESERVED:
            raise GenerationError('%s.%s takes the name of a node attribute' % (owner, name))

    def resolve_from_bases(self, type_name: str, field_name: str) -> "FieldSpec | None":
        for base in self.mro[type_name]:
            for item in self.declared[base]:
                if item.name == field_name:
                    return item
        return None

    def resolve(self, type_name: str, field_name: str) -> "FieldSpec | None":
        for item in self.declared[type_name]:
            if item.name == field_name:
                return item
        return self.resolve_from_bases(type_name, field_name)

    def all_fields(self, type_name: str) -> "list[FieldSpec]":
        """Every field of the type, own and inherited, by name"""
        found = []
        for item in self.model.types[type_name].fields:
            resolved = self.resolve(type_name, item.name)
            if resolved is not None:
                found.append(resolved)
        return sorted(found, key=lambda item: item.name)

    def required(self, spec: FieldSpec) -> "tuple[str, ...]":
        """The Python types a node field's value must be one of"""
        result: "list[str]" = []
        for name in spec.acceptable:
            if name not in self.model.types:
                raise GenerationError('%s accepts %s, which is not a node type'
                                      % (spec.name, name))
            result.append(name)
            if name in MARKERS and self.model.types[name].kind != 'concrete':
                result.append('nodetypes.' + MARKERS[name])
        return tuple(result)


def description(spec: FieldSpec) -> str:
    """The keyword arguments describing a field beyond its default"""
    items = []
    if spec.minimum is not None:
        items.append('minimum=%r' % float(spec.minimum))
        if spec.minimumExclusive:
            items.append('minimumExclusive=True')
    if spec.maximum is not None:
        items.append('maximum=%r' % float(spec.maximum))
        if spec.maximumExclusive:
            items.append('maximumExclusive=True')
    if spec.choices:
        items.append('choices=%r' % (spec.choices,))
        if not spec.choicesOpen:
            items.append('choicesOpen=False')
    if spec.unitCategory:
        items.append('unitCategory=%r' % spec.unitCategory)
    return ''.join(', ' + item for item in items)


def declaration(spec: FieldSpec) -> str:
    """The expression declaring one field"""
    if spec.access == 'inputOnly':
        return 'field.newEvent(%r, %r, 0)' % (spec.name, spec.type)
    if spec.access == 'outputOnly':
        return 'field.newEvent(%r, %r, 1)' % (spec.name, spec.type)
    exposure = 1 if spec.access == 'inputOutput' else 0
    if spec.access not in ('inputOutput', 'initializeOnly'):
        raise GenerationError('%s has access type %r' % (spec.name, spec.access))
    return 'field.newField(%r, %r, %d, %s%s)' % (
        spec.name, spec.type, exposure, default_literal(spec), description(spec),
    )


HEADER = '''"""The X3D {version} node declarations

Generated by tools/generate_x3d.py from the X3D Unified Object Model {version}
(Web3D x3d repository revision {revision}); regenerate rather than edit.

Each class declares the fields it adds to its bases. Abstract types are the
X3D interface hierarchy, and each also inherits the `vrml.vrml97.nodetypes`
marker the engine checks for. Node fields hold the types the X3DUOM accepts
for them, set in the content model at the foot of the module.
"""
from vrml import field, node
from vrml import fieldtypes  # noqa: F401 registers the field types used below
from vrml.vrml97 import nodetypes
from vrml.x3d import behaviours

#: The X3D version these declarations are of.
X3D_VERSION = {version!r}
'''


def class_lines(vocabulary: Vocabulary, spec: TypeSpec) -> "list[str]":
    bases = vocabulary.bases[spec.name]
    lines = ['', '', 'class %s(%s):' % (spec.name, ', '.join(bases)) if bases
             else 'class %s:' % spec.name]
    if spec.kind == 'object':
        summary = 'X3D object type, %s component' % spec.component[0]
    elif spec.kind == 'abstract':
        summary = 'X3D abstract node type, %s component' % spec.component[0]
    else:
        summary = '%s component, level %d' % spec.component
    lines.append('    """%s' % summary)
    lines.append('')
    lines.append('    %s' % spec.url)
    lines.append('    """')
    lines.append('')
    if spec.kind == 'concrete':
        lines.append('    PROTO = %r' % spec.name)
        lines.append('    COMPONENT = %r' % (spec.component,))
        lines.append('    CONTAINER_FIELD = %r' % spec.container)
    for item in vocabulary.declared[spec.name]:
        if keyword.iskeyword(item.name):
            continue
        lines.append('    %s = %s' % (item.name, declaration(item)))
    for old, new in sorted(vocabulary.aliases.get(spec.name, ())):
        lines.append('    %s = field.AliasField(%r, %r)' % (old, old, new))
    if lines[-1] == '':
        lines.pop()
    for item in vocabulary.declared[spec.name]:
        if keyword.iskeyword(item.name):
            lines.append('')
            lines.append('')
            lines.append('# %r is a Python keyword, so it is set on the class.' % item.name)
            lines.append('setattr(%s, %r, %s)' % (spec.name, item.name, declaration(item)))
    return lines


def generate_nodes(vocabulary: Vocabulary) -> str:
    """The text of vrml/x3d/nodes.py"""
    lines = [HEADER.format(version=VOCABULARY, revision=REVISION).rstrip('\n')]
    for spec in vocabulary.order:
        lines.extend(class_lines(vocabulary, spec))
    lines.append('')
    lines.append('')
    lines.append('# Content model: the node types each node field holds.')
    for spec in vocabulary.order:
        for item in vocabulary.declared[spec.name]:
            if item.type in ('SFNode', 'MFNode') and item.acceptable and not item.is_event:
                required = vocabulary.required(item)
                lines.append('%s.%s.requiredTypes = (%s,)' % (
                    spec.name, item.name, ', '.join(required)))
    lines.append('')
    lines.append('#: Every concrete node class, by its X3D name.')
    lines.append('CONCRETE_NODES = {')
    for spec in vocabulary.order:
        if spec.kind == 'concrete':
            lines.append('    %r: %s,' % (spec.name, spec.name))
    lines.append('}')
    lines.append('')
    lines.append('#: Every field type, as the X3DUOM describes it: values per item,')
    lines.append('#: whether it is a list, default, and the XML encoding\'s lexical form.')
    lines.append('FIELD_TYPES = {')
    for name in sorted(vocabulary.model.field_types):
        attributes = vocabulary.model.field_types[name]
        lines.append('    %r: (%s, %s, %r, %r),' % (
            name, int(attributes['tupleSize']), attributes['isArray'] == 'true',
            attributes.get('defaultValue', ''), attributes.get('regex', ''),
        ))
    lines.append('}')
    return '\n'.join(lines) + '\n'


#: What reading each field type answers, and what setting one accepts, as
#: the stubs declare them.
STUB_TYPES = {
    'SFBool': ('bool', 'bool | int'),
    'SFInt32': ('int', 'int'),
    'SFFloat': ('float', 'float'),
    'SFDouble': ('float', 'float'),
    'SFTime': ('float', 'float'),
    'SFString': ('str', 'str'),
    'MFString': ('list[str]', 'str | Iterable[str]'),
    'SFImage': ('_U32', '_Numbers'),
    'MFImage': ('list[_U32]', 'Iterable[_Numbers] | _Numbers'),
    'MFBool': ('NDArray[np.bool_]', '_Numbers'),
    'MFInt32': ('_I32', '_Numbers'),
}
for _name in codecs.FLOAT32_TYPES:
    STUB_TYPES[_name] = ('_F32', '_Numbers')
for _name in codecs.FLOAT64_TYPES:
    STUB_TYPES[_name] = ('_F64', '_Numbers')

STUB_HEADER = '''"""The X3D {version} node declarations: typed interface

Generated by tools/generate_x3d.py; regenerate rather than edit.
"""
from collections.abc import Iterable, Sequence
from typing import Any, ClassVar, Generic, TypeVar, overload

import numpy as np
from numpy.typing import ArrayLike, NDArray

from vrml import field, node
from vrml.vrml97 import nodetypes
from vrml.x3d import behaviours

_Get = TypeVar('_Get')
_Set = TypeVar('_Set')
_F32 = NDArray[np.float32]
_F64 = NDArray[np.float64]
_I32 = NDArray[np.int32]
_U32 = NDArray[np.uint32]
#: What a numeric field takes: an array, nested sequences, or any iterable
#: of numbers (a `zip` or `map` is drawn out).
_Numbers = ArrayLike | Iterable[Any]

class _Field(field.Field, Generic[_Get, _Set]):
    """A field: reads answer `_Get`, assignment takes `_Set`"""

    @overload
    def __get__(self, client: None, cls: type | None = None) -> _Field[_Get, _Set]: ...
    @overload
    def __get__(self, client: object, cls: type | None = None) -> _Get: ...
    def __set__(self, client: object, value: _Set) -> None: ...

X3D_VERSION: str
CONCRETE_NODES: dict[str, type[X3DNode]]
FIELD_TYPES: dict[str, tuple[int, bool, str, str]]
'''


def stub_types(vocabulary: Vocabulary, spec: FieldSpec) -> "tuple[str, str]":
    """The read and assignment types of a field

    A node field's read is `Any`: it answers the node or NULL, which a
    checker cannot tell apart by truthiness, and code reading one asks for
    the attributes of the concrete node it expects there. Assignment takes
    the types the field holds.
    """
    if spec.type in ('SFNode', 'MFNode'):
        held = ' | '.join(vocabulary.required(spec)) or 'node.Node'
        if spec.type == 'SFNode':
            return ('Any', '%s | None' % held)
        return ('list[Any]', 'Sequence[%s]' % held)
    return STUB_TYPES[spec.type]


def generate_stubs(vocabulary: Vocabulary) -> str:
    """The text of vrml/x3d/nodes.pyi"""
    lines = [STUB_HEADER.format(version=VOCABULARY).rstrip('\n')]
    for spec in vocabulary.order:
        bases = vocabulary.bases[spec.name]
        lines.append('')
        lines.append('class %s(%s):' % (spec.name, ', '.join(bases)) if bases
                     else 'class %s:' % spec.name)
        body = []
        if spec.kind == 'concrete':
            body.append('PROTO: str')
            body.append('COMPONENT: ClassVar[tuple[str, int]]')
            body.append('CONTAINER_FIELD: ClassVar[str]')
        for item in vocabulary.declared[spec.name]:
            if keyword.iskeyword(item.name):
                continue
            get, put = stub_types(vocabulary, item)
            body.append('%s: _Field[%s, %s]' % (item.name, get, put))
        for old, new in sorted(vocabulary.aliases.get(spec.name, ())):
            target = vocabulary.resolve(spec.name, new)
            assert target is not None
            get, put = stub_types(vocabulary, target)
            body.append('%s: _Field[%s, %s]' % (old, get, put))
        if spec.kind != 'object':
            parameters = ['DEF: str = ...']
            for item in vocabulary.all_fields(spec.name):
                if item.is_event or keyword.iskeyword(item.name):
                    continue
                parameters.append('%s: %s = ...' % (item.name, stub_types(vocabulary, item)[1]))
            for owner in [spec.name] + vocabulary.mro[spec.name]:
                for old, new in sorted(vocabulary.aliases.get(owner, ())):
                    target = vocabulary.resolve(spec.name, new)
                    assert target is not None
                    parameters.append('%s: %s = ...' % (old, stub_types(vocabulary, target)[1]))
            # An engine's implementation adds fields of its own to the
            # declaration it implements; Node.__init__ refuses a name the
            # class does not have.
            parameters.append('**fields: Any')
            body.append('def __init__(self, *, %s) -> None: ...' % ', '.join(parameters))
        if not body:
            body.append('...')
        lines.extend('    ' + line for line in body)
    return '\n'.join(lines) + '\n'


@dataclasses.dataclass
class VersionDifference:
    """How one X3D version differs from the vocabulary"""

    version: str
    nodeTypes: "list[str]"
    renames: "list[tuple[str, str, str]]"
    defaults: "list[tuple[str, str, str]]"
    #: (node type, vocabulary field names) the version does not have.
    absent: "list[tuple[str, list[str]]]"
    #: What the dialect cannot record, for the report: fields that left a
    #: node without a confirmed new name, fields whose type changed, and
    #: fields whose access type changed.
    removed: "list[tuple[str, str, str]]"
    retyped: "list[tuple[str, str, str, str]]"
    reaccessed: "list[tuple[str, str, str, str]]"


def alias_target(vocabulary: Vocabulary, type_name: str, name: str) -> "str | None":
    """The vocabulary field an old field name of `type_name` is an alias for"""
    for owner in [type_name] + vocabulary.mro[type_name]:
        for old, new in vocabulary.aliases.get(owner, ()):
            if old == name:
                return new
    return None


def difference(vocabulary: Vocabulary, version: str) -> VersionDifference:
    """Compare one version's X3DUOM with the vocabulary's"""
    old = Model(fetch(version))
    current = vocabulary.model.types
    result = VersionDifference(version, [], [], [], [], [], [], [])
    for name in sorted(old.types):
        spec = old.types[name]
        if spec.kind != 'concrete':
            continue
        if name not in current:
            raise GenerationError('X3D %s node %s is not in the vocabulary' % (version, name))
        result.nodeTypes.append(name)
        then = {item.name: item for item in spec.fields}
        now = {item.name: item for item in current[name].fields}
        renamed_to = set()
        for field_name in sorted(set(then) - set(now)):
            target = alias_target(vocabulary, name, field_name)
            if target is None:
                result.removed.append((name, field_name, then[field_name].type))
            else:
                result.renames.append((name, field_name, target))
                renamed_to.add(target)
        added = sorted(set(now) - set(then) - renamed_to)
        if added:
            result.absent.append((name, added))
        for field_name in sorted(set(then) & set(now)):
            before, after = then[field_name], now[field_name]
            if before.type != after.type:
                result.retyped.append((name, field_name, before.type, after.type))
                continue
            if before.access != after.access:
                result.reaccessed.append((name, field_name, before.access, after.access))
            if before.is_event or after.is_event:
                continue
            if default_literal(before) != default_literal(after):
                result.defaults.append((name, field_name, before.default or ''))
    return result


def generate_dialects(differences: "list[VersionDifference]") -> str:
    """The text of vrml/x3d/dialects.py"""
    lines = [
        '"""The X3D dialects, one per version from 3.0 to %s' % VOCABULARY,
        '',
        'Generated by tools/generate_x3d.py from the X3D Unified Object Model of',
        'each version (Web3D x3d repository revision %d); regenerate rather than' % REVISION,
        'edit. VRML97\'s dialect is written by hand in `vrml.x3d.dialect`.',
        '"""',
        '',
        'from vrml.x3d.dialect import VRML97, AbsentFields, Dialect, FieldDefault, FieldRename',
    ]
    names = []
    for item in differences:
        variable = 'X3D_' + item.version.replace('.', '_')
        names.append((item.version, variable))
        lines.extend(['', '', '%s = Dialect(' % variable])
        lines.append('    name=%r,' % ('X3D ' + item.version))
        lines.append('    version=%r,' % item.version)
        if item.version != VOCABULARY:
            lines.append('    nodeTypes=[')
            row: "list[str]" = []
            for node_type in item.nodeTypes:
                if len(', '.join(row + [repr(node_type)])) > 70:
                    lines.append('        %s,' % ', '.join(row))
                    row = []
                row.append(repr(node_type))
            if row:
                lines.append('        %s,' % ', '.join(row))
            lines.append('    ],')
        if item.renames:
            lines.append('    renamed=[')
            for node_type, old, new in item.renames:
                lines.append('        FieldRename(nodeType=%r, old=%r, current=%r),'
                             % (node_type, old, new))
            lines.append('    ],')
        if item.defaults:
            lines.append('    defaults=[')
            for node_type, field_name, value in item.defaults:
                lines.append('        FieldDefault(nodeType=%r, fieldName=%r, value=%r),'
                             % (node_type, field_name, value))
            lines.append('    ],')
        if item.absent:
            lines.append('    absent=[')
            for node_type, field_names in item.absent:
                lines.extend(_absent_lines(node_type, field_names))
            lines.append('    ],')
        lines.append(')')
    lines.extend(['', '#: Each dialect by the version a document\'s header gives.'])
    lines.append('DIALECTS = {')
    lines.append("    '2.0': VRML97,")
    for version, variable in sorted(names):
        lines.append('    %r: %s,' % (version, variable))
    lines.append('}')
    return '\n'.join(lines) + '\n'


def _absent_lines(node_type: str, names: "list[str]") -> "list[str]":
    """One `AbsentFields` entry, wrapped to the line length"""
    items = ', '.join(repr(name) for name in names)
    single = '        AbsentFields(nodeType=%r, fields=[%s]),' % (node_type, items)
    if len(single) <= 92:
        return [single]
    lines = ['        AbsentFields(nodeType=%r, fields=[' % node_type]
    row: "list[str]" = []
    for name in names:
        if row and len(', '.join(row + [repr(name)])) > 78:
            lines.append('            %s,' % ', '.join(row))
            row = []
        row.append(repr(name))
    lines.append('            %s,' % ', '.join(row))
    lines.append('        ]),')
    return lines


def report(differences: "list[VersionDifference]") -> None:
    """Print what the dialects cannot record, for review"""
    for item in differences:
        print('X3D %s: %d node types, %d renames, %d defaults' % (
            item.version, len(item.nodeTypes), len(item.renames), len(item.defaults)))
        for node_type, field_name, type_name in item.removed:
            print('  no longer a field: %s.%s (%s)' % (node_type, field_name, type_name))
        for node_type, field_name, before, after in item.retyped:
            print('  type changed: %s.%s %s -> %s' % (node_type, field_name, before, after))
        for node_type, field_name, before, after in item.reaccessed:
            print('  access changed: %s.%s %s -> %s' % (node_type, field_name, before, after))


def differences_from(vocabulary: Vocabulary) -> "list[VersionDifference]":
    return [difference(vocabulary, version) for version in sorted(SOURCES)]


def generate(directory: str) -> "dict[str, str]":
    """Write the generated modules into `directory`, answering their paths"""
    vocabulary = Vocabulary(Model(fetch(VOCABULARY)))
    outputs = {
        'nodes.py': generate_nodes(vocabulary),
        'nodes.pyi': generate_stubs(vocabulary),
        'dialects.py': generate_dialects(differences_from(vocabulary)),
    }
    written = {}
    for name, text in outputs.items():
        path = os.path.join(directory, name)
        staging = path + '.part'
        with open(staging, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(staging, path)
        written[name] = path
    return written


def check() -> int:
    """Regenerate into a temporary directory and compare; 0 if identical"""
    differences = 0
    with tempfile.TemporaryDirectory() as directory:
        for name, path in generate(directory).items():
            with open(path, encoding='utf-8') as stream:
                fresh = stream.read().splitlines(keepends=True)
            existing_path = os.path.join(OUTPUT, name)
            try:
                with open(existing_path, encoding='utf-8') as stream:
                    existing = stream.read().splitlines(keepends=True)
            except FileNotFoundError:
                existing = []
            diff = list(difflib.unified_diff(existing, fresh, existing_path, '(generated)'))
            if diff:
                differences += 1
                sys.stdout.writelines(diff[:200])
    return 1 if differences else 0


def main(arguments: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true',
                        help='compare a fresh generation with the checked-in modules')
    parser.add_argument('--report', action='store_true',
                        help='print the version differences the dialects cannot record')
    options = parser.parse_args(arguments)
    if options.check:
        return check()
    if options.report:
        report(differences_from(Vocabulary(Model(fetch(VOCABULARY)))))
        return 0
    for path in generate(OUTPUT).values():
        print(path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
