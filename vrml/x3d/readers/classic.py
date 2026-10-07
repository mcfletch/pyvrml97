"""The ClassicVRML encoding (ISO/IEC 19776-2) and VRML97 (ISO/IEC 14772-1)

One SimpleParse grammar for both: the first line says which (`#X3D V4.0
utf8` or `#VRML V2.0 utf8`), and the VRML97 dialect applies to the second.
The grammar finds a document's structure; a field's value is reported as one
span, which the processor decodes by the type of the field it is for, so a
list of numbers is converted by the field's codec in one step rather than
number by number.

A file with an X3D header that declares fields with VRML97's words
(`field`, `exposedField`, `eventIn`, `eventOut`) is read with a warning,
which is an error in strict mode. What Web3D's converter writes outside the
grammar (a DEF name with a full stop, a prototype inside a list of nodes) is
read with a warning.
"""

import re
from typing import Any

from simpleparse.common import chartypes  # noqa: F401 registers EOF, which the grammar names
from simpleparse.error import ParserSyntaxError
from simpleparse.parser import Parser

from vrml.x3d import codecs
from vrml.x3d.builder import SceneBuilder
from vrml.x3d.scene import X3DScene

GRAMMAR = r'''
classicFile    := header?, statements, ts, EOF
header         := '#', headerKind, [ \t]+, 'V'?, version, -[\n]*
headerKind     := 'VRML' / 'X3D'
version        := [0-9]+, '.', [0-9]+

statements     := (ts, statement)*
>statement<    := profile / component / unit / meta / proto / externProto / route
                / import / export / nodeStatement

profile        := 'PROFILE', ws, !, id
component      := 'COMPONENT', ws, !, componentName, ts, ':', ts, integer
componentName  := -[: \t\r\n,]+
unit           := 'UNIT', ws, !, id, ws, id, ws, factor
factor         := number
meta           := 'META', ts, !, string, ts, string
route          := 'ROUTE', ws, !, id, '.', id, ws, 'TO', ws, id, '.', id
import         := 'IMPORT', ws, !, id, '.', id, (ws, 'AS', ws, id)?
export         := 'EXPORT', ws, !, id, (ws, 'AS', ws, id)?

proto          := 'PROTO', ws, !, id, ts, '[', declarations, ts, ']', ts,
                  '{', protoBody, ts, '}'
protoBody      := statements
externProto    := 'EXTERNPROTO', ws, !, id, ts, '[', declarations, ts, ']', ts, urls
urls           := listValue / string
declarations   := (ts, declaration)*
declaration    := accessType, ws, !, id, ws, id, (ts, isTarget)?, (ts, value)?
isTarget       := 'IS', ws, id
accessType     := ('initializeOnly' / 'inputOutput' / 'inputOnly' / 'outputOnly'
                / 'exposedField' / 'field' / 'eventIn' / 'eventOut'), ?(delimiter / EOF)

>nodeStatement< := defNode / useNode / node
defNode        := 'DEF', ws, !, nodeName, ws, node
useNode        := 'USE', ws, !, nodeName
node           := id, ts, '{', nodeBody, ts, '}'!
nodeBody       := (ts, bodyElement)*
>bodyElement<  := declaration / proto / externProto / route / connect / fieldValue
connect        := id, ws, 'IS', ?(delimiter / EOF), ws, !, id
fieldValue     := id, ts, value

>value<        := listValue / null / nodeStatement / scalars
null           := 'NULL', ?(delimiter / EOF)
listValue      := '[', ts, (scalarList / nodeList), ts, ']'!
scalarList     := scalar, (ts, scalar)*
nodeList       := (ts, listItem)*
>listItem<     := proto / externProto / route / nodeStatement
scalars        := scalar, (ts, scalar)*
<scalar>       := number / string / (word, ?(delimiter / EOF))
<word>         := 'TRUE' / 'FALSE' / 'true' / 'false'

nodeName       := id, ('.', idRest+)*
id             := idFirst, idRest*
<idFirst>      := -[][{}\000-\040"'#,.\\:+0-9\177-]
<idRest>       := -[][{}\000-\040"'#,.\\\177]
<delimiter>    := [][{}\000-\040"'#,.\\\177]
<number>       := [-+]?, (hexadecimal / decimal)
<hexadecimal>  := '0', [xX], [0-9a-fA-F]+
<decimal>      := (([0-9]+, ('.', [0-9]*)?) / ('.', [0-9]+)), ([eE], [-+]?, [0-9]+)?
integer        := [-+]?, [0-9]+
string         := '"', (-[\\"] / ('\\', -[\000]))*, '"'
<ws>           := ([ \t\r\n,] / comment)+
<ts>           := ([ \t\r\n,] / comment)*
<comment>      := ('#/*', -'*/#'*, '*/#') / ('#', -[\n]*)
'''


PARSER = Parser(GRAMMAR, 'classicFile')

ACCESS_TYPES = {
    'initializeOnly': 'initializeOnly', 'inputOutput': 'inputOutput',
    'inputOnly': 'inputOnly', 'outputOnly': 'outputOnly',
}
VRML97_ACCESS_TYPES = {
    'field': 'initializeOnly', 'exposedField': 'inputOutput',
    'eventIn': 'inputOnly', 'eventOut': 'outputOnly',
}

#: A comment inside a span of values, outside the strings there.
COMMENT = re.compile(r'"(?:[^"\\]|\\.)*"|#/\*.*?\*/#|#[^\n]*', re.DOTALL)


class ClassicReader:
    """Turns a ClassicVRML or VRML97 parse tree into builder calls"""

    def __init__(self, builder: SceneBuilder, text: str) -> None:
        self.builder = builder
        self.text = text
        self.vrml97 = False
        self._line_position = 0
        self._line = 1

    def _where(self, position: int) -> None:
        """Tell the builder the line and column of `position`"""
        if position < self._line_position:
            self._line_position, self._line = 0, 1
        self._line += self.text.count('\n', self._line_position, position)
        self._line_position = position
        self.builder.line = self._line
        self.builder.column = position - self.text.rfind('\n', 0, position)

    def _text(self, production: Any) -> str:
        return self.text[production[1]:production[2]]

    def read(self) -> X3DScene:
        try:
            success, children, end = PARSER.parse(self.text)
        except ParserSyntaxError as error:
            position = error.position or 0
            self._where(position)
            expected = ' (expected %s)' % error.expected if error.expected else ''
            self.builder.problem('error', 'ClassicVRML: %s%s' % (self._describe(position), expected))
            return self.builder.end_document(complete=False)
        if not success:
            self._where(end)
            self.builder.problem('error', 'ClassicVRML: %s' % self._describe(end))
            return self.builder.end_document(complete=False)
        if not children or children[0][0] != 'header':
            self._where(0)
            self.builder.problem('error', 'No #X3D or #VRML header')
        for production in children:
            if production[0] != 'EOF':
                getattr(self, '_' + production[0])(production)
        return self.builder.end_document()

    def _describe(self, position: int) -> str:
        found = self.text[position:position + 20].split('\n')[0]
        return 'cannot read %r' % found if found else 'unexpected end of text'

    # Statements

    def _header(self, production: Any) -> None:
        kind, version = production[3]
        self.vrml97 = self._text(kind) == 'VRML'
        self.builder.document('', self._text(version))

    def _statements(self, production: Any) -> None:
        for statement in production[3]:
            self._where(statement[1])
            getattr(self, '_' + statement[0])(statement)

    def _profile(self, production: Any) -> None:
        self.builder.document(self._text(production[3][0]), self.builder.scene.version)

    def _component(self, production: Any) -> None:
        name, level = production[3]
        self.builder.component(self._text(name), int(self._text(level)))

    def _unit(self, production: Any) -> None:
        category, name, factor = production[3]
        self.builder.unit(self._text(category), self._text(name), float(self._text(factor)))

    def _meta(self, production: Any) -> None:
        key, value = (codecs.decode('MFString', self._text(item))[0] for item in production[3])
        self.builder.meta(key, value)

    def _route(self, production: Any) -> None:
        names = [self._text(item) for item in production[3]]
        self.builder.route(*names)

    def _import(self, production: Any) -> None:
        names = [self._text(item) for item in production[3]]
        self.builder.import_(names[0], names[1], names[2] if len(names) > 2 else '')

    def _export(self, production: Any) -> None:
        names = [self._text(item) for item in production[3]]
        self.builder.export(names[0], names[1] if len(names) > 1 else '')

    # Prototypes and declarations

    def _proto(self, production: Any) -> None:
        name, declarations, body = production[3]
        self.builder.start_proto(self._text(name))
        for declaration in declarations[3]:
            self._declaration(declaration, proto=True)
        self.builder.start_proto_body()
        self._statements(body[3][0])
        self.builder.end_proto_body()
        self.builder.end_proto()

    def _externProto(self, production: Any) -> None:
        name, declarations, urls = production[3]
        self.builder.start_proto(self._text(name), extern=True)
        for declaration in declarations[3]:
            self._declaration(declaration, proto=True)
        self.builder.proto_url(codecs.decode('MFString', self._span(urls[3][0])))
        self.builder.end_proto()

    def _access(self, production: Any) -> str:
        word = self._text(production)
        if word in VRML97_ACCESS_TYPES:
            if not self.vrml97:
                self._where(production[1])
                self.builder.problem(
                    'error' if self.builder.strict else 'warning',
                    'VRML97 declaration word %r in an X3D file' % word)
            return VRML97_ACCESS_TYPES[word]
        return ACCESS_TYPES[word]

    def _declaration(self, production: Any, proto: bool = False) -> None:
        """A field declaration of a prototype's interface, or of a Script or shader"""
        self._where(production[1])
        access_production, type_production, name_production, *rest = production[3]
        access = self._access(access_production)
        type_name = self._text(type_production)
        name = self._text(name_production)
        target = next((item for item in rest if item[0] == 'isTarget'), None)
        value = next((item for item in rest if item[0] != 'isTarget'), None)
        declare = self.builder.proto_field if proto else self.builder.declare_field
        if target is not None:
            declare(name, type_name, access)
            self.builder.connect(name, self._text(target[3][0]))
            return
        if value is None:
            declare(name, type_name, access)
            return
        if type_name in ('SFNode', 'MFNode'):
            declare(name, type_name, access)
            if proto:
                self.builder.start_proto_field_nodes(name)
            else:
                self.builder.start_field(name)
            self._nodes(value)
            if proto:
                self.builder.end_proto_field_nodes()
            else:
                self.builder.end_field()
            return
        kind, payload = self._decoded(type_name, value)
        if kind == 'text':
            declare(name, type_name, access, text=payload)
        else:
            declare(name, type_name, access, value=payload)

    # Nodes

    def _name(self, production: Any) -> str:
        name = self._text(production)
        if '.' in name:
            self._where(production[1])
            self.builder.problem('warning', 'Name %r holds a full stop' % name)
        return name

    def _useNode(self, production: Any, containerField: str = '') -> None:
        self._where(production[1])
        self.builder.start_node('', USE=self._name(production[3][0]),
                                containerField=containerField)
        self.builder.end_node()

    def _defNode(self, production: Any, containerField: str = '') -> None:
        name, built = production[3]
        self._node(built, containerField, self._name(name))

    def _node(self, production: Any, containerField: str = '', DEF: str = '') -> None:
        type_production, body = production[3]
        self._where(production[1])
        self.builder.start_node(self._text(type_production), DEF=DEF,
                                containerField=containerField)
        for element in body[3]:
            self._where(element[1])
            kind = element[0]
            if kind == 'fieldValue':
                self._field_value(element)
            elif kind == 'connect':
                field, target = element[3]
                self.builder.connect(self._text(field), self._text(target))
            elif kind == 'declaration':
                self._declaration(element)
            else:
                getattr(self, '_' + kind)(element)
        self.builder.end_node()

    def _field_value(self, production: Any) -> None:
        name_production, value = production[3]
        name = self._text(name_production)
        type_name = self.builder.field_type(name)
        if type_name is None:
            if self.builder.current_node() is not None:
                self.builder.problem('warning', '%s has no field %s' % (
                    type(self.builder.current_node()).__name__, name))
            return
        if type_name in ('SFNode', 'MFNode'):
            if value[0] == 'null':
                self.builder.field(name, None)
                return
            self.builder.start_field(name)
            self._nodes(value)
            self.builder.end_field()
            return
        kind, payload = self._decoded(type_name, value)
        if kind == 'text':
            self.builder.field_text(name, payload)
        else:
            self.builder.field(name, payload)

    def _nodes(self, value: Any) -> None:
        """A node-valued field's nodes, into the field the builder has open"""
        kind = value[0]
        if kind == 'null':
            return
        if kind == 'listValue':
            items = value[3][0]
            if items[0] == 'scalarList':
                self._where(items[1])
                self.builder.problem('error', 'Values where nodes belong: %r'
                                     % self._text(items)[:40])
                return
            for item in items[3]:
                if item[0] in ('proto', 'externProto', 'route'):
                    self._where(item[1])
                    self.builder.problem('warning', '%s statement inside a list of nodes'
                                         % self._text(item).split()[0])
                getattr(self, '_' + item[0])(item)
            return
        if kind in ('node', 'defNode', 'useNode'):
            getattr(self, '_' + kind)(value)
            return
        self._where(value[1])
        self.builder.problem('error', 'Values where a node belongs: %r' % self._text(value)[:40])

    def _span(self, value: Any) -> str:
        """The text of a value, without brackets or comments"""
        if value[0] == 'listValue':
            inner = value[3][0] if value[3] else None
            text = self._text(inner) if inner is not None and inner[0] == 'scalarList' else ''
        else:
            text = self._text(value)
        if '#' in text:
            text = COMMENT.sub(lambda match: match.group() if match.group().startswith('"')
                               else ' ', text)
        return text

    def _decoded(self, type_name: str, value: Any) -> "tuple[str, Any]":
        """A non-node value: ('text', XML-style text) or ('value', strings)"""
        if value[0] in ('null', 'node', 'defNode', 'useNode') or (
                value[0] == 'listValue' and value[3] and value[3][0][0] == 'nodeList'
                and value[3][0][3]):
            self._where(value[1])
            self.builder.problem('error', 'A node where a %s value belongs: %r'
                                 % (type_name, self._text(value)[:40]))
            return 'text', ''
        text = self._span(value)
        if type_name == 'SFString':
            strings = codecs.decode('MFString', text)
            return 'value', strings[0] if strings else ''
        if type_name == 'MFString':
            return 'value', codecs.decode('MFString', text)
        return 'text', text


def read(data: bytes, builder: SceneBuilder) -> X3DScene:
    """The scene a ClassicVRML or VRML97 document builds"""
    return ClassicReader(builder, data.decode('utf-8-sig', errors='replace')).read()
