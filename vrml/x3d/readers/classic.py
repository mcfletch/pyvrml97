"""The ClassicVRML encoding (ISO/IEC 19776-2) and VRML97 (ISO/IEC 14772-1)

One reader for both: the first line says which (`#X3D V4.0 utf8` or
`#VRML V2.0 utf8`), and the VRML97 dialect applies to the second. Field
values are read by the type of the field they are for, which the builder
knows, so a bracketed list of numbers is taken as one slice of text and
decoded by the field's codec rather than number by number.

A file with an X3D header that declares fields with VRML97's words
(`field`, `exposedField`, `eventIn`, `eventOut`) is read with a warning,
which is an error in strict mode.
"""

import re
from typing import Any

from vrml.x3d import codecs
from vrml.x3d.builder import SceneBuilder
from vrml.x3d.scene import X3DScene

TOKEN = re.compile(r'''
    (?P<space>[ \t\r\n,]+)
  | (?P<block>\#/\*.*?\*/\#)
  | (?P<comment>\#[^\n]*)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<number>[+-]?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?))
  | (?P<punct>[{}\[\].:])
  | (?P<id>[^\x00-\x20"\#',.\[\]\\{}\x7f+\-0-9:][^\x00-\x20"\#',.\[\]\\{}\x7f]*)
''', re.VERBOSE | re.DOTALL)

HEADER = re.compile(r'#(VRML|X3D)\s+V?(\d+\.\d+)\s+utf8[^\n]*')

#: Up to the close of a list of numbers: anything but a string, a comment or
#: the bracket.
NUMBERS = re.compile(r'[^\]"#{}]*')

ACCESS_TYPES = {
    'initializeOnly': 'initializeOnly', 'inputOutput': 'inputOutput',
    'inputOnly': 'inputOnly', 'outputOnly': 'outputOnly',
}
VRML97_ACCESS_TYPES = {
    'field': 'initializeOnly', 'exposedField': 'inputOutput',
    'eventIn': 'inputOnly', 'eventOut': 'outputOnly',
}
STATEMENT_WORDS = frozenset((
    'PROTO', 'EXTERNPROTO', 'ROUTE', 'IMPORT', 'EXPORT', 'PROFILE', 'COMPONENT',
    'UNIT', 'META',
))
WORDS = frozenset(('TRUE', 'FALSE', 'true', 'false'))


class ClassicSyntaxError(ValueError):
    """Text the grammar does not allow"""

    def __init__(self, message: str, position: int) -> None:
        super().__init__(message)
        self.position = position


class _Token:
    __slots__ = ('kind', 'text', 'start', 'end')

    def __init__(self, kind: str, text: str, start: int, end: int) -> None:
        self.kind = kind
        self.text = text
        self.start = start
        self.end = end

    def __repr__(self) -> str:
        return '%s %r' % (self.kind, self.text)


class ClassicReader:
    """Reads ClassicVRML or VRML97 text into builder calls"""

    def __init__(self, builder: SceneBuilder, text: str) -> None:
        self.builder = builder
        self.text = text
        self.position = 0
        self.peeked: "_Token | None" = None
        self.vrml97 = False
        self._line_position = 0
        self._line = 1

    # Positions and tokens

    def _where(self, position: int) -> None:
        """Tell the builder the line and column of `position`"""
        if position < self._line_position:
            self._line_position, self._line = 0, 1
        self._line += self.text.count('\n', self._line_position, position)
        self._line_position = position
        self.builder.line = self._line
        self.builder.column = position - self.text.rfind('\n', 0, position)

    def peek(self) -> "_Token | None":
        if self.peeked is None:
            self.peeked = self._scan()
        return self.peeked

    def next(self) -> _Token:
        token = self.peek()
        if token is None:
            raise ClassicSyntaxError('Unexpected end of text', len(self.text))
        self.peeked = None
        return token

    def _scan(self) -> "_Token | None":
        text = self.text
        while self.position < len(text):
            match = TOKEN.match(text, self.position)
            if match is None:
                if text.startswith('#/*', self.position):
                    raise ClassicSyntaxError('Block comment is not closed', self.position)
                raise ClassicSyntaxError('Unexpected character %r' % text[self.position],
                                         self.position)
            self.position = match.end()
            kind = match.lastgroup or ''
            if kind in ('space', 'block', 'comment'):
                continue
            return _Token(kind, match.group(), match.start(), match.end())
        return None

    def expect(self, text: str) -> _Token:
        token = self.next()
        if token.text != text:
            raise ClassicSyntaxError('Expected %r, found %r' % (text, token.text), token.start)
        return token

    def identifier(self) -> _Token:
        token = self.next()
        if token.kind != 'id':
            raise ClassicSyntaxError('Expected a name, found %r' % token.text, token.start)
        return token

    def node_name(self) -> str:
        """A DEF or USE name

        ClassicVRML names cannot hold a full stop, but XML IDs can, and
        converted documents carry them over: `brick.jpg` is read as one name,
        with a warning.
        """
        token = self.identifier()
        name = token.text
        while self.position < len(self.text) and self.text[self.position] == '.':
            follow = TOKEN.match(self.text, self.position + 1)
            if follow is None or follow.lastgroup not in ('id', 'number'):
                break
            name += '.' + follow.group()
            self.position = follow.end()
            self.peeked = None
        if name != token.text:
            self._where(token.start)
            self.builder.problem('warning', 'Name %r holds a full stop' % name)
        return name

    def at(self, text: str) -> bool:
        token = self.peek()
        return token is not None and token.text == text

    # The document

    def read(self) -> X3DScene:
        try:
            self._header()
            while self.peek() is not None:
                self._statement()
        except ClassicSyntaxError as error:
            self._where(error.position)
            self.builder.problem('error', 'ClassicVRML: %s' % error)
            return self.builder.end_document(complete=False)
        return self.builder.end_document()

    def _header(self) -> None:
        match = HEADER.match(self.text)
        if match is None:
            self._where(0)
            self.builder.problem('error', 'No #X3D or #VRML header')
            return
        self.vrml97 = match.group(1) == 'VRML'
        self.position = match.end()
        self.builder.document('', match.group(2))

    def _statement(self) -> None:
        token = self.peek()
        assert token is not None
        word = token.text
        if word == 'PROFILE':
            self.next()
            name = self.identifier()
            self._where(name.start)
            self.builder.document(name.text, self.builder.scene.version)
        elif word == 'COMPONENT':
            self._component()
        elif word == 'UNIT':
            self.next()
            category = self.identifier()
            name = self.identifier()
            factor = self.next()
            self._where(category.start)
            try:
                self.builder.unit(category.text, name.text, float(factor.text))
            except ValueError:
                raise ClassicSyntaxError('UNIT conversion factor %r' % factor.text,
                                         factor.start) from None
        elif word == 'META':
            self.next()
            key = self._string()
            value = self._string()
            self.builder.meta(key, value)
        elif word in ('PROTO', 'EXTERNPROTO'):
            self._proto()
        elif word == 'ROUTE':
            self._route()
        elif word == 'IMPORT':
            self._import()
        elif word == 'EXPORT':
            self._export()
        else:
            self._node_statement()

    def _component(self) -> None:
        self.next()
        name = self.identifier()
        text = name.text
        if ':' in text:
            component, _colon, level = text.partition(':')
            if not level:
                level = self.next().text
        else:
            self.expect(':')
            component, level = text, self.next().text
        self._where(name.start)
        try:
            self.builder.component(component, int(level))
        except ValueError:
            raise ClassicSyntaxError('COMPONENT level %r' % level, name.start) from None

    def _string(self) -> str:
        token = self.next()
        if token.kind != 'string':
            raise ClassicSyntaxError('Expected a string, found %r' % token.text, token.start)
        return codecs.decode('MFString', token.text)[0]

    def _route(self) -> None:
        start = self.next().start
        source = self.identifier().text
        self.expect('.')
        source_field = self.identifier().text
        self.expect('TO')
        destination = self.identifier().text
        self.expect('.')
        destination_field = self.identifier().text
        self._where(start)
        self.builder.route(source, source_field, destination, destination_field)

    def _import(self) -> None:
        start = self.next().start
        inline = self.identifier().text
        self.expect('.')
        exported = self.identifier().text
        local = ''
        if self.at('AS'):
            self.next()
            local = self.identifier().text
        self._where(start)
        self.builder.import_(inline, exported, local)

    def _export(self) -> None:
        start = self.next().start
        local = self.identifier().text
        name = ''
        if self.at('AS'):
            self.next()
            name = self.identifier().text
        self._where(start)
        self.builder.export(local, name)

    # Prototypes and declarations

    def _access(self, token: _Token) -> "str | None":
        if token.text in ACCESS_TYPES:
            return ACCESS_TYPES[token.text]
        if token.text in VRML97_ACCESS_TYPES:
            if not self.vrml97:
                self._where(token.start)
                self.builder.problem(
                    'error' if self.builder.strict else 'warning',
                    'VRML97 declaration word %r in an X3D file' % token.text)
            return VRML97_ACCESS_TYPES[token.text]
        return None

    def _proto(self) -> None:
        keyword = self.next()
        extern = keyword.text == 'EXTERNPROTO'
        name = self.identifier()
        self._where(name.start)
        self.builder.start_proto(name.text, extern=extern)
        self.expect('[')
        while not self.at(']'):
            self._declaration(proto=True, values=not extern)
        self.expect(']')
        if extern:
            self.builder.proto_url(self._url_list())
        else:
            self.expect('{')
            self.builder.start_proto_body()
            while not self.at('}'):
                self._statement()
            self.expect('}')
            self.builder.end_proto_body()
        self.builder.end_proto()

    def _url_list(self) -> "list[str]":
        if self.at('['):
            self.next()
            urls = []
            while not self.at(']'):
                urls.append(self._string())
            self.next()
            return urls
        return [self._string()]

    def _declaration(self, proto: bool, values: bool) -> None:
        """A field declaration of a prototype's interface, or of a Script or shader"""
        word = self.next()
        access = self._access(word)
        if access is None:
            raise ClassicSyntaxError('Expected a field declaration, found %r' % word.text,
                                     word.start)
        type_name = self.identifier().text
        name = self.identifier()
        self._where(name.start)
        holds_value = values and access in ('initializeOnly', 'inputOutput')
        if not proto and self.at('IS'):
            self.builder.declare_field(name.text, type_name, access)
            self.next()
            self.builder.connect(name.text, self.identifier().text)
            return
        if not holds_value:
            if proto:
                self.builder.proto_field(name.text, type_name, access)
            else:
                self.builder.declare_field(name.text, type_name, access)
            return
        if type_name in ('SFNode', 'MFNode'):
            if proto:
                self.builder.proto_field(name.text, type_name, access)
                self.builder.start_proto_field_nodes(name.text)
                self._nodes(type_name)
                self.builder.end_proto_field_nodes()
            else:
                self.builder.declare_field(name.text, type_name, access)
                self.builder.start_field(name.text)
                self._nodes(type_name)
                self.builder.end_field()
            return
        kind, payload = self._value(type_name)
        if proto:
            if kind == 'text':
                self.builder.proto_field(name.text, type_name, access, text=payload)
            else:
                self.builder.proto_field(name.text, type_name, access, value=payload)
        elif kind == 'text':
            self.builder.declare_field(name.text, type_name, access, text=payload)
        else:
            self.builder.declare_field(name.text, type_name, access, value=payload)

    # Nodes

    def _node_statement(self, containerField: str = '') -> None:
        token = self.next()
        if token.text == 'USE':
            name = self.node_name()
            self._where(token.start)
            self.builder.start_node('', USE=name, containerField=containerField)
            self.builder.end_node()
            return
        DEF = ''
        if token.text == 'DEF':
            DEF = self.node_name()
            token = self.identifier()
        if token.kind != 'id':
            raise ClassicSyntaxError('Expected a node, found %r' % token.text, token.start)
        self._where(token.start)
        self.builder.start_node(token.text, DEF=DEF, containerField=containerField)
        self.expect('{')
        while not self.at('}'):
            self._body_element()
        self.next()
        self.builder.end_node()

    def _body_element(self) -> None:
        token = self.peek()
        assert token is not None
        if token.kind != 'id':
            raise ClassicSyntaxError('Expected a field name, found %r' % token.text, token.start)
        if token.text in ACCESS_TYPES or token.text in VRML97_ACCESS_TYPES:
            self._declaration(proto=False, values=True)
            return
        if token.text in ('PROTO', 'EXTERNPROTO'):
            self._proto()
            return
        if token.text == 'ROUTE':
            self._route()
            return
        self.next()
        name = token.text
        if self.at('IS'):
            self.next()
            self._where(token.start)
            self.builder.connect(name, self.identifier().text)
            return
        self._where(token.start)
        type_name = self.builder.field_type(name)
        if type_name is None:
            if self.builder.current_node() is not None:
                self.builder.problem('warning', '%s has no field %s' % (
                    type(self.builder.current_node()).__name__, name))
            self._skip_value()
            return
        if type_name in ('SFNode', 'MFNode'):
            if self.at('NULL'):
                self.next()
                self.builder.field(name, None)
                return
            self.builder.start_field(name)
            self._nodes(type_name)
            self.builder.end_field()
            return
        kind, payload = self._value(type_name)
        if kind == 'text':
            self.builder.field_text(name, payload)
        else:
            self.builder.field(name, payload)

    def _nodes(self, type_name: str) -> None:
        """A node-valued field's nodes, into the field the builder has open"""
        if self.at('NULL'):
            self.next()
            return
        if type_name == 'MFNode' and self.at('['):
            self.next()
            while not self.at(']'):
                token = self.peek()
                assert token is not None
                if token.text in ('PROTO', 'EXTERNPROTO', 'ROUTE'):
                    # Not part of a node list in the grammar; converted
                    # documents put them there.
                    self._where(token.start)
                    self.builder.problem('warning', '%s statement inside a list of nodes'
                                         % token.text)
                    self._statement()
                    continue
                self._node_statement()
            self.next()
            return
        self._node_statement()

    def _value(self, type_name: str) -> "tuple[str, Any]":
        """A non-node value: ('text', XML-style text) or ('value', strings)"""
        if type_name == 'SFString':
            return 'value', self._string()
        if type_name == 'MFString':
            if self.at('['):
                self.next()
                strings = []
                while not self.at(']'):
                    strings.append(self._string())
                self.next()
                return 'value', strings
            return 'value', [self._string()]
        if type_name.startswith('MF') and self.at('['):
            return 'text', self._bracketed()
        count = codecs.TUPLE_SIZE.get(type_name, 1)
        if type_name == 'SFImage':
            header = [self._scalar() for _ in range(3)]
            try:
                count = int(header[0], 0) * int(header[1], 0)
            except ValueError:
                raise ClassicSyntaxError('SFImage header %r' % header, self.position) from None
            return 'text', ' '.join(header + [self._scalar() for _ in range(count)])
        if type_name == 'MFImage':
            return 'text', self._bracketed()
        return 'text', ' '.join(self._scalar() for _ in range(count))

    def _scalar(self) -> str:
        token = self.next()
        if token.kind == 'number' or token.text in WORDS:
            return token.text
        raise ClassicSyntaxError('Expected a value, found %r' % token.text, token.start)

    def _bracketed(self) -> str:
        """The text between `[` and `]`, without comments"""
        self.expect('[')
        start = self.position
        match = NUMBERS.match(self.text, start)
        assert match is not None
        end = match.end()
        if end < len(self.text) and self.text[end] == ']':
            self.position = end + 1
            return self.text[start:end]
        parts = []
        while not self.at(']'):
            token = self.next()
            if token.kind not in ('number', 'id', 'string'):
                raise ClassicSyntaxError('Unexpected %r in a list' % token.text, token.start)
            parts.append(token.text)
        self.next()
        return ' '.join(parts)

    def _skip_value(self) -> None:
        """Pass over the value of a field nothing here knows the type of"""
        token = self.peek()
        if token is None:
            return
        if token.text == '[':
            depth = 0
            while True:
                token = self.next()
                if token.text in ('[', '{'):
                    depth += 1
                elif token.text in (']', '}'):
                    depth -= 1
                    if depth == 0:
                        return
        if token.text in ('USE', 'DEF', 'NULL'):
            self.next()
            if token.text != 'NULL':
                self.identifier()
                if token.text == 'DEF':
                    self._skip_node()
            return
        if token.kind == 'id' and token.text not in WORDS:
            self.next()
            if self.at('{'):
                self._skip_node(started=True)
            return
        while True:
            token = self.peek()
            if token is None or not (token.kind in ('number', 'string') or token.text in WORDS):
                return
            self.next()

    def _skip_node(self, started: bool = False) -> None:
        if not started:
            self.identifier()
        self.expect('{')
        depth = 1
        while depth:
            token = self.next()
            if token.text == '{':
                depth += 1
            elif token.text == '}':
                depth -= 1


def read(data: bytes, builder: SceneBuilder) -> X3DScene:
    """The scene a ClassicVRML or VRML97 document builds"""
    return ClassicReader(builder, data.decode('utf-8-sig', errors='replace')).read()
