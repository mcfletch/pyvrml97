"""The X3D XML encoding (ISO/IEC 19776-1)

Attributes are written in X3D canonical form's order (ISO/IEC 19776-3,
4.2.3): `DEF`, `USE` and a `containerField` the reader would not infer, then
the rest alphabetically. An MFString attribute is delimited by single quotes,
every other by double quotes. Program source is written as CDATA.
`canonical=True` adds the DTD and the schema attributes the canonical form
names. Within a value, an apostrophe is written `&apos;`, which reads back as
the same character, where the canonical form gives `&#8242;`, which does not.
"""

import re
from typing import Any

from vrml import node, protofunctions
from vrml.x3d import codecs
from vrml.x3d.scene import X3DScene
from vrml.x3d.writers.base import NODE_TYPES, Declaration, SceneWriter, Value

DOCTYPE = ('<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D %(version)s//EN" '
           '"https://www.web3d.org/specifications/x3d-%(version)s.dtd">')
SCHEMA_ATTRIBUTES = (
    ('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema-instance'),
    ('xsd:noNamespaceSchemaLocation', 'https://www.web3d.org/specifications/x3d-%s.xsd'),
)
INDENT = '  '

_ESCAPES = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '\n': '&#10;', '\r': '&#13;', '\t': '&#9;'}
#: The characters XML 1.0 has no form for, escaped or not, once tab, newline
#: and carriage return are written as references.
UNWRITABLE = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff\ud800-\udfff]')


def attribute(name: str, text: str, quote: str = '"') -> str:
    """An XML attribute ` name="text"`, escaped for the given quote character"""
    escaped = ''.join(_ESCAPES.get(character, character) for character in text)
    escaped = escaped.replace(quote, '&quot;' if quote == '"' else '&apos;')
    return ' %s=%s%s%s' % (name, quote, escaped, quote)


def cdata(text: str) -> str:
    """Program text wrapped in CDATA sections"""
    return '<![CDATA[%s]]>' % text.replace(']]>', ']]]]><![CDATA[>')


class XMLWriter(SceneWriter):
    """Writes a scene as an X3D XML document"""

    encoding = 'xml'

    def document(self) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        if self.canonical:
            lines.append(DOCTYPE % {'version': self.version})
        root = attribute('profile', self.profile) + attribute('version', self.version)
        if self.canonical:
            root += ''.join(attribute(name, value % self.version if '%' in value else value)
                            for name, value in SCHEMA_ATTRIBUTES)
        lines.append('<X3D%s>' % root)
        self.out: "list[str]" = []
        self.enter(self.scene)
        self.graph(self.scene, 2)
        for inlineDEF, importedDEF, AS in self.imports():
            self.element(2, 'IMPORT', [('AS', AS), ('importedDEF', importedDEF),
                                       ('inlineDEF', inlineDEF)])
        for localDEF, AS in self.exports():
            self.element(2, 'EXPORT', [('AS', AS), ('localDEF', localDEF)])
        self.route_elements(self.scene, 2)
        self.leave()
        head = self.head()
        if head:
            lines.append(INDENT + '<head>')
            lines.extend(INDENT * 2 + line for line in head)
            lines.append(INDENT + '</head>')
        if self.out:
            lines.append(INDENT + '<Scene>')
            lines.extend(self.out)
            lines.append(INDENT + '</Scene>')
        else:
            lines.append(INDENT + '<Scene/>')
        lines.append('</X3D>')
        text = '\n'.join(lines) + '\n'
        for found in UNWRITABLE.finditer(text):
            line = text.count('\n', 0, found.start()) + 1
            self.problem('%r, on line %d, is a character XML 1.0 cannot carry: %s'
                         % (found.group(), line, text.splitlines()[line - 1].strip()[:60]))
        return text

    def head(self) -> "list[str]":
        found = []
        for name, level in self.components():
            found.append('<component%s/>' % (attribute('level', str(level))
                                             + attribute('name', name)))
        if self.writes_units:
            for item in self.scene.units:
                found.append('<unit%s/>' % (
                    attribute('category', item.category)
                    + attribute('conversionFactor', codecs.encode('SFDouble', item.conversionFactor))
                    + attribute('name', item.name)))
        for item in self.scene.meta:
            pairs = [('content', item.content), ('dir', item.dir), ('http-equiv', item.httpEquiv),
                     ('lang', item.lang), ('name', item.name), ('scheme', item.scheme)]
            found.append('<meta%s/>' % ''.join(
                attribute(name, value) for name, value in pairs if value or name == 'content'))
        return found

    def element(self, depth: int, tag: str, pairs: "list[tuple[str, str]]") -> None:
        self.out.append('%s<%s%s/>' % (INDENT * depth, tag, ''.join(
            attribute(name, value) for name, value in pairs if value)))

    # Scenes and prototype bodies

    def graph(self, graph: Any, depth: int) -> None:
        """Write the prototypes and nodes of a scene or prototype body"""
        for proto in self._scopes[-1].protos:
            self.proto(proto, depth)
        for child in graph.children:
            self.node(child, depth)

    def route_elements(self, graph: Any, depth: int) -> None:
        for fromNode, fromField, toNode, toField in self.routes(graph):
            self.element(depth, 'ROUTE', [('fromField', fromField), ('fromNode', fromNode),
                                          ('toField', toField), ('toNode', toNode)])

    def proto(self, proto: type, depth: int) -> None:
        name = protofunctions.protoName(proto)
        indent = INDENT * depth
        urls = self.external_urls(proto)
        if urls:
            fields = self.interface(proto)
            opening = '%s<ExternProtoDeclare%s%s' % (
                indent, attribute('name', name),
                attribute('url', codecs.encode('MFString', urls), "'"))
            if not fields:
                self.out.append(opening + '/>')
                return
            self.out.append(opening + '>')
            for declared in fields:
                self.field_declaration(declared, depth + 1)
            self.out.append('%s</ExternProtoDeclare>' % indent)
            return
        self.out.append('%s<ProtoDeclare%s>' % (indent, attribute('name', name)))
        fields = self.interface(proto)
        if fields:
            self.out.append('%s<ProtoInterface>' % (indent + INDENT))
            for declared in fields:
                self.field_declaration(declared, depth + 2)
            self.out.append('%s</ProtoInterface>' % (indent + INDENT))
        graph = self.body(proto)
        if graph is not None:
            self.out.append('%s<ProtoBody>' % (indent + INDENT))
            self.graph(graph, depth + 2)
            self.route_elements(graph, depth + 2)
            self.leave()
            self.out.append('%s</ProtoBody>' % (indent + INDENT))
        self.out.append('%s</ProtoDeclare>' % indent)

    def field_declaration(self, declared: Declaration, depth: int) -> None:
        indent = INDENT * depth
        pairs = attribute('accessType', declared.accessType) + attribute(
            'name', declared.name) + attribute('type', declared.type_name)
        nodes = self._declared_nodes(declared)
        if declared.value is not None and declared.type_name not in NODE_TYPES:
            pairs += self.value_attribute('value', declared.type_name, declared.value)
        if not nodes:
            self.out.append('%s<field%s/>' % (indent, pairs))
            return
        self.out.append('%s<field%s>' % (indent, pairs))
        for child in nodes:
            self.node(child, depth + 1)
        self.out.append('%s</field>' % indent)

    @staticmethod
    def _declared_nodes(declared: Declaration) -> "list[Any]":
        if declared.type_name == 'MFNode':
            return list(declared.value or [])
        if declared.type_name == 'SFNode' and declared.value:
            return [declared.value]
        return []

    def value_attribute(self, name: str, type_name: str, value: Any) -> str:
        quote = "'" if type_name == 'MFString' else '"'
        return attribute(name, codecs.encode(type_name, value), quote)

    # Nodes

    def node(self, target: Any, depth: int, parent: Any = None, field_name: str = '') -> None:
        target = self.written_as(target)
        indent = INDENT * depth
        type_name, prototype = self.type_of(target)
        name, use = self.reference(target)
        tag = 'ProtoInstance' if prototype else type_name
        start = ''
        if name:
            start += attribute('USE' if use else 'DEF', name)
        if parent is not None and not self.implied_container(parent, target, field_name):
            written = field_name if isinstance(parent, node.PrototypedNode) else (
                self.dialect.dialect_name(protofunctions.protoName(parent), field_name))
            start += attribute('containerField', written)
        if prototype:
            start += attribute('name', type_name)
        if use:
            self.out.append('%s<%s%s/>' % (indent, tag, start))
            return
        self.opened(target)
        content: "list[str]" = []
        saved, self.out = self.out, content
        # Declared fields come first: an IS connection names one of them.
        for declared in self.own_declarations(target):
            self.field_declaration(declared, depth + 1)
        # A prototype instance's field values come before its IS, as the
        # schema's X3DPrototypeInstance orders them; a node's IS comes first.
        if prototype:
            for item in self.values(target) + self.node_fields(target):
                self.field_value(item, depth + 1)
        connections = self.connections(target)
        if connections:
            self.out.append('%s<IS>' % (indent + INDENT))
            for nodeField, protoField in connections:
                self.element(depth + 2, 'connect', [('nodeField', nodeField),
                                                     ('protoField', protoField)])
            self.out.append('%s</IS>' % (indent + INDENT))
        if not prototype:
            for item in self.values(target):
                start += self.value_attribute(item.name, item.type_name, item.value)
            # The schema puts a node's metadata before its other node fields.
            for item in sorted(self.node_fields(target), key=lambda item: item.name != 'metadata'):
                current = self.dialect.current_name(type_name, item.name)
                for child in self._children(item):
                    self.node(child, depth + 1, target, current)
        source = self.source(target).strip()
        self.out = saved
        self.closed(target)
        if not content and not source:
            self.out.append('%s<%s%s/>' % (indent, tag, start))
            return
        self.out.append('%s<%s%s>' % (indent, tag, start))
        self.out.extend(content)
        if source:
            self.out.append('%s%s' % (indent + INDENT, cdata('\n' + source + '\n')))
        self.out.append('%s</%s>' % (indent, tag))

    @staticmethod
    def _children(item: Value) -> "list[Any]":
        return list(item.value) if item.type_name == 'MFNode' else [item.value]

    def field_value(self, item: Value, depth: int) -> None:
        indent = INDENT * depth
        if item.type_name not in NODE_TYPES:
            self.out.append('%s<fieldValue%s%s/>' % (
                indent, attribute('name', item.name),
                self.value_attribute('value', item.type_name, item.value)))
            return
        self.out.append('%s<fieldValue%s>' % (indent, attribute('name', item.name)))
        for child in self._children(item):
            self.node(child, depth + 1)
        self.out.append('%s</fieldValue>' % indent)


def write(scene: X3DScene, version: "str | None" = None, canonical: bool = False) -> str:
    """Write a scene as an X3D XML document"""
    return XMLWriter(scene, version, canonical).write()
