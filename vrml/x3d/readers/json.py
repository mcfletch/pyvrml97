"""The X3D JSON encoding, read with the standard `json` module

Web3D's X3D JSON design: a document is `{"X3D": {...}}`; a node is an
object with one key, its type, whose value holds its fields as `@name`
values, its node fields as `-name` (an object or a list of them), and
`#comment` and `#sourceCode` entries. Statements (`ROUTE`, `ProtoDeclare`,
`IMPORT`, ...) appear among the nodes. Values arrive typed, so they go to
the builder as values rather than text.
"""

import contextlib
import json
from collections.abc import Iterator, Mapping
from typing import Any

from vrml.x3d import codecs
from vrml.x3d.builder import XML_NAME, SceneBuilder
from vrml.x3d.scene import X3DScene

#: `@` keys of a node object that are the encoding's, not the node's.
#: A ProtoInstance's member naming its prototype, which is not one of its fields.
PROTOTYPE_NAME = frozenset(('@name',))
#: A DEF's node type, the members that are not its fields, and its object.
_Definition = tuple[str, frozenset[str], Mapping]


def _typed(type_name: str, value: Any) -> Any:
    """A typed value (JSON's) in the shape its field type takes

    Web3D's JSON converter writes a string field whose text is `true` as a
    JSON boolean, and some MFString values as one string in their XML text
    form.
    """
    if type_name == 'SFString' and isinstance(value, bool):
        return 'true' if value else 'false'
    if type_name == 'MFString':
        if isinstance(value, str) and value.lstrip().startswith('"'):
            return codecs.decode('MFString', value)
        if isinstance(value, list):
            return [('true' if item else 'false') if isinstance(item, bool) else item
                    for item in value]
    return value


class JSONReader:
    """Turns a decoded X3D JSON document into builder calls"""

    def __init__(self, builder: SceneBuilder, charset: "str | None" = None) -> None:
        self.builder = builder
        builder.def_names = XML_NAME
        #: The members and indexes leading to where the reader is.
        self.path: "list[str]" = []
        self.charset = charset or 'utf-8-sig'
        #: For each open DEF scope (the scene, each prototype body): the
        #: node type and object each of its DEFs names, and the names built
        #: ahead of their DEF because a USE came first.
        self.scopes: "list[tuple[dict[str, _Definition], set[str]]]" = []

    def read(self, data: bytes) -> X3DScene:
        try:
            document = json.loads(data.decode(self.charset))
        except (ValueError, UnicodeDecodeError) as error:
            self.builder.problem('error', 'JSON: %s' % error)
            return self.builder.end_document(complete=False)
        top = document.get('X3D') if isinstance(document, dict) else None
        if not isinstance(top, dict):
            self.builder.problem('error', 'JSON document has no X3D object')
            return self.builder.end_document(complete=False)
        self.builder.document(str(top.get('@profile', '')), str(top.get('@version', '')))
        self._head(self._object(top.get('head'), 'head'))
        try:
            with self._at('Scene'):
                self._scope(self._object(top.get('Scene'), 'Scene').get('-children'))
        except RecursionError:
            self.builder.problem('error', 'JSON: nodes nested too deeply to read')
            return self.builder.end_document(complete=False)
        return self.builder.end_document()

    def _object(self, value: Any, what: str) -> Mapping:
        """`value`, or an empty object where it is missing or not an object"""
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            self.builder.problem('error', 'JSON: %s is not an object' % what)
            return {}
        return value

    def _head(self, head: Mapping) -> None:
        for item in self._entries(head, 'component'):
            level = self._number(item, '@level', int, 1)
            if level is not None:
                self.builder.component(str(item.get('@name', '')), level)
        for item in self._entries(head, 'unit'):
            factor = self._number(item, '@conversionFactor', float, 0.0)
            if factor is not None:
                self.builder.unit(str(item.get('@category', '')), str(item.get('@name', '')),
                                  factor)
        for item in self._entries(head, 'meta'):
            others = {key[1:]: str(value) for key, value in item.items()
                      if key.startswith('@') and key not in ('@name', '@content')}
            self.builder.meta(str(item.get('@name', '')), str(item.get('@content', '')),
                              **others)

    def _entries(self, head: Mapping, kind: str) -> "list[Mapping]":
        """The head's `kind` entries that are objects; each other one is reported"""
        found = []
        for item in self._list(head.get(kind)):
            if isinstance(item, Mapping):
                found.append(item)
            else:
                self.builder.problem('error', 'JSON: %s %r is not an object' % (kind, item))
        return found

    def _number(self, item: Mapping, key: str, kind: "type[Any]", default: Any) -> Any:
        """`item[key]` as an int or float; None, reported, where it is not a number"""
        value = item.get(key, default)
        try:
            return kind(value)
        except (TypeError, ValueError):
            self.builder.problem('error', 'JSON: %s %r is not a number' % (key[1:], value))
            return None

    @contextlib.contextmanager
    def _at(self, part: str) -> Iterator[None]:
        """Within the member or index `part` of the one before, for problems' paths"""
        self.path.append(part)
        self.builder.path = '/'.join(self.path)
        try:
            yield
        finally:
            self.path.pop()
            self.builder.path = '/'.join(self.path)

    def _scope(self, items: Any) -> None:
        """Read the nodes of one DEF scope"""
        definitions: "dict[str, _Definition]" = {}
        self._prescan(items, definitions)
        self.scopes.append((definitions, set()))
        try:
            self._items(items, '-children')
        finally:
            self.scopes.pop()

    def _prescan(self, items: Any, definitions: "dict[str, _Definition]") -> None:
        """Find the node objects DEFs name in one scope, not entering prototypes

        Object members are grouped by field name rather than kept in
        document order, so a USE can come before the DEF it names.
        """
        for item in self._list(items):
            if not isinstance(item, Mapping):
                continue
            for name, value in item.items():
                if not isinstance(value, Mapping) or name.startswith('#') or name in (
                        'ProtoDeclare', 'ExternProtoDeclare'):
                    continue
                if '@DEF' in value:
                    definitions.setdefault(str(value['@DEF']), self._started(name, value) + (value,))
                for key, inner in value.items():
                    if key.startswith('-'):
                        self._prescan(inner, definitions)
                    elif key in ('field', 'fieldValue'):
                        for declaration in self._list(inner):
                            if isinstance(declaration, Mapping):
                                self._prescan(declaration.get('-children'), definitions)

    @staticmethod
    def _started(name: str, value: Mapping) -> "tuple[str, frozenset[str]]":
        """The node type an object under the member `name` starts, and the
        members that are not its fields"""
        if name == 'ProtoInstance':
            return str(value.get('@name', '')), PROTOTYPE_NAME
        return name, frozenset()

    @staticmethod
    def _list(value: Any) -> "list[Any]":
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _items(self, items: Any, key: str) -> None:
        """Nodes and statements, in document order: the member `key`'s value"""
        listed = isinstance(items, list)
        for index, item in enumerate(self._list(items)):
            with self._at('%s[%d]' % (key, index) if listed else key):
                if not isinstance(item, Mapping):
                    self.builder.problem('error', 'JSON: expected a node, found %r' % (item,))
                    continue
                for name, value in item.items():
                    self._item(name, value)

    def _item(self, name: str, value: Any) -> None:
        if name.startswith('#'):
            return
        with self._at(name):
            if not isinstance(value, Mapping):
                self.builder.problem('error', 'JSON: %s is not an object' % name)
                return
            statement = getattr(self, '_statement_' + name, None)
            if statement is not None:
                statement(value)
            else:
                self._node(name, value)

    def _node(
        self, name: str, value: Mapping, skip: "frozenset[str]" = frozenset(),
        containerField: "str | None" = None,
    ) -> None:
        if containerField is None:
            containerField = str(value.get('@containerField', ''))
        DEF = str(value.get('@DEF', ''))
        USE = str(value.get('@USE', ''))
        if self.scopes:
            definitions, early = self.scopes[-1]
            if USE and not self.builder.defined(USE) and USE in definitions:
                defined_type, defined_skip, defined = definitions[USE]
                self._node(defined_type, defined, defined_skip, containerField)
                early.add(USE)
                return
            if DEF and DEF in early:
                DEF, USE = '', DEF
        self.builder.start_node(name, DEF=DEF, USE=USE, containerField=containerField)
        if not USE:
            self._contents(value, skip)
        self.builder.end_node()

    def _contents(self, value: Mapping, skip: "frozenset[str]") -> None:
        """A node's fields, declarations, IS connections and source"""
        for key, item in value.items():
            if key in skip:
                continue
            if key.startswith('@'):
                attribute = key[1:]
                if not self.builder.encoding_attribute(attribute):
                    with self._at(key):
                        self.builder.field(attribute,
                                           _typed(self.builder.field_type(attribute) or '', item))
            elif key.startswith('-'):
                self.builder.start_field(key[1:])
                self._items(item, key)
                self.builder.end_field()
            elif key == 'field':
                for declaration in self._list(item):
                    self._declare(declaration)
            elif key == 'IS':
                for connection in self._list(item.get('connect')):
                    self.builder.connect(str(connection.get('@nodeField', '')),
                                         str(connection.get('@protoField', '')))
            elif key == 'fieldValue':
                for given in self._list(item):
                    name = str(given.get('@name', ''))
                    if '@value' in given:
                        self.builder.field(name, given['@value'])
                    if '-children' in given:
                        self.builder.start_field(name)
                        self._items(given['-children'], '-children')
                        self.builder.end_field()
            elif key == '#sourceCode':
                lines = self._list(item)
                self.builder.source_text('\n'.join(str(line) for line in lines))

    def _declare(self, declaration: Mapping, proto: bool = False) -> None:
        """A field a node (a Script, a shader) or, with `proto`, a prototype
        declares, with its default"""
        name = str(declaration.get('@name', ''))
        type_name = str(declaration.get('@type', ''))
        access = str(declaration.get('@accessType', ''))
        declare = self.builder.proto_field if proto else self.builder.declare_field
        if '@value' in declaration:
            declare(name, type_name, access, value=_typed(type_name, declaration['@value']))
        else:
            declare(name, type_name, access)
        if '-children' in declaration:
            if proto:
                self.builder.start_proto_field_nodes(name)
            else:
                self.builder.start_field(name)
            self._items(declaration['-children'], '-children')
            if proto:
                self.builder.end_proto_field_nodes()
            else:
                self.builder.end_field()

    # Statements

    def _statement_ROUTE(self, value: Mapping) -> None:
        self.builder.route(str(value.get('@fromNode', '')), str(value.get('@fromField', '')),
                           str(value.get('@toNode', '')), str(value.get('@toField', '')))

    def _statement_IMPORT(self, value: Mapping) -> None:
        self.builder.import_(str(value.get('@inlineDEF', '')), str(value.get('@importedDEF', '')),
                             str(value.get('@AS', '')))

    def _statement_EXPORT(self, value: Mapping) -> None:
        self.builder.export(str(value.get('@localDEF', '')), str(value.get('@AS', '')))

    def _statement_ProtoDeclare(self, value: Mapping) -> None:
        self.builder.start_proto(str(value.get('@name', '')))
        interface = value.get('ProtoInterface') or {}
        for declaration in self._list(interface.get('field')):
            self._declare(declaration, proto=True)
        self.builder.start_proto_body()
        self._scope((value.get('ProtoBody') or {}).get('-children'))
        self.builder.end_proto_body()
        self.builder.end_proto()

    def _statement_ExternProtoDeclare(self, value: Mapping) -> None:
        self.builder.start_proto(str(value.get('@name', '')), extern=True)
        self.builder.proto_url([str(url) for url in self._list(value.get('@url'))])
        for declaration in self._list(value.get('field')):
            self._declare(declaration, proto=True)
        self.builder.end_proto()

    def _statement_ProtoInstance(self, value: Mapping) -> None:
        name, skip = self._started('ProtoInstance', value)
        self._node(name, value, skip)


def read(data: bytes, builder: SceneBuilder, charset: "str | None" = None) -> X3DScene:
    """The scene an X3D JSON document builds; its text is UTF-8 unless
    `charset` names another encoding"""
    return JSONReader(builder, charset).read(data)
