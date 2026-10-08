"""SceneBuilder: the one place an X3D document becomes a scene

Every encoding's reader turns its syntax into calls on a `SceneBuilder`;
the builder owns everything the encodings share: node construction and
where each node goes, `DEF`/`USE` and their scopes, prototypes and `IS`,
routes, `IMPORT`/`EXPORT`, the document's units and dialect, and the
problems found on the way. A reader passes names and text; the builder
resolves the names to node classes and fields and decodes the text by the
field's type.

A reader sets `line` and `column` before each call it can place, and each
problem is recorded at that position. Problems are `LoadProblem` nodes on
the scene's `problems` field; in strict mode the first error raises
`X3DLoadError` instead.
"""

import math
import weakref
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from vrml import field, node, protofunctions, route
from vrml.vrml97.scenegraph import SceneGraph
from vrml.x3d import codecs, dialect, dialects, extension, profiles, runtime
from vrml.x3d import nodes as x3d
from vrml.x3d.dialect import DialectTables
from vrml.x3d.scene import (
    ComponentInfo, ExportInfo, ImportInfo, LoadProblem, MetaInfo, RouteInfo,
    UnitInfo, X3DScene,
)

#: The unit categories a `unit` statement names, and the derived categories
#: a field may be in, as powers of the base categories (ISO/IEC 19775-1,
#: 4.3.6, Tables 4.2 and 4.3). Time is always seconds.
DERIVED_UNITS: "dict[str, dict[str, int]]" = {
    'angle': {'angle': 1},
    'force': {'force': 1},
    'length': {'length': 1},
    'mass': {'mass': 1},
    'acceleration': {'length': 1},
    'angular_velocity': {'angle': 1},
    'area': {'length': 2},
    'speed': {'length': 1},
    'volume': {'length': 3},
}

#: Node types whose instances may declare their own fields, as `field`
#: statements in XML and as declarations in ClassicVRML.
DECLARES_FIELDS = (x3d.X3DScriptNode, x3d.X3DProgrammableShaderObject)


#: A prototype's class.
ProtoClass = type[node.PrototypedNode]

#: The attributes of a node's element that can be the encoding's, not the node's.
ENCODING_ATTRIBUTES = frozenset(('DEF', 'USE', 'containerField', 'class', 'id', 'style'))

#: A field declaration given no value.
_UNSET: Any = object()


def unit_factor(category: str, units: "Mapping[str, float]") -> float:
    """What a value of a field in unit `category` is multiplied by

    units -- each base category's conversion factor, as `unit` statements give
    """
    factor = 1.0
    for base, power in DERIVED_UNITS[category].items():
        factor *= units.get(base, 1.0) ** power
    return factor


def scaled(declared: Any, value: Any, factor: float) -> Any:
    """`value` of the field `declared`, multiplied by `factor`

    A rotation's angle is scaled and its axis is not.
    """
    if factor == 1.0:
        return value
    value = declared.coerce(value)
    if declared.typeName() in ('SFRotation', 'MFRotation'):
        value = value.copy()
        value[..., 3] *= factor
        return value
    return value * factor


class X3DLoadError(ValueError):
    """A document has an error, raised in strict mode"""

    def __init__(self, problem: LoadProblem) -> None:
        super().__init__(str(problem))
        self.problem = problem


class _Scope:
    """The DEF names and prototypes of a document or a prototype body"""

    def __init__(self, parent: "_Scope | None") -> None:
        self.parent = parent
        self.defs: "dict[str, Any]" = {}
        self.protos: "dict[str, type]" = {}
        #: Local names an IMPORT statement promises, bound when the Inline
        #: that exports them has loaded.
        self.imports: "set[str]" = set()

    def proto(self, name: str) -> "type | None":
        scope: "_Scope | None" = self
        while scope is not None:
            found = scope.protos.get(name)
            if found is not None:
                return found
            scope = scope.parent
        return None


class _Frame:
    """A node being built: the values for its node fields, gathered until it ends"""

    def __init__(self, built: Any, type_name: str, notify: bool) -> None:
        self.node = built
        self.type_name = type_name
        self.notify = notify
        self.children: "dict[str, list[Any]]" = {}
        self.set_fields: "set[str]" = set()
        #: The field nodes go into while a reader names one (`start_field`).
        self.target: "list[str]" = []
        self.used = False
        self.skip = False


class _ProtoDefinition:
    """A `ProtoDeclare`/`PROTO` or `ExternProtoDeclare`/`EXTERNPROTO` in progress"""

    def __init__(self, name: str, extern: bool, scope: _Scope) -> None:
        self.name = name
        self.extern = extern
        self.scope = scope
        self.fields: "list[Any]" = []
        self.urls: "list[str]" = []
        #: (prototype field, body node, node field) for each IS connection.
        self.connections: "list[tuple[str, Any, str]]" = []
        self.body: "_Body | None" = None
        #: The nodes open where the prototype is declared, put back when its body ends.
        self.outside: "list[_Frame]" = []


class _Body:
    """The root nodes and routes of a document or a prototype body"""

    def __init__(self, scope: _Scope) -> None:
        self.scope = scope
        self.roots: "list[Any]" = []
        self.routes: "list[Any]" = []


#: Resolves an EXTERNPROTO's URLs against the document's base URI to the
#: prototype class they name, or None where none of them can be read.
ExternResolver = Callable[[Sequence[str], str, str], 'type | None']


#: What a document is built from when no prototypes are given.
DEFAULT_VOCABULARY: "Mapping[str, type]" = {**x3d.CONCRETE_NODES, **runtime.PROTOTYPES}


class SceneBuilder:
    """Builds an `X3DScene` from the calls a reader makes

    prototypes -- node classes by X3D name, laid over the declarations in
        `vrml.x3d.nodes` with `vrml.x3d.runtime`'s behaviours. An engine
        passes its implementations here, and its `X3DScene` subclass under
        'X3DScene' for the scene itself; each node type it does not supply
        and the runtime gives no behaviour is reported once, as an `info`
        problem.
    baseURI -- where the document is, for resolving relative URLs
    strict -- raise `X3DLoadError` at the first error rather than recording
        it and carrying on
    extern_resolver -- called with an EXTERNPROTO's URLs, the base URI and
        the prototype's name; answers the defining prototype class or None
    """

    def __init__(
        self,
        prototypes: "Mapping[str, type] | None" = None,
        baseURI: str = '',
        strict: bool = False,
        extern_resolver: "ExternResolver | None" = None,
    ) -> None:
        self.vocabulary: "Mapping[str, type]" = (
            {**DEFAULT_VOCABULARY, **prototypes} if prototypes else DEFAULT_VOCABULARY)
        #: Whether an engine gave its own classes, so a type built from its
        #: bare declaration is one the engine does not implement.
        self._engine = bool(prototypes)
        self.strict = strict
        self.extern_resolver = extern_resolver
        self.line = 0
        self.column = 0
        #: Where the reader is in a document with no lines (JSON's members).
        self.path = ''
        scene_class = self.vocabulary.get('X3DScene', X3DScene)
        if not (isinstance(scene_class, type) and issubclass(scene_class, X3DScene)):
            scene_class = X3DScene
        self.scene = scene_class(baseURI=baseURI)
        self.dialect: DialectTables = dialects.DIALECTS[x3d.X3D_VERSION].tables()
        #: The name of the document's version, for messages: 'VRML97', 'X3D 3.3'.
        self.version_name = dialects.DIALECTS[x3d.X3D_VERSION].name
        self._units: "dict[str, float]" = {}
        self._scope = _Scope(None)
        self._body = _Body(self._scope)
        self._bodies: "list[_Body]" = [self._body]
        self._frames: "list[_Frame]" = []
        self._protos: "list[_ProtoDefinition]" = []
        #: Each prototype field whose default holds nodes, while it is read:
        #: (prototype, field, nodes, the number of nodes open where it began).
        self._proto_field: "list[tuple[_ProtoDefinition, Any, list[Any], int]]" = []
        self._problems: "list[LoadProblem]" = []
        self._scripts = 0
        self._unknown_types: "set[str]" = set()

    # Problems

    def problem(self, severity: str, message: str, subject: Any = None) -> None:
        """Record a problem at the reader's current position"""
        record = LoadProblem(
            severity=severity, line=self.line, column=self.column, message=message,
            path=self.path,
        )
        if subject is not None:
            record.node = subject
        if self.strict and severity == 'error':
            raise X3DLoadError(record)
        self._problems.append(record)

    # Document statements

    def document(self, profile: str = '', version: str = '') -> None:
        """The document's header: its profile and version"""
        self.profile(profile)
        if version:
            self.scene.version = version
            chosen = dialects.DIALECTS.get(version)
            if chosen is None:
                known = sorted(dialects.DIALECTS, key=lambda v: tuple(map(int, v.split('.'))))
                same_major = [v for v in known if v.split('.')[0] == version.split('.')[0]]
                nearest = same_major[-1] if same_major else x3d.X3D_VERSION
                self.problem('warning', 'Unknown version %r; read as %s' % (version, nearest))
                chosen = dialects.DIALECTS[nearest]
            self.dialect = chosen.tables()
            self.version_name = chosen.name

    def profile(self, name: str) -> None:
        """The document's profile, from its header or a PROFILE statement"""
        if name and name not in profiles.PROFILES:
            self.problem('warning', 'Unknown profile %r' % name)
        self.scene.profile = name

    def component(self, name: str, level: int) -> None:
        """A `component` statement"""
        name = profiles.COMPONENT_ALIASES.get(name, name)
        if name not in profiles.COMPONENTS:
            self.problem('warning', 'Unknown component %r' % name)
        self.scene.components.append(ComponentInfo(name=name, level=level))

    def unit(self, category: str, name: str, conversionFactor: float) -> None:
        """A `unit` statement: values in `category` are scaled from here on"""
        if self.scene.version in ('2.0', '3.0', '3.1', '3.2'):
            # 7.2.5.5: UNIT statements are for X3D 3.3 and later.
            self.problem('error', 'UNIT statements need X3D 3.3 or later, not %s'
                         % self.scene.version)
            return
        if category not in ('angle', 'force', 'length', 'mass'):
            self.problem('error', 'Unknown unit category %r' % category)
            return
        if not (math.isfinite(conversionFactor) and conversionFactor > 0):
            self.problem('error', 'Unit %s has conversion factor %r' % (name, conversionFactor))
            return
        self._units[category] = conversionFactor
        self.scene.units.append(UnitInfo(
            category=category, name=name, conversionFactor=conversionFactor,
        ))

    def meta(self, name: str, content: str, **others: str) -> None:
        """A `meta` statement"""
        record = MetaInfo(name=name, content=content)
        for key, value in others.items():
            key = 'httpEquiv' if key == 'http-equiv' else key
            if key in ('dir', 'httpEquiv', 'lang', 'scheme'):
                setattr(record, key, value)
        self.scene.meta.append(record)

    def end_document(self, complete: bool = True) -> X3DScene:
        """The finished scene, rooted once

        complete -- False where the document stopped early (a syntax error
            already reported), so what is still open is closed without a
            problem for each part of it
        """
        while self._frames or self._protos:
            if self._frames:
                if complete:
                    self.problem('error', 'Node %s is not closed' % self._frames[-1].type_name)
                self.end_node()
            else:
                if complete:
                    self.problem('error', 'Prototype %s is not closed' % self._protos[-1].name)
                if self._proto_field:
                    self.end_proto_field_nodes()
                if self._body is self._protos[-1].body:
                    self.end_proto_body()
                self.end_proto()
        if self._scripts:
            self.problem(
                'warning',
                '%d Script node%s read; scripts are kept and not run'
                % (self._scripts, '' if self._scripts == 1 else 's'),
            )
        for name in sorted(self._unknown_types):
            self.problem('info', 'Node type %s has no implementation here' % name)
        scene = self.scene
        for name, value in self._scope.protos.items():
            scene.protoTypes[name] = value
        scene.defNames.update(self._scope.defs)
        scene.children = self._body.roots
        scene.routes = self._body.routes
        scene.problems = self._problems
        return scene

    # Nodes

    def _resolve_type(self, type_name: str) -> "type | None":
        found = self._scope.proto(type_name)
        if found is None:
            found = self.vocabulary.get(type_name)
            if self._engine and found is not None and found is x3d.CONCRETE_NODES.get(type_name):
                self._unknown_types.add(type_name)
        return found

    def start_node(
        self,
        type_name: str,
        DEF: str = '',
        USE: str = '',
        containerField: str = '',
    ) -> Any:
        """Begin a node, or a USE of a named one; answers the node or None"""
        parent = self._frames[-1] if self._frames else None
        if parent is not None and parent.skip:
            frame = _Frame(None, type_name, False)
            frame.skip = True
            self._frames.append(frame)
            return None
        if USE:
            built = self._lookup(USE)
            frame = _Frame(built, type_name, False)
            frame.used = True
            if built is None:
                self.problem('error', 'USE of %r, which no DEF names' % USE)
                frame.skip = True
            else:
                if DEF:
                    self.problem('error', 'Node has both DEF and USE')
                actual = protofunctions.protoName(built)
                if type_name and actual != type_name and type_name != 'ProtoInstance':
                    self.problem('warning', 'USE of %r names a %s, not a %s'
                                 % (USE, actual, type_name), built)
                self._place(built, containerField)
            self._frames.append(frame)
            return built
        cls = self._resolve_type(type_name)
        if cls is None:
            self.problem('error', 'Unknown node type %s' % type_name)
            frame = _Frame(None, type_name, False)
            frame.skip = True
            self._frames.append(frame)
            return None
        declared = x3d.CONCRETE_NODES.get(type_name)
        if (declared is not None and issubclass(cls, declared)
                and not self.dialect.has_node(type_name)):
            # A class that is not X3D's node is the vocabulary's own, in no version.
            self.problem('warning', '%s has no node %s' % (self.version_name, type_name))
        built = cls()
        notify = isinstance(built, node.PrototypedNode)
        if not notify:
            # In the document's scene before any field is set, so a field that
            # reads the document (a url resolved against it) finds it. A
            # prototype instance is rooted with its body when it is placed.
            protofunctions.root(built, self.scene)
        if isinstance(built, x3d.X3DScriptNode):
            self._scripts += 1
        frame = _Frame(built, type_name, notify)
        if DEF:
            self._define(DEF, built)
        self._place(built, containerField)
        self._frames.append(frame)
        return built

    def end_node(self) -> Any:
        """Finish the open node: set its node fields and the dialect's defaults"""
        frame = self._frames.pop()
        if frame.skip or frame.used:
            return frame.node
        built = frame.node
        for name, values in frame.children.items():
            declared = protofunctions.getField(built, name)
            if isinstance(declared, node.MFNode):
                declared.fset(built, values, notify=frame.notify)
            elif values:
                if len(values) > 1:
                    self.problem('error', '%s.%s holds one node, given %d'
                                 % (frame.type_name, name, len(values)), built)
                declared.fset(built, values[-1], notify=frame.notify)
            frame.set_fields.add(name)
        for name, value in dialect.declared_defaults(type(built), frame.type_name):
            if name not in frame.set_fields:
                declared = protofunctions.getField(built, name)
                declared.fset(built, declared.copyValue(value), notify=False)
        for name, value in self.dialect.defaults(frame.type_name):
            if name not in frame.set_fields:
                declared = protofunctions.getField(built, name)
                declared.fset(built, declared.copyValue(value), notify=False)
        extension.restore(built, self._resolve_type,
                          lambda message: self.problem('warning', message, built))
        return built

    def defined(self, name: str) -> bool:
        """Whether a DEF in the current scope has given `name` a node"""
        return self._lookup(name) is not None

    def _current_name(self, target: Any, type_name: str, name: str) -> str:
        """The current name of `type_name`'s field `name` in the document's dialect

        A prototype instance keeps the names its prototype declares, even where the
        prototype shares a name with an X3D node the dialect renames fields of.
        """
        if isinstance(target, node.PrototypedNode):
            return name
        return self.dialect.current_name(type_name, name)

    def field_type(self, name: str) -> "str | None":
        """The type of the open node's field `name`, as its document names it

        None where the node has no such field, or there is no open node.
        """
        frame = self._frames[-1] if self._frames else None
        if frame is None or frame.node is None:
            return None
        try:
            declared = protofunctions.getField(
                frame.node, self._current_name(frame.node, frame.type_name, name))
        except AttributeError:
            return None
        # An attribute of the node's class that is not a field (a prototype
        # instance's `nodeType`) names no field
        if not isinstance(declared, (field.Field, field.Event)):
            return None
        return str(declared.typeName())

    def current_node(self) -> Any:
        """The node being built, or None outside one or in skipped content"""
        if not self._frames:
            return None
        return self._frames[-1].node

    def encoding_attribute(self, name: str) -> bool:
        """Whether an attribute of the open node's element is the encoding's
        (XML's and JSON's) rather than one of its fields: `DEF`, `USE`,
        `containerField`, `class`, `id`, and `style` where the node has no
        `style` field of its own (`FontStyle` has)"""
        if name not in ENCODING_ATTRIBUTES:
            return False
        if name == 'style':
            return not isinstance(getattr(type(self.current_node()), 'style', None), field.Field)
        return True

    def current_type(self) -> str:
        """The X3D type name of the node being built, as the document names it; ''
        outside one"""
        return self._frames[-1].type_name if self._frames else ''

    def source_text(self, text: str) -> None:
        """Program text inside the open node, for its `sourceCode` field

        X3D 4.1 gives Script, ShaderPart and ShaderProgram a sourceCode field
        for the source a document carries inline; it is kept verbatim.
        """
        if not self._frames or self._frames[-1].node is None:
            return
        frame = self._frames[-1]
        declared = getattr(type(frame.node), 'sourceCode', None)
        if not isinstance(declared, field.Field):
            if text.strip():
                self.problem('warning', '%s holds no text' % frame.type_name, frame.node)
            return
        declared.fset(frame.node, declared.fget(frame.node) + text, notify=False)
        frame.set_fields.add('sourceCode')

    def start_field(self, name: str) -> None:
        """Nodes started until `end_field` go into the open node's field `name`"""
        if self._frames:
            self._frames[-1].target.append(name)

    def end_field(self) -> None:
        if self._frames and self._frames[-1].target:
            self._frames[-1].target.pop()

    def _lookup(self, name: str) -> Any:
        return self._scope.defs.get(name)

    def _define(self, name: str, built: Any) -> None:
        if name in self._scope.defs:
            self.problem('warning', 'DEF %r is named twice; the later node takes it' % name)
        self._scope.defs[name] = built
        protofunctions.defName(built, name, notify=0)

    def _place(self, built: Any, containerField: str) -> None:
        """Put a node in its parent's field, or among the body's roots"""
        if self._proto_field and len(self._frames) == self._proto_field[-1][3]:
            self._proto_field[-1][2].append(built)
            return
        if not self._frames:
            self._body.roots.append(built)
            return
        parent = self._frames[-1]
        if parent.node is None:
            return
        if parent.target:
            containerField = parent.target[-1]
        name = self._container(parent, built, containerField)
        if name is not None:
            parent.children.setdefault(name, []).append(built)

    def _container(self, parent: _Frame, built: Any, explicit: str) -> "str | None":
        """The parent field a node goes into: the explicit one, else the implied one"""
        name: "str | None"
        if explicit:
            name = self._current_name(parent.node, parent.type_name, explicit)
            declared = _node_field(parent.node, name)
            if declared is not None and node.accepts(_field_types(declared), built):
                return name
            why = 'has no node field' if declared is None else 'does not accept a %s in field' % (
                protofunctions.protoName(built))
            self.problem('error', '%s %s %s' % (parent.type_name, why, name), built)
            return None
        # The vocabulary's default container, whatever the version: X3D 3.x
        # gives metadata nodes `metadata`, where documents of that age, and
        # X_ITE, put them in a MetadataSet's `value`
        name = implied_container(parent.node, built)
        if name is None:
            self.problem('error', '%s has no field that holds a %s'
                         % (parent.type_name, protofunctions.protoName(built)), built)
        return name

    # Field values

    def field_text(self, name: str, text: str) -> None:
        """A field value as XML attribute text, decoded by its field type"""
        declared, frame = self._settable(name)
        if declared is None or frame is None:
            return
        type_name = declared.typeName()
        try:
            value = codecs.decode(type_name, text)
        except (KeyError, ValueError) as error:
            self.problem('error', '%s.%s: %s' % (frame.type_name, name, error), frame.node)
            return
        if type_name == 'MFString' and not codecs.is_quoted(text):
            self.problem('warning', '%s.%s: MFString value not quoted: %r'
                         % (frame.type_name, name, text[:40]), frame.node)
        elif type_name == 'MFString' and codecs.undefined_escape(text):
            self.problem('warning', '%s.%s: a backslash before a character other than " or '
                         '\\ is dropped: %r' % (frame.type_name, name, text[:40]), frame.node)
        self._set(frame, declared, value)

    def field(self, name: str, value: Any) -> None:
        """A field value already of the field's kind (numbers, strings, lists)"""
        declared, frame = self._settable(name)
        if declared is None or frame is None:
            return
        self._set(frame, declared, value)

    def _settable(self, name: str) -> "tuple[Any, _Frame | None]":
        if not self._frames:
            self.problem('error', 'Field %s outside a node' % name)
            return None, None
        frame = self._frames[-1]
        if frame.skip or frame.node is None:
            return None, None
        if frame.used:
            self.problem('error', 'USE node given field %s' % name, frame.node)
            return None, None
        current = self._current_name(frame.node, frame.type_name, name)
        try:
            declared = protofunctions.getField(frame.node, current)
        except AttributeError:
            declared = None
        if isinstance(declared, field.Event):
            self.problem('warning', '%s.%s is an event and takes no value'
                         % (frame.type_name, name), frame.node)
            return None, None
        if not isinstance(declared, field.Field):
            self.problem('warning', '%s has no field %s' % (frame.type_name, name), frame.node)
            return None, None
        if not isinstance(frame.node, node.PrototypedNode) and not self.dialect.has_field(
                frame.type_name, current):
            self.problem('warning', '%s has no field %s.%s'
                         % (self.version_name, frame.type_name, current), frame.node)
        return declared, frame

    def _set(self, frame: _Frame, declared: Any, value: Any) -> None:
        if declared.unitCategory and self._units:
            value = self._scaled(declared, value)
        try:
            declared.fset(frame.node, value, notify=frame.notify)
        except ValueError as error:
            self.problem('error', '%s.%s: %s' % (frame.type_name, declared.name, error),
                         frame.node)
            return
        frame.set_fields.add(declared.name)

    def _scaled(self, declared: Any, value: Any) -> Any:
        """A value in the document's units, in the scene's base units"""
        return scaled(declared, value, unit_factor(declared.unitCategory, self._units))

    # Fields a Script or shader declares

    def declare_field(
        self,
        name: str,
        type_name: str,
        accessType: str,
        text: "str | None" = None,
        value: Any = _UNSET,
    ) -> None:
        """A field a Script or programmable shader declares for itself"""
        if not self._frames or self._frames[-1].node is None:
            self.problem('error', 'Field declaration %s outside a node' % name)
            return
        frame = self._frames[-1]
        if not isinstance(frame.node, DECLARES_FIELDS):
            self.problem('error', '%s does not declare fields' % frame.type_name, frame.node)
            return
        declared = self._declaration(name, type_name, accessType, text, value)
        if declared is None:
            return
        built = frame.node
        own = type(built)
        if not own.__dict__.get(' declares', False):
            own = type(own.__name__, (own,), {'PROTO': protofunctions.protoName(built),
                                              ' declares': True})
            built.__class__ = own
        protofunctions.addField(own, declared)
        if isinstance(declared, field.Field) and (text is not None or value is not _UNSET):
            frame.set_fields.add(name)
            declared.fset(built, declared.getDefault(), notify=False)

    def _declaration(
        self, name: str, type_name: str, accessType: str,
        text: "str | None", value: Any,
    ) -> Any:
        if type_name not in field.baseFieldTypes:
            self.problem('error', 'Field %s has unknown type %s' % (name, type_name))
            return None
        if accessType in ('inputOnly', 'outputOnly', 'eventIn', 'eventOut'):
            return field.newEvent(name, type_name, accessType in ('outputOnly', 'eventOut'))
        if accessType not in ('inputOutput', 'initializeOnly', 'exposedField', 'field'):
            self.problem('error', 'Field %s has unknown access type %s' % (name, accessType))
            return None
        exposure = int(accessType in ('inputOutput', 'exposedField'))
        if text is not None:
            try:
                value = codecs.decode(type_name, text)
            except (KeyError, ValueError) as error:
                self.problem('error', 'Field %s: %s' % (name, error))
                value = _UNSET
        if value is _UNSET or value is None and type_name == 'SFNode':
            return field.newField(name, type_name, exposure)
        try:
            return field.newField(name, type_name, exposure, field.baseFieldTypes[type_name](
                name, exposure).coerce(value))
        except ValueError as error:
            self.problem('error', 'Field %s: %s' % (name, error))
            return field.newField(name, type_name, exposure)

    # Prototypes

    def start_proto(self, name: str, extern: bool = False) -> None:
        """Begin a ProtoDeclare/PROTO or ExternProtoDeclare/EXTERNPROTO"""
        self._protos.append(_ProtoDefinition(name, extern, self._scope))

    def proto_field(
        self,
        name: str,
        type_name: str,
        accessType: str,
        text: "str | None" = None,
        value: Any = _UNSET,
    ) -> None:
        """A field of the prototype's interface, with its default"""
        if not self._protos:
            self.problem('error', 'Prototype field %s outside a prototype' % name)
            return
        declared = self._declaration(name, type_name, accessType, text, value)
        if declared is not None:
            self._protos[-1].fields.append(declared)

    def start_proto_field_nodes(self, name: str) -> None:
        """The nodes started until `end_proto_field_nodes` are field `name`'s default"""
        definition = self._protos[-1]
        declared = next((item for item in definition.fields if item.name == name), None)
        self._proto_field.append((definition, declared, [], len(self._frames)))

    def end_proto_field_nodes(self) -> None:
        definition, declared, nodes, _depth = self._proto_field.pop()
        if declared is None:
            self.problem('error', 'Nodes given for an undeclared prototype field')
            return
        if isinstance(declared, field.Event):
            # An event carries no value, so has no default to give
            if nodes:
                self.problem('error', 'Prototype field %s is %s, which takes no default'
                             % (declared.name, declared.accessType))
            return
        default = nodes if isinstance(declared, node.MFNode) else (nodes[-1] if nodes else node.NULL)
        replacement = type(declared)(declared.name, declared.exposure, default)
        definition.fields[definition.fields.index(declared)] = replacement

    def start_proto_body(self) -> None:
        """Begin a prototype's body: a scope of its own for DEF names"""
        definition = self._protos[-1]
        scope = _Scope(self._scope)
        definition.body = _Body(scope)
        self._scope = scope
        self._bodies.append(definition.body)
        self._body = definition.body
        definition.outside = self._frames
        self._frames = []

    def end_proto_body(self) -> None:
        if self._frames:
            self.problem('error', 'Node %s is not closed' % self._frames[-1].type_name)
        self._frames = self._protos[-1].outside
        self._bodies.pop()
        self._body = self._bodies[-1]
        assert self._scope.parent is not None
        self._scope = self._scope.parent

    def proto_url(self, urls: Sequence[str]) -> None:
        """An EXTERNPROTO's URLs"""
        self._protos[-1].urls = list(urls)

    def connect(self, nodeField: str, protoField: str) -> None:
        """An IS connection: the open node's field is the prototype's field"""
        if not self._protos or not self._frames or self._frames[-1].node is None:
            self.problem('error', 'IS connection %s/%s outside a prototype body'
                         % (nodeField, protoField))
            return
        frame = self._frames[-1]
        definition = next((item for item in reversed(self._protos) if item.body is not None),
                          None)
        if definition is None:
            self.problem('error', 'IS connection outside a prototype body')
            return
        interface = next((item for item in definition.fields if item.name == protoField), None)
        if interface is None:
            self.problem('error', 'IS names %s, which prototype %s does not declare'
                         % (protoField, definition.name), frame.node)
            return
        current = self._current_name(frame.node, frame.type_name, nodeField)
        try:
            declared = protofunctions.getField(frame.node, current)
        except AttributeError:
            self.problem('error', '%s has no field %s to connect'
                         % (frame.type_name, nodeField), frame.node)
            return
        if declared.typeName() != interface.typeName():
            self.problem('error', 'IS joins %s.%s, an %s, to %s, an %s'
                         % (frame.type_name, nodeField, declared.typeName(), protoField,
                            interface.typeName()), frame.node)
            return
        if declared.accessType != 'inputOutput' and declared.accessType != interface.accessType:
            # ISO/IEC 19775-1 4.4.4.3 forbids it; the connection is kept, so
            # the value an instance gives still reaches the node.
            self.problem('warning', 'IS joins %s.%s, which is %s, to %s, which is %s'
                         % (frame.type_name, nodeField, declared.accessType, protoField,
                            interface.accessType), frame.node)
        definition.connections.append((protoField, frame.node, current))
        frame.set_fields.add(current)

    def end_proto(self) -> "type | None":
        """Finish the prototype: its class, registered in the enclosing scope"""
        definition = self._protos.pop()
        if definition.extern:
            cls = cast(ProtoClass, node.prototype(definition.name, definition.fields,
                                                  externalURL=definition.urls))
            node.PENDING_PROTOTYPES[cls] = weakref.WeakSet()
            definition.scope.protos[definition.name] = cls
            if self.extern_resolver is not None:
                found = self.extern_resolver(definition.urls, self.scene.baseURI, definition.name)
                if found is None:
                    self.problem('warning', 'EXTERNPROTO %s: none of %s could be read'
                                 % (definition.name, ', '.join(definition.urls)))
                else:
                    for message in complete_extern_proto(cls, found):
                        self.problem('error', message)
            else:
                self.problem('info', 'EXTERNPROTO %s is not read: no resolver was given'
                             % definition.name)
            return cls
        body = definition.body or _Body(_Scope(definition.scope))
        template = SceneGraph(children=body.roots, routes=body.routes)
        template.defNames.update(body.scope.defs)
        template.protoTypes.update(body.scope.protos)
        first = body.roots[0] if body.roots else None
        nodeType = getattr(first, 'nodeType', None) if isinstance(first, node.PrototypedNode) else (
            type(first) if first is not None else None)
        cls = cast(ProtoClass, node.prototype(definition.name, definition.fields, template))
        cls.nodeType = nodeType
        ismaps = node.ismaps(cls)
        for protoField, target, nodeField in definition.connections:
            ismaps.setdefault(protoField, []).append((target, nodeField))
        definition.scope.protos[definition.name] = cls
        return cls

    # Routes, imports and exports

    def route(self, fromNode: str, fromField: str, toNode: str, toField: str) -> Any:
        """A ROUTE between two named nodes; answers the route, or None"""
        source = self._lookup(fromNode)
        destination = self._lookup(toNode)
        missing = [name for name, found in ((fromNode, source), (toNode, destination))
                   if found is None]
        if missing:
            if all(name in self._scope.imports for name in missing):
                self.scene.pendingRoutes.append(RouteInfo(
                    fromNode=fromNode, fromField=fromField, toNode=toNode, toField=toField,
                ))
                return None
            self.problem('error', 'ROUTE names %s, which no DEF names' % ', '.join(missing))
            return None
        sourceField = self._route_field(source, fromField, 'from')
        destinationField = self._route_field(destination, toField, 'to')
        if sourceField is None or destinationField is None:
            return None
        sourceType = protofunctions.getField(source, sourceField).typeName()
        destinationType = protofunctions.getField(destination, destinationField).typeName()
        if sourceType != destinationType:
            self.problem('error', 'ROUTE from %s.%s, an %s, to %s.%s, an %s'
                         % (fromNode, fromField, sourceType, toNode, toField, destinationType))
            return None
        made = route.ROUTE(source, sourceField, destination, destinationField)
        self._body.routes.append(made)
        return made

    def _route_field(self, target: Any, name: str, end: str) -> "str | None":
        type_name = protofunctions.protoName(target)
        current = self._current_name(target, type_name, name)
        for prefix, suffix in (('set_', ''), ('', '_changed')):
            if name.startswith(prefix) and name.endswith(suffix) and (prefix or suffix):
                bare = name[len(prefix):len(name) - len(suffix)]
                renamed = self._current_name(target, type_name, bare)
                if renamed != bare:
                    current = prefix + renamed + suffix
        try:
            declared = protofunctions.getField(target, current)
        except AttributeError:
            self.problem('error', 'ROUTE %s %s.%s: no such field' % (end, type_name, name), target)
            return None
        access = declared.accessType
        if end == 'from' and access in ('inputOnly', 'initializeOnly'):
            self.problem('error', 'ROUTE from %s.%s, which is %s' % (type_name, name, access), target)
            return None
        if end == 'to' and access in ('outputOnly', 'initializeOnly'):
            self.problem('error', 'ROUTE to %s.%s, which is %s' % (type_name, name, access), target)
            return None
        if not isinstance(target, node.PrototypedNode) and not self.dialect.has_field(
                type_name, declared.name):
            self.problem('warning', '%s has no field %s.%s'
                         % (self.version_name, type_name, declared.name), target)
        return current

    def import_(self, inlineDEF: str, importedDEF: str, AS: str = '') -> None:
        """An IMPORT statement"""
        local = AS or importedDEF
        if self._lookup(inlineDEF) is None:
            self.problem('error', 'IMPORT from %r, which no DEF names' % inlineDEF)
        self._scope.imports.add(local)
        self.scene.imports.append(ImportInfo(
            inlineDEF=inlineDEF, importedDEF=importedDEF, localDEF=local,
        ))

    def export(self, localDEF: str, AS: str = '') -> None:
        """An EXPORT statement"""
        if self._lookup(localDEF) is None:
            self.problem('error', 'EXPORT of %r, which no DEF names' % localDEF)
        self.scene.exports.append(ExportInfo(localDEF=localDEF, AS=AS or localDEF))


def _node_field(target: Any, name: str) -> Any:
    """`target`'s node field `name`, or None"""
    try:
        declared = protofunctions.getField(target, name)
    except AttributeError:
        return None
    if isinstance(declared, (node.SFNode, node.MFNode)):
        return declared
    return None


def implied_container(parent: Any, child: Any, dialect: Any = None) -> "str | None":
    """The field of `parent` a `child` with no containerField goes into

    The child type's default container, the `dialect`'s where it gives one
    (a version's default that differs from the vocabulary's), where the
    parent has that field and it accepts the child; else the first, by name,
    of the parent's node fields that accepts it; None where none does. A
    prototype instance whose node type is not known (an EXTERNPROTO not read)
    goes in `children`, the ProtoInstance's own default (ISO/IEC 19776-1),
    or nowhere.
    """
    if isinstance(child, node.PrototypedNode) and getattr(child, 'nodeType', None) is None:
        declared = _node_field(parent, 'children')
        return 'children' if declared is not None else None
    own = child if not isinstance(child, node.PrototypedNode) else getattr(child, 'nodeType', None)
    versioned = dialect.container(protofunctions.protoName(own)) if (
        dialect is not None and own is not None) else None
    default = versioned or getattr(child, 'CONTAINER_FIELD', '') or getattr(
        getattr(child, 'nodeType', None), 'CONTAINER_FIELD', '')
    if default:
        declared = _node_field(parent, default)
        if declared is not None and node.accepts(_field_types(declared), child):
            return str(default)
    for declared in sorted(protofunctions.getFields(parent), key=lambda f: f.name):
        if isinstance(declared, (node.SFNode, node.MFNode)) and not declared.name.startswith(' '):
            if node.accepts(_field_types(declared), child):
                return str(declared.name)
    return None


def _field_types(declared: Any) -> "tuple[type, ...]":
    """The types a node field accepts"""
    types = declared.requiredTypes
    if isinstance(declared, node.MFNode) and not types:
        types = type(declared).baseSFNode.requiredTypes
    return types or (node.Node,)


def complete_extern_proto(extern: "ProtoClass", definition: type) -> "list[str]":
    """Give an EXTERNPROTO's class the body of the prototype that defines it

    The definition's field declarations replace the EXTERNPROTO's, so its
    defaults are the definition's (ISO/IEC 19775-1, 4.4.5.2). Instances made
    before the definition arrived are given their bodies. Answers a message
    for each field whose type the two declare differently.
    """
    mismatches = []
    for declared in protofunctions.getFields(definition) + protofunctions.getFields(definition, 1):
        if declared.name.startswith(' ') or getattr(node.Node, declared.name, None) is declared:
            continue
        try:
            existing = protofunctions.getField(extern, declared.name)
        except AttributeError:
            existing = None
        if existing is not None and existing.typeName() != declared.typeName():
            mismatches.append('EXTERNPROTO %s declares %s as %s, its definition as %s' % (
                protofunctions.protoName(extern), declared.name, existing.typeName(),
                declared.typeName()))
            continue
        replacement = declared.copy(definition) if isinstance(declared, field.Field) else (
            declared.clone())
        protofunctions.addField(extern, replacement)
    node.PrototypedNode.scenegraph.fset(extern, protofunctions.getSceneGraph(definition))
    extern.nodeType = getattr(definition, 'nodeType', None)
    ismaps = node.ismaps(extern)
    ismaps.clear()
    ismaps.update(node.ismaps(definition))
    for instance in list(node.PENDING_PROTOTYPES.pop(extern, ())):
        node.PrototypedNode.instantiate(instance)
    return mismatches


def bind_imports(scene: X3DScene, inline: Any, inlined: X3DScene) -> "list[str]":
    """Bind the scene's IMPORTs from an Inline that has loaded

    `inline` is the Inline node, and `inlined` the scene it loaded. Each
    IMPORT naming the Inline's DEF name and a node `inlined` exports is
    bound to that node, and each pending route whose ends are now all known
    is made. Answers the local names bound.
    """
    inlineDEF = protofunctions.defName(inline)
    exported = {item.AS: inlined.getDEF(item.localDEF) for item in inlined.exports}
    bound = []
    for record in scene.imports:
        if record.inlineDEF == inlineDEF and exported.get(record.importedDEF) is not None:
            scene.defNames[record.localDEF] = exported[record.importedDEF]
            bound.append(record.localDEF)
    for record in list(scene.pendingRoutes):
        source = scene.getDEF(record.fromNode)
        destination = scene.getDEF(record.toNode)
        if source is not None and destination is not None:
            scene.addRoute(route.ROUTE(source, record.fromField, destination, record.toField))
            scene.pendingRoutes.remove(record)
    return bound
