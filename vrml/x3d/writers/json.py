"""Writer for the X3D JSON encoding

Follows Web3D's X3D JSON layout, which the JSON reader reads. A node is an
object with one key, its type. Field values are typed JSON values under
`@name` keys, node fields are under `-name` keys (an object for SFNode, a
list for MFNode), and program source is a list of lines under `#sourceCode`.
Numbers are written with the shortest text that reads back as the same
value at the field's precision.
"""

import json
from typing import Any

import numpy as np

from vrml import protofunctions
from vrml.x3d import codecs
from vrml.x3d.scene import X3DScene
from vrml.x3d.writers.base import NODE_TYPES, Declaration, SceneWriter

SCHEMA = 'https://www.web3d.org/specifications/x3d-%s.xsd'
JSON_SCHEMA = 'https://www.web3d.org/specifications/x3d-%s-JSONSchema.json'


def _number(value: Any) -> "int | float":
    """An integer as an int; a float as the shortest float that reads back the same"""
    if isinstance(value, (int, np.integer)):
        return int(value)
    return float(codecs.number_text(value))


def json_value(type_name: str, value: Any) -> Any:
    """A field value as a JSON-ready Python value"""
    if type_name in ('SFBool', 'SFString'):
        return bool(value) if type_name == 'SFBool' else str(value)
    if type_name == 'MFBool':
        return [bool(item) for item in value]
    if type_name == 'MFString':
        return [str(item) for item in value]
    if type_name == 'MFImage':
        return [int(item) for image in value for item in np.asarray(image).ravel()]
    if type_name in ('SFInt32', 'SFFloat', 'SFDouble', 'SFTime'):
        return _number(value)
    return [_number(item) for item in np.asarray(value).ravel()]


def text(value: Any, depth: int = 0) -> str:
    """`value` as JSON text indented by two spaces a level, as `json.dumps`
    indents it, except that a list of numbers and booleans is one line"""
    indent, inner = '  ' * depth, '  ' * (depth + 1)
    if isinstance(value, dict):
        if not value:
            return '{}'
        return '{\n%s\n%s}' % (',\n'.join(
            '%s%s: %s' % (inner, json.dumps(key, ensure_ascii=False), text(item, depth + 1))
            for key, item in value.items()), indent)
    if isinstance(value, list):
        if not value:
            return '[]'
        if all(isinstance(item, (int, float)) for item in value):
            return '[%s]' % ', '.join(json.dumps(item) for item in value)
        return '[\n%s\n%s]' % (',\n'.join(
            inner + text(item, depth + 1) for item in value), indent)
    return json.dumps(value, ensure_ascii=False)


class JSONWriter(SceneWriter):
    """Writes a scene as an X3D JSON document"""

    encoding = 'json'

    def document(self) -> str:
        top: "dict[str, Any]" = {
            'encoding': 'UTF-8',
            '@profile': self.profile,
            '@version': self.version,
            '@xsd:noNamespaceSchemaLocation': SCHEMA % self.version,
            'JSON schema': JSON_SCHEMA % self.version,
        }
        self.enter(self.scene)
        children = self.graph(self.scene)
        for inlineDEF, importedDEF, AS in self.imports():
            record = {'@inlineDEF': inlineDEF, '@importedDEF': importedDEF}
            if AS:
                record['@AS'] = AS
            children.append({'IMPORT': record})
        for localDEF, AS in self.exports():
            record = {'@localDEF': localDEF}
            if AS:
                record['@AS'] = AS
            children.append({'EXPORT': record})
        children.extend(self.route_objects(self.scene))
        self.leave()
        head = self.head()
        if head:
            top['head'] = head
        top['Scene'] = {'-children': children} if children else {}
        return text({'X3D': top}) + '\n'

    def head(self) -> "dict[str, Any]":
        head: "dict[str, Any]" = {}
        components = self.components()
        if components:
            head['component'] = [{'@name': name, '@level': level}
                                 for name, level in components]
        if self.writes_units and self.scene.units:
            head['unit'] = [{'@category': item.category, '@name': item.name,
                             '@conversionFactor': _number(item.conversionFactor)}
                            for item in self.scene.units]
        if self.scene.meta:
            head['meta'] = []
            for item in self.scene.meta:
                record = {}
                for key, value in (('name', item.name), ('content', item.content),
                                   ('dir', item.dir), ('http-equiv', item.httpEquiv),
                                   ('lang', item.lang), ('scheme', item.scheme)):
                    if value or key == 'content':
                        record['@' + key] = value
                head['meta'].append(record)
        return head

    # Scenes and prototype bodies

    def graph(self, graph: Any) -> "list[Any]":
        """The prototypes and nodes of a scene or prototype body, as JSON objects"""
        found = [self.proto(proto) for proto in self._scopes[-1].protos]
        found.extend(self.node(child) for child in graph.children)
        return found

    def route_objects(self, graph: Any) -> "list[Any]":
        return [{'ROUTE': {'@fromNode': fromNode, '@fromField': fromField,
                           '@toNode': toNode, '@toField': toField}}
                for fromNode, fromField, toNode, toField in self.routes(graph)]

    def proto(self, proto: type) -> "dict[str, Any]":
        name = protofunctions.protoName(proto)
        urls = self.external_urls(proto)
        fields = [self.declaration_object(item) for item in self.interface(proto)]
        if urls:
            record: "dict[str, Any]" = {'@name': name, '@url': urls}
            if fields:
                record['field'] = fields
            return {'ExternProtoDeclare': record}
        record = {'@name': name}
        if fields:
            record['ProtoInterface'] = {'field': fields}
        graph = self.body(proto)
        body: "list[Any]" = []
        if graph is not None:
            body = self.graph(graph) + self.route_objects(graph)
            self.leave()
        record['ProtoBody'] = {'-children': body}
        return {'ProtoDeclare': record}

    def declaration_object(self, declared: Declaration) -> "dict[str, Any]":
        record: "dict[str, Any]" = {'@name': declared.name, '@accessType': declared.accessType,
                                    '@type': declared.type_name}
        if declared.value is None:
            return record
        if declared.type_name in NODE_TYPES:
            nodes = self._nodes(declared.type_name, declared.value)
            if nodes:
                record['-children'] = nodes
        else:
            record['@value'] = json_value(declared.type_name, declared.value)
        return record

    # Nodes

    def node(self, target: Any) -> "dict[str, Any]":
        target = self.written_as(target)
        type_name, prototype = self.type_of(target)
        name, use = self.reference(target)
        record: "dict[str, Any]" = {}
        if prototype:
            record['@name'] = type_name
        if name:
            record['@USE' if use else '@DEF'] = name
        key = 'ProtoInstance' if prototype else type_name
        if use:
            return {key: record}
        self.opened(target)
        # Declared fields come first: an IS connection names one of them.
        declarations = [self.declaration_object(item) for item in self.own_declarations(target)]
        if declarations:
            record['field'] = declarations
        connections = self.connections(target)
        if connections:
            record['IS'] = {'connect': [{'@nodeField': nodeField, '@protoField': protoField}
                                        for nodeField, protoField in connections]}
        if prototype:
            given = []
            for item in self.values(target):
                given.append({'@name': item.name,
                              '@value': json_value(item.type_name, item.value)})
            for item in self.node_fields(target):
                given.append({'@name': item.name,
                              '-children': self._nodes(item.type_name, item.value)})
            if given:
                record['fieldValue'] = given
        else:
            for item in self.values(target):
                record['@' + item.name] = json_value(item.type_name, item.value)
            for item in self.node_fields(target):
                nodes = self._nodes(item.type_name, item.value)
                record['-' + item.name] = nodes[0] if item.type_name == 'SFNode' else nodes
        source = self.source(target).strip()
        if source:
            record['#sourceCode'] = source.split('\n')
        self.closed(target)
        return {key: record}

    def _nodes(self, type_name: str, value: Any) -> "list[Any]":
        if type_name == 'SFNode':
            return [self.node(value)] if value else []
        return [self.node(child) for child in value]


def write(scene: X3DScene, version: "str | None" = None, canonical: bool = False) -> str:
    """Write a scene as an X3D JSON document"""
    return JSONWriter(scene, version, canonical).write()
