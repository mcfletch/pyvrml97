"""The ClassicVRML encoding (ISO/IEC 19776-2) and VRML97 (ISO/IEC 14772-1)

VRML97 is version '2.0': its header, its access words (`field`,
`exposedField`, `eventIn`, `eventOut`) and no PROFILE, COMPONENT, UNIT or
META statements. A program's source goes in the `sourceCode` field where the
version has one, and first in the `url` field where it does not.
"""

import re
from typing import Any

from vrml import protofunctions
from vrml.x3d import codecs
from vrml.x3d.scene import X3DScene
from vrml.x3d.writers.base import NODE_TYPES, Declaration, SceneWriter

INDENT = '  '


def value_text(type_name: str, value: Any) -> str:
    """A field value in ClassicVRML syntax"""
    if type_name == 'SFBool':
        return 'TRUE' if value else 'FALSE'
    if type_name == 'MFBool':
        return '[ %s ]' % ' '.join('TRUE' if item else 'FALSE' for item in value) if len(
            value) else '[ ]'
    if type_name == 'SFString':
        return codecs.encode('MFString', [value])
    text = codecs.encode(type_name, value)
    if type_name.startswith('MF'):
        return '[ %s ]' % text if text else '[ ]'
    return text


class ClassicWriter(SceneWriter):
    """Writes a scene as a ClassicVRML or VRML97 document"""

    encoding = 'classic'
    #: A DEF name as the reader's grammar reads one: no space, control
    #: character or one of ``[]{}"'#,\`` anywhere, and not a digit, '.',
    #: '+', '-' or ':' first. The '.' later on is the reader's, not
    #: ClassicVRML's identifier; Web3D's translations write it.
    name_pattern = re.compile(r'''[^\][{}\x00-\x20"'#,.\\:+0-9\x7f-][^\][{}\x00-\x20"'#,\\\x7f]*\Z''')

    def document(self) -> str:
        self.out: "list[str]" = []
        if self.vrml97:
            self.out.append('#VRML V2.0 utf8')
            # VRML97 has no META statement: a comment keeps the text.
            for item in self.scene.meta:
                self.out.append('# META %s' % codecs.encode('MFString', [item.name, item.content]))
        else:
            self.out.append('#X3D V%s utf8' % self.version)
            self.out.append('PROFILE %s' % self.profile)
            components = len(self.out)
            if self.writes_units:
                for item in self.scene.units:
                    self.out.append('UNIT %s %s %s' % (
                        item.category, item.name,
                        codecs.encode('SFDouble', item.conversionFactor)))
            for item in self.scene.meta:
                self.out.append('META %s' % codecs.encode('MFString', [item.name, item.content]))
        self.out.append('')
        self.enter(self.scene)
        self.graph(self.scene, 0)
        for inlineDEF, importedDEF, AS in self.imports():
            self.out.append('IMPORT %s.%s%s' % (inlineDEF, importedDEF, ' AS ' + AS if AS else ''))
        for localDEF, AS in self.exports():
            self.out.append('EXPORT %s%s' % (localDEF, ' AS ' + AS if AS else ''))
        self.route_lines(self.scene, 0)
        self.leave()
        if not self.vrml97:
            self.out[components:components] = [
                'COMPONENT %s:%d' % (name, level) for name, level in self.components()]
        return '\n'.join(self.out) + '\n'

    # Scenes and prototype bodies

    def graph(self, graph: Any, depth: int) -> None:
        for proto in self._scopes[-1].protos:
            self.proto(proto, depth)
        for child in graph.children:
            self.out.append(INDENT * depth + self.node(child, depth))

    def route_lines(self, graph: Any, depth: int) -> None:
        for fromNode, fromField, toNode, toField in self.routes(graph):
            self.out.append('%sROUTE %s.%s TO %s.%s' % (
                INDENT * depth, fromNode, fromField, toNode, toField))

    def proto(self, proto: type, depth: int) -> None:
        indent = INDENT * depth
        name = protofunctions.protoName(proto)
        urls = self.external_urls(proto)
        fields = self.interface(proto)
        keyword = 'EXTERNPROTO' if urls else 'PROTO'
        if fields:
            self.out.append('%s%s %s [' % (indent, keyword, name))
            for declared in fields:
                self.out.append(indent + INDENT + self.declaration_text(declared, depth + 1))
            self.out.append(indent + ']')
        else:
            self.out.append('%s%s %s [ ]' % (indent, keyword, name))
        if urls:
            self.out.append(indent + value_text('MFString', urls))
            return
        self.out.append(indent + '{')
        graph = self.body(proto)
        if graph is not None:
            self.graph(graph, depth + 1)
            self.route_lines(graph, depth + 1)
            self.leave()
        self.out.append(indent + '}')

    def declaration_text(self, declared: Declaration, depth: int, connected: str = '') -> str:
        text = '%s %s %s' % (self.access_word(declared.accessType), declared.type_name,
                             declared.name)
        if connected:
            return '%s IS %s' % (text, connected)
        if declared.value is None:
            return text
        if declared.type_name in NODE_TYPES:
            return '%s %s' % (text, self.nodes_text(declared.type_name, declared.value, depth))
        return '%s %s' % (text, value_text(declared.type_name, declared.value))

    # Nodes

    def node(self, target: Any, depth: int) -> str:
        """The ClassicVRML text of a node, without leading indentation"""
        target = self.written_as(target)
        type_name, _prototype = self.type_of(target)
        name, use = self.reference(target)
        if use:
            return 'USE %s' % name
        self.opened(target)
        prefix = 'DEF %s ' % name if name else ''
        indent = INDENT * (depth + 1)
        lines = []
        connections = self.connections(target)
        for declared in self.own_declarations(target):
            # A declaration carries one IS; any further one is a statement of its own
            written = self.dialect.dialect_name(type_name, declared.name)
            first = next((pair for pair in connections if pair[0] == written), None)
            if first is not None:
                connections.remove(first)
            lines.append(self.declaration_text(declared, depth + 1, first[1] if first else ''))
        for nodeField, protoField in connections:
            lines.append('%s IS %s' % (nodeField, protoField))
        source = 'field' if self.dialect.has_field(type_name, 'sourceCode') else 'url'
        for item in self.values(target, source):
            lines.append('%s %s' % (item.name, value_text(item.type_name, item.value)))
        for item in self.node_fields(target):
            lines.append('%s %s' % (item.name, self.nodes_text(item.type_name, item.value,
                                                               depth + 1)))
        self.closed(target)
        if not lines:
            return '%s%s { }' % (prefix, type_name)
        body = '\n'.join(indent + line for line in lines)
        return '%s%s {\n%s\n%s}' % (prefix, type_name, body, INDENT * depth)

    def nodes_text(self, type_name: str, value: Any, depth: int) -> str:
        if type_name == 'SFNode':
            return self.node(value, depth) if value else 'NULL'
        if not len(value):
            return '[ ]'
        indent = INDENT * (depth + 1)
        items = '\n'.join(indent + self.node(child, depth + 1) for child in value)
        return '[\n%s\n%s]' % (items, INDENT * depth)


def write(scene: X3DScene, version: "str | None" = None, canonical: bool = False) -> str:
    """Write a scene as a ClassicVRML or VRML97 document"""
    return ClassicWriter(scene, version, canonical).write()
