"""The X3D XML encoding (ISO/IEC 19776-1), read with expat

Elements become builder calls: `X3D`, `head` and its statements, `Scene`,
the prototype statements, `ROUTE`, `IMPORT`, `EXPORT`, and every other
element as a node whose attributes are field values in XML attribute text.

The parser fetches nothing: the DTD a document names is not read, and an
external entity is not expanded.
"""

from collections.abc import Callable
from typing import Any
from xml.parsers import expat

from vrml import field
from vrml.x3d import codecs
from vrml.x3d.builder import SceneBuilder
from vrml.x3d.scene import X3DScene

#: Attributes of a node element that are the encoding's, not the node's.
ENCODING_ATTRIBUTES = frozenset(('DEF', 'USE', 'containerField', 'class', 'id', 'style'))

#: Elements that only hold others.
CONTAINERS = frozenset(('head', 'Scene', 'ProtoInterface', 'IS'))


class _Element:
    """An open element: what it was read as, and what ending it does"""

    __slots__ = ('kind', 'ends', 'text', 'cdata')

    def __init__(self, kind: str, ends: "Callable[[], Any] | None" = None) -> None:
        self.kind = kind
        self.ends = ends
        self.text: "list[str]" = []
        self.cdata: "list[str]" = []


class ElementReader:
    """Turns the elements of an X3D document into builder calls

    An encoding's reader calls `_start`, `_end` and `_characters` in
    document order, setting `in_cdata` around the text of a CDATA section.
    """

    def __init__(self, builder: SceneBuilder) -> None:
        self.builder = builder
        self.stack: "list[_Element]" = []
        self.in_cdata = False
        self.statements: "dict[str, Callable[[dict[str, str]], _Element]]" = {
            'X3D': self._x3d,
            'component': self._component,
            'unit': self._unit,
            'meta': self._meta,
            'ROUTE': self._route,
            'IMPORT': self._import,
            'EXPORT': self._export,
            'ProtoDeclare': self._proto,
            'ExternProtoDeclare': self._extern_proto,
            'ProtoBody': self._proto_body,
            'field': self._field,
            'connect': self._connect,
            'ProtoInstance': self._proto_instance,
            'fieldValue': self._field_value,
        }

    def _position(self) -> None:
        """Tell the builder where in the document the reader is"""

    def _start(self, name: str, attributes: "dict[str, str]") -> None:
        self._position()
        if name in CONTAINERS:
            element = _Element(name)
        elif name in self.statements:
            element = self.statements[name](attributes)
        else:
            element = self._node(name, attributes)
        self.stack.append(element)

    def _end(self, _name: str) -> None:
        self._position()
        element = self.stack.pop()
        if element.kind == 'node':
            source = ''.join(element.cdata) or ''.join(element.text).strip()
            if source:
                self.builder.source_text(source)
        if element.ends is not None:
            element.ends()

    def _characters(self, data: str) -> None:
        if self.stack and self.stack[-1].kind == 'node':
            (self.stack[-1].cdata if self.in_cdata else self.stack[-1].text).append(data)

    def _parent_kind(self) -> str:
        return self.stack[-1].kind if self.stack else ''

    # Statements

    def _x3d(self, attributes: "dict[str, str]") -> _Element:
        self.builder.document(attributes.get('profile', ''), attributes.get('version', ''))
        return _Element('X3D')

    def _component(self, attributes: "dict[str, str]") -> _Element:
        try:
            level = int(attributes.get('level', '1'))
        except ValueError:
            self.builder.problem('error', 'component level %r' % attributes.get('level'))
        else:
            self.builder.component(attributes.get('name', ''), level)
        return _Element('statement')

    def _unit(self, attributes: "dict[str, str]") -> _Element:
        try:
            factor = float(attributes.get('conversionFactor', ''))
        except ValueError:
            self.builder.problem('error', 'unit conversionFactor %r'
                                 % attributes.get('conversionFactor'))
        else:
            self.builder.unit(attributes.get('category', ''), attributes.get('name', ''), factor)
        return _Element('statement')

    def _meta(self, attributes: "dict[str, str]") -> _Element:
        others = {key: value for key, value in attributes.items()
                  if key not in ('name', 'content')}
        self.builder.meta(attributes.get('name', ''), attributes.get('content', ''), **others)
        return _Element('statement')

    def _route(self, attributes: "dict[str, str]") -> _Element:
        self.builder.route(attributes.get('fromNode', ''), attributes.get('fromField', ''),
                           attributes.get('toNode', ''), attributes.get('toField', ''))
        return _Element('statement')

    def _import(self, attributes: "dict[str, str]") -> _Element:
        self.builder.import_(attributes.get('inlineDEF', ''), attributes.get('importedDEF', ''),
                             attributes.get('AS', ''))
        return _Element('statement')

    def _export(self, attributes: "dict[str, str]") -> _Element:
        self.builder.export(attributes.get('localDEF', ''), attributes.get('AS', ''))
        return _Element('statement')

    def _proto(self, attributes: "dict[str, str]") -> _Element:
        self.builder.start_proto(attributes.get('name', ''))
        return _Element('proto', self.builder.end_proto)

    def _extern_proto(self, attributes: "dict[str, str]") -> _Element:
        self.builder.start_proto(attributes.get('name', ''), extern=True)
        try:
            urls = codecs.decode('MFString', attributes.get('url', ''))
        except ValueError as error:
            self.builder.problem('error', 'ExternProtoDeclare url: %s' % error)
            urls = []
        self.builder.proto_url(urls)
        return _Element('extern', self.builder.end_proto)

    def _proto_body(self, _attributes: "dict[str, str]") -> _Element:
        self.builder.start_proto_body()
        return _Element('body', self.builder.end_proto_body)

    def _field(self, attributes: "dict[str, str]") -> _Element:
        name = attributes.get('name', '')
        type_name = attributes.get('type', '')
        access = attributes.get('accessType', '')
        value = attributes.get('value')
        holds_nodes = type_name in ('SFNode', 'MFNode')
        if self._parent_kind() in ('ProtoInterface', 'extern'):
            self.builder.proto_field(name, type_name, access, value)
            if holds_nodes:
                self.builder.start_proto_field_nodes(name)
                return _Element('field', self.builder.end_proto_field_nodes)
            return _Element('field')
        self.builder.declare_field(name, type_name, access, value)
        if holds_nodes:
            self.builder.start_field(name)
            return _Element('field', self.builder.end_field)
        return _Element('field')

    def _connect(self, attributes: "dict[str, str]") -> _Element:
        self.builder.connect(attributes.get('nodeField', ''), attributes.get('protoField', ''))
        return _Element('statement')

    def _proto_instance(self, attributes: "dict[str, str]") -> _Element:
        self.builder.start_node(
            attributes.get('name', ''), DEF=attributes.get('DEF', ''),
            USE=attributes.get('USE', ''), containerField=attributes.get('containerField', ''),
        )
        return _Element('node', self.builder.end_node)

    def _field_value(self, attributes: "dict[str, str]") -> _Element:
        name = attributes.get('name', '')
        if 'value' in attributes:
            self.builder.field_text(name, attributes['value'])
        self.builder.start_field(name)
        return _Element('fieldValue', self.builder.end_field)

    # Nodes

    def _node(self, name: str, attributes: "dict[str, str]") -> _Element:
        built = self.builder.start_node(
            name, DEF=attributes.get('DEF', ''), USE=attributes.get('USE', ''),
            containerField=attributes.get('containerField', ''),
        )
        style_is_a_field = isinstance(getattr(type(built), 'style', None), field.Field)
        for key, value in attributes.items():
            if key in ENCODING_ATTRIBUTES and not (key == 'style' and style_is_a_field):
                continue
            self._value(key, value)
        return _Element('node', self.builder.end_node)

    def _value(self, name: str, value: Any) -> None:
        """A node's field value, as the encoding gives it"""
        if (self.builder.field_type(name) in ('SFBool', 'MFBool')
                and any(word in ('TRUE', 'FALSE') for word in str(value).split())):
            self.builder.problem('warning', '%s="%s": XML writes a boolean as true or false'
                                 % (name, value))
        self.builder.field_text(name, value)


class XMLReader(ElementReader):
    """Turns expat's events into builder calls"""

    def __init__(self, builder: SceneBuilder, charset: "str | None" = None) -> None:
        super().__init__(builder)
        self.parser = expat.ParserCreate(charset)
        self.parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
        self.parser.ExternalEntityRefHandler = self._external_entity
        self.parser.StartElementHandler = self._start
        self.parser.EndElementHandler = self._end
        self.parser.CharacterDataHandler = self._characters
        self.parser.StartCdataSectionHandler = self._start_cdata
        self.parser.EndCdataSectionHandler = self._end_cdata
        self.parser.buffer_text = True

    def read(self, data: bytes) -> X3DScene:
        try:
            self.parser.Parse(data, True)
        except expat.ExpatError as error:
            self.builder.line = error.lineno
            self.builder.column = error.offset + 1
            self.builder.problem('error', 'XML: %s' % expat.errors.messages[error.code])
            return self.builder.end_document(complete=False)
        return self.builder.end_document()

    @staticmethod
    def _external_entity(*_arguments: Any) -> int:
        """Refuse every external entity: nothing a document names is read"""
        return 1

    def _position(self) -> None:
        self.builder.line = self.parser.CurrentLineNumber
        self.builder.column = self.parser.CurrentColumnNumber + 1

    def _start_cdata(self) -> None:
        self.in_cdata = True

    def _end_cdata(self) -> None:
        self.in_cdata = False


def read(data: bytes, builder: SceneBuilder, charset: "str | None" = None) -> X3DScene:
    """The scene an X3D XML document builds; `charset`, where given, is the
    encoding of its bytes in place of the one its XML declaration names"""
    return XMLReader(builder, charset).read(data)
