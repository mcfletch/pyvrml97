"""Base class for the X3D and VRML97 writers

`SceneWriter` holds the target version and walks the scene. For each node it
gives the type name, the DEF or USE name, the fields that differ from the
version's defaults (under the version's field names), the IS connections,
and the fields a Script or shader declares. Each encoding's writer is a
subclass that produces the text.

Node types, fields and field types the target version lacks are collected
as problems, and `write()` raises `X3DWriteError` listing all of them.
"""

from collections.abc import Iterable, Sequence
from typing import Any, NamedTuple

import numpy as np

from vrml import field, node, protofunctions
from vrml.x3d import dialects, extension
from vrml.x3d import codecs
from vrml.x3d.codecs import same
from vrml.x3d import nodes as x3d
from vrml.x3d.builder import XML_NAME, implied_container, scaled, unit_factor

#: The field types VRML97 has (ISO/IEC 14772-1, section 5).
VRML97_TYPES = frozenset((
    'SFBool', 'SFColor', 'SFFloat', 'SFImage', 'SFInt32', 'SFNode', 'SFRotation',
    'SFString', 'SFTime', 'SFVec2f', 'SFVec3f',
    'MFColor', 'MFFloat', 'MFInt32', 'MFNode', 'MFRotation', 'MFString', 'MFTime',
    'MFVec2f', 'MFVec3f',
))

#: VRML97's word for each access type.
VRML97_ACCESS = {
    'initializeOnly': 'field', 'inputOutput': 'exposedField',
    'inputOnly': 'eventIn', 'outputOnly': 'eventOut',
}

#: The url schemes that mark a Script's program written inline.
INLINE_SCHEMES = ('ecmascript:', 'javascript:', 'vrmlscript:')

#: Fields every prototype has that are pyvrml97's, not its interface's.
_PROTOTYPE_FIELDS = frozenset(
    item.name for item in protofunctions.getFields(node.PrototypedNode)
    + protofunctions.getFields(node.PrototypedNode, 1)
)

#: The field types whose values are nodes.
NODE_TYPES = ('SFNode', 'MFNode')


class X3DWriteError(ValueError):
    """Raised when a scene uses something the target version or encoding lacks

    `problems` lists each thing, as a message.
    """

    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__('\n'.join(problems))
        self.problems = list(problems)


class Value(NamedTuple):
    """A field value to write, with the field name used by the target version"""

    name: str
    type_name: str
    value: Any


class Declaration(NamedTuple):
    """A field declared by a prototype interface, a Script or a shader

    `value` is None for an event, and for an EXTERNPROTO's field.
    """

    accessType: str
    type_name: str
    name: str
    value: Any


def target_version(scene: Any, encoding: str, version: "str | None") -> str:
    """The version to write

    `version` if given, else the scene's own. VRML97 ('2.0') exists only in
    the ClassicVRML encoding, so a VRML97 scene written to XML or JSON uses
    the vocabulary's version.
    """
    if version is None:
        version = scene.version or x3d.X3D_VERSION
        if version == '2.0' and encoding != 'classic':
            version = x3d.X3D_VERSION
    if version not in dialects.DIALECTS:
        raise ValueError('No VRML or X3D version %r; known: %s'
                         % (version, ', '.join(sorted(dialects.DIALECTS))))
    if version == '2.0' and encoding != 'classic':
        raise X3DWriteError(['VRML97 has only the ClassicVRML encoding, not %s' % encoding])
    return version


def _inline_program(source: str, type_name: str, vrml97: bool = False) -> str:
    """Script source text as an inline url entry: X3D's ecmascript: scheme, or
    for VRML97 the javascript: of ISO/IEC 14772-1 Annex C"""
    if type_name != 'Script':
        return source
    scheme = 'javascript:' if vrml97 else 'ecmascript:'
    stripped = source.lstrip()
    if stripped.lower().startswith('ecmascript:'):
        return scheme + stripped[len('ecmascript:'):]
    if not stripped.lower().startswith(INLINE_SCHEMES):
        return scheme + source
    return source


def _finite(type_name: str, value: Any) -> bool:
    """Whether every number in a value of `type_name` has a text form"""
    if type_name not in codecs.FLOAT32_TYPES | codecs.FLOAT64_TYPES | codecs.SCALAR_FLOAT_TYPES:
        return True
    try:
        return bool(np.isfinite(np.asarray(value, dtype=np.float64)).all())
    except (TypeError, ValueError):
        return True


class _Scope:
    """DEF names and IS connections for one scene or prototype body"""

    def __init__(self, protos: "list[type]") -> None:
        self.protos = protos
        self.names: "dict[Any, str]" = {}
        self.written: "set[Any]" = set()
        #: For each body node, its fields' IS connections: node field to the
        #: prototype fields it is connected to.
        self.connections: "dict[Any, dict[str, list[str]]]" = {}


class SceneWriter:
    """Base class for writing a scene in one encoding and version

    version -- the VRML or X3D version to write ('2.0' for VRML97, '3.0'
        to '4.1'); the scene's own where not given
    canonical -- the encoding's canonical form, where it has one
    """

    encoding = ''
    #: What a DEF name written in this encoding matches.
    name_pattern = XML_NAME

    def __init__(self, scene: Any, version: "str | None" = None, canonical: bool = False) -> None:
        self.scene = scene
        self.version = target_version(scene, self.encoding, version)
        chosen = dialects.DIALECTS[self.version]
        self.dialect = chosen.tables()
        self.version_name = chosen.name
        self.vrml97 = self.version == '2.0'
        self.canonical = canonical
        self.problems: "list[str]" = []
        self.units = {
            unit.category: unit.conversionFactor for unit in scene.units
        } if self.writes_units else {}
        self._scopes: "list[_Scope]" = []
        self._open: "set[Any]" = set()
        self._equivalents: "dict[Any, Any]" = {}
        self._extension_sets: "dict[Any, Any]" = {}

    @property
    def writes_units(self) -> bool:
        """Whether the version has UNIT statements (X3D 3.3 and later)"""
        major, minor = (int(part) for part in self.version.split('.'))
        return (major, minor) >= (3, 3)

    @property
    def profile(self) -> str:
        return str(self.scene.profile or 'Full')

    def write(self) -> str:
        """The scene as text; raises X3DWriteError if the version cannot hold it"""
        try:
            text = self.document()
        except RecursionError:
            self.problem('the nodes are nested too deeply to write')
            raise X3DWriteError(self.problems) from None
        if self.problems:
            raise X3DWriteError(self.problems)
        return text

    def document(self) -> str:
        raise NotImplementedError

    def problem(self, message: str) -> None:
        if message not in self.problems:
            self.problems.append(message)

    # Scopes

    def enter(self, graph: Any, extra: Iterable[type] = ()) -> _Scope:
        """Start a scene or prototype body, assigning DEF names and listing prototypes

        extra -- prototype classes this scope declares beyond the graph's own
        """
        visible = {id(proto) for scope in self._scopes for proto in scope.protos}
        protos: "list[type]" = []
        for proto in list(extra) + list(graph.protoTypes.values()):
            if id(proto) not in {id(item) for item in protos}:
                protos.append(proto)
        scope = _Scope(protos)
        counts: "dict[Any, int]" = {}
        order: "list[Any]" = []
        undeclared: "list[type]" = []
        known = visible | {id(proto) for proto in protos}
        roots = list(graph.children)
        for proto in protos:
            roots.extend(self._default_nodes(proto))
        self._count(roots, counts, order, undeclared, known)
        if not self._scopes:
            for proto in undeclared:
                if id(proto) not in {id(item) for item in protos}:
                    protos.insert(0, proto)
        routed = set()
        for each in graph.routes:
            routed.add(each.source)
            routed.add(each.destination)
        # The names a node is given come first, then the names the scene's
        # imports, exports and waiting routes use, and only then those made
        # up for shared and routed nodes, so a made-up name never takes one
        # of the others.
        taken: "set[str]" = set()
        given = [target for target in order if protofunctions.defName(target)]
        for target in given:
            name = protofunctions.defName(target)
            if not self.name_pattern.match(name):
                self.problem('DEF name %r cannot be written in the %s encoding'
                             % (name, self.encoding))
            self._name(scope, target, name, taken)
        taken.update(self._names_used(graph))
        for target in order:
            if target not in scope.names and (counts[target] > 1 or target in routed):
                self._name(scope, target, protofunctions.protoName(target), taken)
        self._scopes.append(scope)
        return scope

    @staticmethod
    def _name(scope: _Scope, target: Any, wanted: str, taken: "set[str]") -> None:
        """Name `target` `wanted`, or `wanted` numbered where that is taken"""
        name, number = wanted, 1
        while name in taken:
            number += 1
            name = '%s_%d' % (wanted, number)
        taken.add(name)
        scope.names[target] = name

    @staticmethod
    def _names_used(graph: Any) -> "set[str]":
        """The DEF names `graph`'s IMPORT, EXPORT and waiting ROUTE statements use"""
        used = {str(item.localDEF) for item in getattr(graph, 'imports', ())}
        used.update(str(item.localDEF) for item in getattr(graph, 'exports', ()))
        for waiting in getattr(graph, 'pendingRoutes', ()):
            used.update((str(waiting.fromNode), str(waiting.toNode)))
        return used

    def leave(self) -> None:
        self._scopes.pop()

    def _count(
        self, roots: Iterable[Any], counts: "dict[Any, int]", order: "list[Any]",
        undeclared: "list[type]", known: "set[int]",
    ) -> None:
        """Count references to each node in one scope, excluding prototype bodies"""
        stack = list(reversed(list(roots)))
        while stack:
            current = stack.pop()
            if not current or not isinstance(current, node.Node):
                continue
            current = self.written_as(current)
            if current in counts:
                counts[current] += 1
                continue
            counts[current] = 1
            order.append(current)
            cls = type(current)
            if isinstance(current, node.PrototypedNode) and id(cls) not in known:
                known.add(id(cls))
                undeclared.append(cls)
            inner = []
            for declared in protofunctions.getFields(current):
                if declared.name.startswith(' '):
                    continue
                if isinstance(declared, node.MFNode):
                    inner.extend(declared.fget(current))
                elif isinstance(declared, node.SFNode) and getattr(declared, 'adopts', True):
                    inner.append(declared.fget(current))
            stack.extend(reversed(inner))

    def _default_nodes(self, proto: type) -> "list[Any]":
        found: "list[Any]" = []
        if protofunctions.getExternalURL(proto):
            return found
        for declared in self.interface_fields(proto):
            if isinstance(declared, node.MFNode):
                found.extend(declared.getDefault())
            elif isinstance(declared, node.SFNode):
                found.append(declared.getDefault())
        return found

    # Nodes

    def written_as(self, target: Any) -> Any:
        """The node written for `target`: its `x3dEquivalent()`, made once, or itself"""
        make = getattr(target, 'x3dEquivalent', None)
        if not callable(make):
            return target
        found = self._equivalents.get(target)
        if found is None:
            found = self._equivalents[target] = make()
        return found

    def type_of(self, target: Any) -> "tuple[str, bool]":
        """A node's type name, and whether it is a prototype instance"""
        type_name = str(protofunctions.protoName(target))
        if isinstance(target, node.PrototypedNode):
            return type_name, True
        if not self.dialect.has_node(type_name):
            self.problem('%s has no node %s' % (self.version_name, type_name))
        return type_name, False

    def reference(self, target: Any) -> "tuple[str, bool]":
        """(name, is_use) for a node; ('', False) for an unnamed node

        The first call for a node gives its DEF name; later calls give a USE.
        A node that contains itself is recorded as a problem and written as
        a USE.
        """
        scope = self._scopes[-1]
        name = scope.names.get(target, '')
        if target in scope.written:
            if not name:
                self.problem('%s is written twice with no name'
                             % protofunctions.protoName(target))
            return name, True
        if target in self._open:
            self.problem('%s contains itself' % protofunctions.protoName(target))
            return name, True
        scope.written.add(target)
        return name, False

    def opened(self, target: Any) -> None:
        self._open.add(target)

    def closed(self, target: Any) -> None:
        self._open.discard(target)

    def connections(self, target: Any) -> "list[tuple[str, str]]":
        """(node field, prototype field) for each IS connection of a body node"""
        found = self._scopes[-1].connections.get(target, {})
        type_name = protofunctions.protoName(target)
        prototype = isinstance(target, node.PrototypedNode)
        return sorted(
            (name if prototype else self.dialect.dialect_name(type_name, name), protoField)
            for name, protoFields in found.items() for protoField in protoFields
        )

    def _default(self, declared: Any, type_name: str, defaults: "dict[str, Any]") -> Any:
        """A field's default for `type_name` in the target version, coerced;
        worked out once for each field and node type in a write"""
        memo: "dict[tuple[Any, str], Any]" = self.__dict__.setdefault('_defaults', {})
        key = (declared, type_name)
        if key not in memo:
            default = defaults[declared.name] if declared.name in defaults else declared.getDefault()
            try:
                default = declared.coerce(default)
            except (TypeError, ValueError):
                pass
            memo[key] = default
        return memo[key]

    def _inherited(self, cls: type) -> "set[str]":
        """The field and event names a class has from the declaration it extends"""
        memo: "dict[type, set[str]]" = self.__dict__.setdefault('_inherited_names', {})
        if cls not in memo:
            base = next(item for item in cls.__mro__ if not item.__dict__.get(' declares', False))
            memo[cls] = {item.name for item in protofunctions.getFields(base)
                         + protofunctions.getFields(base, 1)}
        return memo[cls]

    def own_declarations(self, target: Any) -> "list[Declaration]":
        """Fields a Script or shader node declares, with their current values"""
        cls = type(target)
        inherited = self._inherited(cls)
        found = []
        connected = self._scopes[-1].connections.get(target, {}) if self._scopes else {}
        for declared in protofunctions.getFields(cls) + protofunctions.getFields(cls, 1):
            if declared.name in inherited or declared.name.startswith(' '):
                continue
            value = None
            if isinstance(declared, field.Field) and declared.name not in connected:
                value = declared.fget(target)
                if declared.typeName() not in NODE_TYPES:
                    value = self.scaled_out(declared, value)
            found.append(self.declaration(declared, value))
        return sorted(found, key=lambda item: item.name)

    def own_names(self, target: Any) -> "set[str]":
        cls = type(target)
        if not cls.__dict__.get(' declares', False):
            return set()
        return {item.name for item in self.own_declarations(target)}

    def declaration(self, declared: Any, value: Any) -> Declaration:
        type_name = str(declared.typeName())
        if self.vrml97 and type_name not in VRML97_TYPES:
            self.problem('VRML97 has no field type %s (%s)' % (type_name, declared.name))
        return Declaration(declared.accessType, type_name, declared.name, value)

    def access_word(self, accessType: str) -> str:
        """The access type keyword for the target version"""
        return VRML97_ACCESS[accessType] if self.vrml97 else accessType

    def values(self, target: Any, source: str = 'separate') -> "list[Value]":
        """Non-node fields whose values differ from the version's defaults

        source -- where a program's `sourceCode` goes: 'separate' leaves it
            out for the encoding to write itself, 'field' writes it as a
            field, 'url' puts it first in the `url` field
        """
        return self._split(target, source)[0]

    def node_fields(self, target: Any) -> "list[Value]":
        """Node-valued fields that are not empty, named as the version names them"""
        return self._split(target, None)[1]

    def _split(self, target: Any, source: "str | None") -> "tuple[list[Value], list[Value]]":
        """`target`'s fields to write, values apart from nodes; the last node's
        are kept, since an encoding asks for both one after the other (`source`
        None takes either, for the node fields it does not change)"""
        last = self.__dict__.get('_last_split')
        if last is not None and last[0] is target and (source is None or last[1] == source):
            found: "tuple[list[Value], list[Value]]" = last[2]
            return found
        written = self._fields(target, source or 'separate')
        found = ([item for item in written if item.type_name not in NODE_TYPES],
                 [item for item in written if item.type_name in NODE_TYPES])
        self.__dict__['_last_split'] = (target, source or 'separate', found)
        return found

    def source(self, target: Any) -> str:
        """Inline program text of a Script or shader node, or ''"""
        declared = getattr(type(target), 'sourceCode', None)
        if not isinstance(declared, field.Field):
            return ''
        return str(declared.fget(target) or '')

    def _fields(self, target: Any, source: str) -> "list[Value]":
        type_name = protofunctions.protoName(target)
        prototype = isinstance(target, node.PrototypedNode)
        connected = self._scopes[-1].connections.get(target, {})
        own = self.own_names(target)
        defaults = dict(self.dialect.defaults(type_name)) if not prototype else {}
        known = extension.vocabulary_fields(type_name) if not prototype else frozenset()
        carries = getattr(type(target), 'x3dExtension', None)
        added: "list[tuple[Any, Any]]" = []
        program = self.source(target)
        result = []
        for declared in protofunctions.getFields(target):
            name = declared.name
            if name.startswith(' ') or name in own or name in connected:
                continue
            if name in _PROTOTYPE_FIELDS:
                if prototype or name == 'externalURL':
                    continue
            value = declared.fget(target)
            type_name_of = str(declared.typeName())
            if name == 'sourceCode' and not prototype:
                if source != 'field' or not value:
                    continue
            elif name == 'url' and source == 'url' and program and not prototype:
                value = [_inline_program(program, type_name, self.vrml97)] + list(value)
            elif isinstance(declared, node.MFNode):
                if not len(value):
                    continue
                value = [self.written_as(child) for child in value]
            elif isinstance(declared, node.SFNode):
                if not value:
                    continue
                value = self.written_as(value)
            else:
                default = self._default(declared, type_name, defaults)
                if same(value, default):
                    continue
                if not _finite(type_name_of, value):
                    self.problem('%s.%s holds %r, which X3D has no text for'
                                 % (type_name, name, value))
                    continue
                value = self.scaled_out(declared, value)
            if not prototype and name not in known:
                if carries:
                    added.append((declared, declared.fget(target)))
                else:
                    self.problem('%s is not a field of X3D\'s %s, and %s names no '
                                 'x3dExtension to carry it'
                                 % (name, type_name, type(target).__name__))
                continue
            if not prototype and not self.dialect.has_field(type_name, name):
                self.problem('%s has no field %s.%s' % (self.version_name, type_name, name))
                continue
            written = name if prototype else self.dialect.dialect_name(type_name, name)
            result.append(Value(written, type_name_of, value))
        if added:
            result = [item for item in result if item.name != 'metadata']
            if not self.dialect.has_field(type_name, 'metadata'):
                self.problem('%s has no metadata to carry %s' % (self.version_name, ', '.join(
                    declared.name for declared, _value in added)))
            else:
                found = self._extension_sets.get(target)
                if found is None:
                    found = self._extension_sets[target] = extension.extension_set(
                        target, added, self.written_as)
                result.append(Value('metadata', 'SFNode', found))
        return sorted(result, key=lambda item: item.name)

    def scaled_out(self, declared: Any, value: Any) -> Any:
        """Convert a value from base units to the document's declared units"""
        category = getattr(declared, 'unitCategory', None)
        if not self.units or not category:
            return value
        return scaled(declared, value, 1.0 / unit_factor(category, self.units))

    # Prototypes

    def interface_fields(self, proto: type) -> "list[Any]":
        """Fields and events declared by a prototype"""
        found = [item for item in protofunctions.getFields(proto) + protofunctions.getFields(proto, 1)
                 if item.name not in _PROTOTYPE_FIELDS and not item.name.startswith(' ')]
        return sorted(found, key=lambda item: item.name)

    def interface(self, proto: type) -> "list[Declaration]":
        """Interface declarations of a prototype, with defaults unless it is external"""
        external = bool(protofunctions.getExternalURL(proto))
        found = []
        for declared in self.interface_fields(proto):
            value = None
            if isinstance(declared, field.Field) and not external:
                value = declared.getDefault()
            found.append(self.declaration(declared, value))
        return found

    def external_urls(self, proto: type) -> "list[str]":
        return list(protofunctions.getExternalURL(proto) or [])

    def body(self, proto: type) -> Any:
        """Start a prototype body; returns its scene graph, or None if it has none"""
        graph = protofunctions.getSceneGraph(proto)
        if not graph:
            return None
        scope = self.enter(graph)
        for protoField, targets in node.ismaps(proto).items():
            for target, nodeField in targets:
                scope.connections.setdefault(target, {}).setdefault(nodeField, []).append(
                    protoField)
        return graph

    # Routes and statements

    def routes(self, graph: Any) -> "list[tuple[str, str, str, str]]":
        """(from node, from field, to node, to field) for each route"""
        names = self._scopes[-1].names
        found = []
        for each in graph.routes:
            ends = []
            for target, name in ((each.source, each.sourceField),
                                 (each.destination, each.destinationField)):
                target = self.written_as(target)
                if target not in names:
                    self.problem('ROUTE names a %s that is not in the scene'
                                 % protofunctions.protoName(target))
                ends.extend([names.get(target, ''), self.event_name(target, name)])
            found.append((ends[0], ends[1], ends[2], ends[3]))
        if graph is self.scene:
            for record in getattr(graph, 'pendingRoutes', ()):
                found.append((record.fromNode, record.fromField, record.toNode, record.toField))
        return found

    def event_name(self, target: Any, name: str) -> str:
        """A node's field or event name as the target version spells it"""
        if isinstance(target, node.PrototypedNode):
            return name
        type_name = protofunctions.protoName(target)
        bare = name
        for prefix, suffix in (('set_', ''), ('', '_changed')):
            if name.startswith(prefix) and name.endswith(suffix) and (prefix or suffix):
                candidate = name[len(prefix):len(name) - len(suffix)]
                if candidate in {item.name for item in protofunctions.getFields(target)}:
                    bare = candidate
                    renamed = self.dialect.dialect_name(type_name, candidate)
                    if not self.dialect.has_field(type_name, candidate):
                        self.problem('%s has no field %s.%s'
                                     % (self.version_name, type_name, candidate))
                    return prefix + renamed + suffix
        if not self.dialect.has_field(type_name, bare):
            self.problem('%s has no field %s.%s' % (self.version_name, type_name, bare))
        return self.dialect.dialect_name(type_name, bare)

    def imports(self) -> "list[tuple[str, str, str]]":
        """(inline DEF, imported DEF, AS or '') for each IMPORT"""
        if self.scene.imports and self.vrml97:
            self.problem('VRML97 has no IMPORT statement')
        return [(item.inlineDEF, item.importedDEF,
                 item.localDEF if item.localDEF != item.importedDEF else '')
                for item in self.scene.imports]

    def exports(self) -> "list[tuple[str, str]]":
        """(local DEF, AS or '') for each EXPORT"""
        if self.scene.exports and self.vrml97:
            self.problem('VRML97 has no EXPORT statement')
        return [(item.localDEF, item.AS if item.AS != item.localDEF else '')
                for item in self.scene.exports]

    def implied_container(self, parent: Any, child: Any, name: str) -> bool:
        """True if a reader would place `child` in `parent`'s field `name` without a containerField

        A ProtoInstance is held to X3D's default of `children` as well as to
        the field its first node's type implies.
        """
        if isinstance(child, node.PrototypedNode) and name != 'children':
            return False
        return implied_container(parent, child, self.dialect) == name
