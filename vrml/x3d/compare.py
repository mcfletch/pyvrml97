"""Comparing scenes: where two graphs first differ

`first_difference(a, b)` walks two scenes together and answers a path to
the first node type, field value, route or statement that differs, or None
where the graphs are equal. Numbers compare to float32 precision. A node
shared in one graph has to be shared at the same places in the other.
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

#: Relative and absolute tolerance for numbers: what float32 resolves.
TOLERANCE = 1e-6

#: The url schemes of a program written inline.
INLINE_SCHEMES = ('ecmascript:', 'javascript:', 'vrmlscript:')


def _inline(url: str) -> bool:
    return url.strip().lower().startswith(INLINE_SCHEMES)


def _program(target: Any) -> "tuple[str, list[str]]":
    """A node's inline program text, and the urls that are not inline"""
    urls = list(getattr(target, 'url', None) or [])
    source = (getattr(target, 'sourceCode', '') or '').strip()
    if not source:
        source = '\n'.join(url.strip() for url in urls if _inline(url))
    return source, [url for url in urls if not _inline(url)]


def _values_differ(a: Any, b: Any) -> "str | None":
    """Why two field values differ, or None"""
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        a, b = np.asarray(a), np.asarray(b)
        if a.shape != b.shape:
            return 'shape %s != %s' % (a.shape, b.shape)
        if a.dtype == bool or b.dtype == bool or a.dtype.kind in 'iu':
            equal = bool(np.array_equal(a, b))
        else:
            equal = bool(np.allclose(a, b, rtol=TOLERANCE, atol=TOLERANCE))
        return None if equal else '%s != %s' % (a.tolist()[:6], b.tolist()[:6])
    if isinstance(a, float) or isinstance(b, float):
        try:
            same = abs(float(a) - float(b)) <= TOLERANCE * max(1.0, abs(float(a)))
        except (TypeError, ValueError):
            same = False
        return None if same else '%r != %r' % (a, b)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return 'length %d != %d' % (len(a), len(b))
        for index, (left, right) in enumerate(zip(a, b)):
            found = _values_differ(left, right)
            if found:
                return '[%d] %s' % (index, found)
        return None
    return None if a == b else '%r != %r' % (a, b)


class _Comparison:
    def __init__(self, ignore: "frozenset[tuple[str, str]]") -> None:
        self.ignore = ignore
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
        for name in sorted(names):
            if name.startswith(' ') or name == 'externalURL' or (type_name, name) in self.ignore:
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
        found = _values_differ(left, right)
        return '%s: %s' % (path, found) if found else None

    def node_lists(self, a: Sequence[Any], b: Sequence[Any], path: str) -> "str | None":
        if len(a) != len(b):
            return '%s: %d nodes != %d' % (path, len(a), len(b))
        for index, (left, right) in enumerate(zip(a, b)):
            found = self.nodes(left, right, '%s[%d]' % (path, index))
            if found:
                return found
        return None


def _routes(scene: Any) -> "list[tuple[str, str, str, str]]":
    result = []
    for each in scene.routes:
        result.append((protofunctions.defName(each.source), each.sourceField,
                       protofunctions.defName(each.destination), each.destinationField))
    return sorted(result)


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
    found = comparison.node_lists(list(a.children), list(b.children), 'children')
    if found:
        return found
    if _routes(a) != _routes(b):
        return 'routes: %s != %s' % (_routes(a), _routes(b))
    return None
