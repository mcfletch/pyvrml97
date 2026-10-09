"""Fields a class adds to an X3D node, carried through a document as metadata

A node class that adds fields to an X3D node type names a metadata set in its
`x3dExtension` attribute. The writers put each added field that holds other
than its default in a `MetadataSet` of that name on the node's `metadata`,
with the node's own metadata as the set's `metadata`. The builder, given the
class among its prototypes, sets the fields back from the set and gives the
node its own metadata again. Read without the class, the set stays as the
node's metadata, which is valid X3D.

Each field is one metadata node named after it: the boolean types as
`MetadataBoolean`, the integer types (and `SFImage`) as `MetadataInteger`, the
double-precision types as `MetadataDouble`, the strings as `MetadataString`,
and the other types as `MetadataFloat` with their components in order. A node
value is a `MetadataSet` whose `reference` is the node's type and whose
entries are its fields, by the same rules, and a list of nodes is a
`MetadataSet` holding one such set for each.

A node with no X3D type of its own may give `x3dEquivalent()`, the X3D node
the writers write in its place.
"""

from collections.abc import Callable, Iterable
from typing import Any, Optional

from vrml import node, protofunctions
from vrml.x3d import codecs, xite
from vrml.x3d import nodes as x3d

#: The metadata node a field of each type is written as, by type name.
_BOOLEAN = frozenset(('SFBool', 'MFBool'))
_INTEGER = frozenset(('SFInt32', 'MFInt32', 'SFImage', 'MFImage'))
_STRING = frozenset(('SFString', 'MFString'))
_DOUBLE = frozenset(('SFDouble', 'MFDouble', 'SFTime', 'MFTime', 'SFVec2d', 'MFVec2d',
                     'SFVec3d', 'MFVec3d', 'SFVec4d', 'MFVec4d', 'SFMatrix3d',
                     'MFMatrix3d', 'SFMatrix4d', 'MFMatrix4d'))
_SCALAR = frozenset(('SFBool', 'SFInt32', 'SFString', 'SFFloat', 'SFDouble', 'SFTime'))


def vocabulary_fields(type_name: str) -> "frozenset[str]":
    """The field names the X3D node type `type_name` declares; empty for an unknown type"""
    found = _VOCABULARY.get(type_name)
    if found is None:
        cls = xite.VOCABULARY.get(type_name)
        names = protofunctions.getFields(cls) + protofunctions.getFields(cls, 1) if cls else []
        found = _VOCABULARY[type_name] = frozenset(item.name for item in names)
    return found


_VOCABULARY: "dict[str, frozenset[str]]" = {}


def added_fields(target: Any) -> "list[Any]":
    """The fields `target` declares that its X3D node type does not"""
    known = vocabulary_fields(str(protofunctions.protoName(target)))
    return [declared for declared in protofunctions.getFields(target)
            if not declared.name.startswith(' ') and declared.name not in known]


def _flat(type_name: str, value: Any) -> "list[Any]":
    """A field value as the list of numbers or strings a metadata node holds"""
    if type_name in _SCALAR:
        return [value]
    if type_name in _STRING:
        return [str(item) for item in value]
    if type_name in _BOOLEAN:
        return [bool(item) for item in value]
    if type_name == 'SFImage':
        return [int(item) for item in value]
    import numpy  # noqa: PLC0415 only vector values need it
    return [float(item) if type_name not in _INTEGER else int(item)
            for item in numpy.asarray(value).ravel()]


def _itself(target: Any) -> Any:
    return target


def encode(name: str, declared: Any, value: Any,
           written_as: "Callable[[Any], Any]" = _itself) -> Any:
    """The metadata node holding one field's value, named `name`

    written_as -- the node written for a node value (the writer's
        `x3dEquivalent()` substitution)
    """
    type_name = str(declared.typeName())
    if type_name == 'SFNode':
        return node_metadata(name, written_as(value), written_as)
    if type_name == 'MFNode':
        return nodes_metadata(name, value, written_as)
    if type_name in _BOOLEAN:
        cls: type = x3d.MetadataBoolean
    elif type_name in _INTEGER:
        cls = x3d.MetadataInteger
    elif type_name in _STRING:
        cls = x3d.MetadataString
    elif type_name in _DOUBLE:
        cls = x3d.MetadataDouble
    else:
        cls = x3d.MetadataFloat
    return cls(name=name, value=_flat(type_name, value))


def node_metadata(name: str, target: Any,
                  written_as: "Callable[[Any], Any]" = _itself) -> Any:
    """A `MetadataSet` named `name` holding a node's type and its non-default fields"""
    entries = []
    for declared in protofunctions.getFields(target):
        if declared.name.startswith(' ') or declared.name == 'metadata':
            continue
        value = declared.fget(target)
        if isinstance(declared, node.MFNode):
            if len(value):
                entries.append(nodes_metadata(declared.name, value, written_as))
            continue
        if isinstance(declared, node.SFNode):
            if value:
                entries.append(node_metadata(declared.name, written_as(value), written_as))
            continue
        if codecs.same(value, declared.coerce(declared.getDefault())):
            continue
        entries.append(encode(declared.name, declared, value))
    return x3d.MetadataSet(name=name, reference=str(protofunctions.protoName(target)),
                           value=entries)


def nodes_metadata(name: str, targets: Iterable[Any],
                   written_as: "Callable[[Any], Any]" = _itself) -> Any:
    """A `MetadataSet` named `name` holding a :func:`node_metadata` set for each node"""
    return x3d.MetadataSet(name=name, value=[
        node_metadata(name, written_as(target), written_as) for target in targets])


def extension_set(target: Any, added: "Iterable[tuple[Any, Any]]",
                  written_as: "Callable[[Any], Any]" = _itself) -> Any:
    """The set named by `target`'s class holding the added fields' values

    The node's own metadata is the set's `metadata`.
    """
    entries = [encode(declared.name, declared, value, written_as) for declared, value in added]
    found = x3d.MetadataSet(name=str(type(target).x3dExtension), value=entries)
    own = getattr(target, 'metadata', None)
    if own:
        found.metadata = own
    return found


def decode(declared: Any, entry: Any, make: "Callable[[str], Optional[type]]") -> Any:
    """A field's value from the metadata node it was written as"""
    type_name = str(declared.typeName())
    if type_name == 'SFNode':
        return node_from(entry, make)
    if type_name == 'MFNode':
        built = [node_from(item, make) for item in getattr(entry, 'value', ())]
        return [item for item in built if item]
    values = list(entry.value)
    if type_name in _SCALAR:
        return declared.coerce(values[0]) if values else declared.getDefault()
    size = codecs.TUPLE_SIZE.get(type_name)
    if size and type_name.startswith('MF'):
        values = [values[index:index + size] for index in range(0, len(values), size)]
    return declared.coerce(values)


def node_from(entry: Any, make: "Callable[[str], Optional[type]]") -> Any:
    """The node a `MetadataSet` written by :func:`node_metadata` describes, or NULL"""
    cls = make(str(entry.reference))
    if cls is None or not isinstance(entry, x3d.MetadataSet):
        return node.NULL
    built = cls()
    for item in entry.value:
        try:
            declared = protofunctions.getField(built, str(item.name))
        except AttributeError:
            continue
        declared.fset(built, decode(declared, item, make), notify=False)
    return built


def restore(target: Any, make: "Callable[[str], Optional[type]]",
            report: "Callable[[str], None]") -> None:
    """Set `target`'s added fields from its extension set, and give it its own metadata

    make -- the node class for an X3D type name, or None
    report -- called with a message for an entry naming no field
    """
    name = getattr(type(target), 'x3dExtension', None)
    found = getattr(target, 'metadata', None)
    if not name or not isinstance(found, x3d.MetadataSet) or str(found.name) != name:
        return
    for entry in found.value:
        try:
            declared = protofunctions.getField(target, str(entry.name))
        except AttributeError:
            report('%s has no field %s, named in its %s metadata'
                   % (protofunctions.protoName(target), entry.name, name))
            continue
        declared.fset(target, decode(declared, entry, make), notify=False)
    target.metadata = found.metadata if found.metadata else node.NULL
