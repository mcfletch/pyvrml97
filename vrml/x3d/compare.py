"""Comparing scenes: where two graphs first differ

`first_difference(a, b)` walks two scenes together and answers a path to
the first node type, field value, route, prototype or statement that
differs, or None where the graphs are equal. Numbers compare to the
precision of their type: float32 for the single-precision types, float64
for the double ones. A node shared in one graph has to be shared at the
same places in the other, and a route joins the same nodes in both. A
prototype compares by its interface -- each field's type, access and
default -- and its body.
Comments and `meta` statements are not compared. A Script's or shader's
program is compared as one text without the whitespace around it, whether a
document carries it inline (XML's character data, the `sourceCode` field) or
as an inline url (ClassicVRML's `"ecmascript:..."`), which the encodings
define as the same thing.
"""

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

from vrml import field, node, protofunctions
from vrml.x3d.writers.base import INLINE_SCHEMES

#: Relative and absolute tolerance for numbers: what float32 resolves.
TOLERANCE = 1e-6
#: The same for the double-precision types: what float64 resolves.
DOUBLE_TOLERANCE = 1e-15
#: X3D's double-precision field types.
DOUBLE_TYPES = frozenset((
    'SFDouble', 'MFDouble', 'SFTime', 'MFTime',
    'SFVec2d', 'MFVec2d', 'SFVec3d', 'MFVec3d', 'SFVec4d', 'MFVec4d',
    'SFMatrix3d', 'MFMatrix3d', 'SFMatrix4d', 'MFMatrix4d',
))



def _inline(url: str) -> bool:
    return url.strip().lower().startswith(INLINE_SCHEMES)


def _program(target: Any) -> "tuple[str, list[str]]":
    """A node's inline program text, and the urls that are not inline"""
    urls = list(getattr(target, 'url', None) or [])
    source = (getattr(target, 'sourceCode', '') or '').strip()
    if not source:
        source = '\n'.join(url.strip() for url in urls if _inline(url))
    return source, [url for url in urls if not _inline(url)]


def _values_differ(a: Any, b: Any, tolerance: float = TOLERANCE) -> "str | None":
    """Why two field values differ, or None"""
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        a, b = np.asarray(a), np.asarray(b)
        if a.shape != b.shape:
            return 'shape %s != %s' % (a.shape, b.shape)
        if a.dtype == bool or b.dtype == bool or a.dtype.kind in 'iu':
            equal = bool(np.array_equal(a, b))
        else:
            equal = bool(np.allclose(a, b, rtol=tolerance, atol=tolerance))
        return None if equal else '%s != %s' % (a.tolist()[:6], b.tolist()[:6])
    if isinstance(a, float) or isinstance(b, float):
        try:
            same = abs(float(a) - float(b)) <= tolerance * max(1.0, abs(float(a)))
        except (TypeError, ValueError):
            same = False
        return None if same else '%r != %r' % (a, b)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return 'length %d != %d' % (len(a), len(b))
        for index, (left, right) in enumerate(zip(a, b)):
            found = _values_differ(left, right, tolerance)
            if found:
                return '[%d] %s' % (index, found)
        return None
    return None if a == b else '%r != %r' % (a, b)


def _tolerance(declared: Any) -> float:
    """The tolerance a field's numbers compare to, by its type"""
    return DOUBLE_TOLERANCE if str(declared.typeName()) in DOUBLE_TYPES else TOLERANCE


class _Comparison:
    def __init__(self, ignore: "frozenset[tuple[str, str]]",
                 connected: "dict[Any, set[str]] | None" = None) -> None:
        self.ignore = ignore
        #: For each node of a prototype body, its fields an IS connection
        #: gives a value: the template's own value is not one an instance has.
        self.connected = connected or {}
        self.pairs: "dict[Any, Any]" = {}
        self.reverse: "dict[Any, Any]" = {}

    def nodes(self, a: Any, b: Any, path: str) -> "str | None":
        if not a or not b:
            if bool(a) != bool(b):
                return '%s: %s != %s' % (path, a, b)
            return None
        if a in self.pairs or b in self.reverse:
            if self.pairs.get(a) is b and self.reverse.get(b) is a:
                return None
            return '%s: a node shared in one graph is not shared in the other' % path
        self.pairs[a] = b
        self.reverse[b] = a
        if protofunctions.protoName(a) != protofunctions.protoName(b):
            return '%s: %s != %s' % (path, protofunctions.protoName(a),
                                     protofunctions.protoName(b))
        type_name = protofunctions.protoName(a)
        names = {f.name for f in protofunctions.getFields(a)} | {
            f.name for f in protofunctions.getFields(b)}
        if 'sourceCode' in names and 'url' in names:
            left, right = _program(a), _program(b)
            if left[0] != right[0]:
                return '%s: program source %r != %r' % (path, left[0][:60], right[0][:60])
            if left[1] != right[1]:
                return '%s.url: %r != %r' % (path, left[1], right[1])
            names -= {'sourceCode', 'url'}
        connected = self.connected.get(a, ())
        for name in sorted(names):
            if name.startswith(' ') or name == 'externalURL' or (type_name, name) in self.ignore:
                continue
            if name in connected:
                continue
            found = self.fields(a, b, name, '%s.%s' % (path, name))
            if found:
                return found
        return None

    def fields(self, a: Any, b: Any, name: str, path: str) -> "str | None":
        try:
            left_field = protofunctions.getField(a, name)
            right_field = protofunctions.getField(b, name)
        except AttributeError:
            return '%s: present in only one' % path
        left = left_field.__get__(a) if isinstance(left_field, field.Field) else None
        right = right_field.__get__(b) if isinstance(right_field, field.Field) else None
        if isinstance(left_field, node.MFNode):
            return self.node_lists(list(left or []), list(right or []), path)
        if isinstance(left_field, node.SFNode):
            return self.nodes(left, right, path)
        found = _values_differ(left, right, _tolerance(left_field))
        return '%s: %s' % (path, found) if found else None

    def node_lists(self, a: Sequence[Any], b: Sequence[Any], path: str) -> "str | None":
        if len(a) != len(b):
            return '%s: %d nodes != %d' % (path, len(a), len(b))
        for index, (left, right) in enumerate(zip(a, b)):
            found = self.nodes(left, right, '%s[%d]' % (path, index))
            if found:
                return found
        return None


    def routes(self, a: Any, b: Any, path: str) -> "str | None":
        """Whether `a`'s routes join the nodes paired with those `b`'s join"""
        def ends(scene: Any, pair: "dict[Any, Any]") -> "list[tuple[int, str, int, str]]":
            return sorted((id(pair.get(each.source, each.source)), str(each.sourceField),
                           id(pair.get(each.destination, each.destination)),
                           str(each.destinationField)) for each in scene.routes)
        if ends(a, self.pairs) != ends(b, {}):
            return '%s: %s != %s' % (path, _named_routes(a), _named_routes(b))
        return None

    def connections(self, a: type, b: type, path: str) -> "str | None":
        """Whether prototype `a`'s IS connections join the body nodes paired with `b`'s"""
        def joined(proto: type, pair: "dict[Any, Any]") -> "list[tuple[str, int, str]]":
            return sorted((str(proto_field), id(pair.get(target, target)), str(node_field))
                          for proto_field, targets in node.ismaps(proto).items()
                          for target, node_field in targets)
        if joined(a, self.pairs) != joined(b, {}):
            return '%s: the connections differ' % path
        return None

    def prototypes(self, a: Any, b: Any, path: str) -> "str | None":
        """Where two scenes' prototypes of one name differ: interface, then body"""
        for name in sorted(a.protoTypes):
            left, right = a.protoTypes[name], b.protoTypes[name]
            found = _interface_differs(left, right)
            if found:
                return '%s.%s: %s' % (path, name, found)
            left_body = protofunctions.getSceneGraph(left)
            right_body = protofunctions.getSceneGraph(right)
            if bool(left_body) != bool(right_body):
                return '%s.%s: a body in only one' % (path, name)
            if left_body:
                connected: "dict[Any, set[str]]" = {}
                for targets in node.ismaps(left).values():
                    for target, node_field in targets:
                        connected.setdefault(target, set()).add(node_field)
                body = _Comparison(self.ignore, connected)
                found = (body.node_lists(list(left_body.children), list(right_body.children),
                                         '%s.%s' % (path, name))
                         or body.routes(left_body, right_body, '%s.%s.routes' % (path, name))
                         or body.connections(left, right, '%s.%s.IS' % (path, name)))
                if found:
                    return found
        return None


def _interface_differs(a: type, b: type) -> "str | None":
    """Where two prototypes' declared fields differ: name, type, access, default"""
    def declared(proto: type) -> "dict[str, Any]":
        return {item.name: item for item in protofunctions.getFields(proto)
                if not item.name.startswith(' ') and item.name not in ('externalURL',)}
    left, right = declared(a), declared(b)
    if sorted(left) != sorted(right):
        return 'fields %s != %s' % (sorted(left), sorted(right))
    for name in sorted(left):
        first, second = left[name], right[name]
        if (first.typeName(), first.accessType) != (second.typeName(), second.accessType):
            return '%s: %s %s != %s %s' % (name, first.accessType, first.typeName(),
                                           second.accessType, second.typeName())
        if isinstance(first, (node.SFNode, node.MFNode)):
            continue
        # Each default as an instance holds it: a declaration without a
        # value gives the type's own, which the field coerces on first use
        found = _values_differ(first.coerce(first.getDefault()), second.coerce(second.getDefault()),
                               _tolerance(first))
        if found:
            return '%s default: %s' % (name, found)
    return None


def _named_routes(scene: Any) -> "list[tuple[str, str, str, str]]":
    return sorted((protofunctions.defName(each.source), str(each.sourceField),
                   protofunctions.defName(each.destination), str(each.destinationField))
                  for each in scene.routes)


def _records(nodes: Sequence[Any], names: Sequence[str]) -> "list[tuple[Any, ...]]":
    return [tuple(getattr(item, name) for name in names) for item in nodes]


def first_difference(
    a: Any, b: Any, ignore: "Iterable[tuple[str, str]]" = (), header: bool = True,
) -> "str | None":
    """Where two scenes first differ, or None where their graphs are equal

    ignore -- (node type, field name) pairs not to compare
    header -- compare the profile, version, components and units; False for
        the same scene read from a VRML97 file, which has none of them
    """
    for name in ('profile', 'version') if header else ():
        if getattr(a, name, None) != getattr(b, name, None):
            return '%s: %r != %r' % (name, getattr(a, name, None), getattr(b, name, None))
    checks = (
        ('components', ('name', 'level')),
        ('units', ('category', 'name', 'conversionFactor')),
        ('imports', ('inlineDEF', 'importedDEF', 'localDEF')),
        ('exports', ('localDEF', 'AS')),
    )
    for name, fields in checks:
        if not header and name in ('components', 'units'):
            continue
        left = _records(getattr(a, name, ()), fields)
        right = _records(getattr(b, name, ()), fields)
        if left != right:
            return '%s: %s != %s' % (name, left, right)
    if sorted(a.protoTypes) != sorted(b.protoTypes):
        return 'prototypes: %s != %s' % (sorted(a.protoTypes), sorted(b.protoTypes))
    comparison = _Comparison(frozenset(ignore))
    return (comparison.prototypes(a, b, 'prototypes')
            or comparison.node_lists(list(a.children), list(b.children), 'children')
            or comparison.routes(a, b, 'routes'))
