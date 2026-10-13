"""EXTERNPROTO references that name a node the vocabulary has

Vendors published prototype files for nodes a standard later took up, and
worlds name those files by URN and by URL. `KNOWN` maps each such reference to
the node it is read as. A reference is matched as text and is not fetched, so
a world naming one is built from the load's own class for that node, whether
or not the file it names can still be read.

`SceneBuilder` asks the table for each EXTERNPROTO before its
`extern_resolver`. An entry is used when the load's vocabulary has the node
and the node has each field the EXTERNPROTO declares, with the declared type;
otherwise the declaration is resolved as any other is.

An application adds a reference of its own with `KNOWN.add(KnownPrototype(...))`.

The blaxxun and Bitmanagement references are recorded, with the worlds each
was seen in, in `specs/vrml97/known-prototype-references.md`.
"""

from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any

from vrml import field, node, protofunctions
from vrml import fieldtypes  # noqa: F401 registers the field types used below

__all__ = ['BLAXXUN_NURBS', 'BLAXXUN_REFERENCES', 'KNOWN', 'KnownPrototype',
           'KnownPrototypes', 'interface_difference']


class KnownPrototype(node.Node):
    """References that name one node

    references -- each reference whole, with the node's name: a URN, or a URL
        with its ``#name``
    readAs -- the node's name in the load's vocabulary
    """

    PROTO = 'KnownPrototype'
    references = field.newField('references', 'MFString', 1, list)
    readAs = field.newField('readAs', 'SFString', 1, '')


def _key(reference: str) -> str:
    """What a reference is matched by: its location without regard to case
    or to http against https, and the node's name as written"""
    text = reference.strip()
    cut = text.rfind('#') if '#' in text else text.rfind(':')
    location, name = text[:cut + 1].casefold(), text[cut + 1:]
    if location.startswith('https://'):
        location = 'http://' + location[len('https://'):]
    return location + name


class KnownPrototypes:
    """The known references of a load, by reference"""

    def __init__(self, entries: Iterable[KnownPrototype] = ()) -> None:
        self._entries: "list[KnownPrototype]" = []
        self._by_key: "dict[str, KnownPrototype]" = {}
        for entry in entries:
            self.add(entry)

    def __iter__(self) -> Iterator[KnownPrototype]:
        return iter(self._entries)

    def add(self, entry: KnownPrototype) -> None:
        """Match the entry's references from now on, ahead of an earlier entry's"""
        self._entries.append(entry)
        for reference in entry.references:
            self._by_key[_key(str(reference))] = entry

    def remove(self, entry: KnownPrototype) -> None:
        """Stop matching the entry's references"""
        self._entries.remove(entry)
        self._by_key = {}
        for other in self._entries:
            for reference in other.references:
                self._by_key[_key(str(reference))] = other

    def find(self, urls: Sequence[str]) -> "tuple[str, KnownPrototype] | None":
        """The first of an EXTERNPROTO's URLs that is known, and its entry"""
        for url in urls:
            entry = self._by_key.get(_key(str(url)))
            if entry is not None:
                return str(url).strip(), entry
        return None


#: Field types that hold the same values in a narrower array.
_STORED_AS = {'MFFloat32': 'MFFloat', 'SFArray32': 'SFArray'}


def _values(type_name: str) -> str:
    return _STORED_AS.get(type_name, type_name)


def interface_difference(
    declared: Iterable[Any],
    cls: type,
    current_name: "Callable[[str], str]" = str,
) -> "str | None":
    """How an EXTERNPROTO's fields differ from the node class's; None where they agree

    The answer completes "the node X, ...": the first declared field the class
    lacks, or holds as another type. A field's access is not compared, and
    neither are the declared events.

    current_name -- the class's name for a field the document names
    """
    for item in declared:
        if not isinstance(item, field.Field):
            continue
        try:
            have = protofunctions.getField(cls, current_name(item.name))
        except AttributeError:
            have = None
        if not isinstance(have, field.Field):
            return 'which has no field %s' % item.name
        if _values(str(have.typeName())) != _values(str(item.typeName())):
            return 'whose %s is an %s, not an %s' % (
                item.name, have.typeName(), item.typeName())
    return None


#: What a blaxxun or Bitmanagement world's reference to one of that browser's
#: own nodes begins with; the node's name follows.
BLAXXUN_REFERENCES = (
    'urn:inet:blaxxun.com:node:',
    'urn:inet:bitmanagement.de:node:',
    'http://www.blaxxun.com/vrml/protos/nurbs.wrl#',
)

#: The NURBS nodes those references name.
BLAXXUN_NURBS = (
    'Contour2D', 'CoordinateDeformer', 'NurbsCurve', 'NurbsCurve2D', 'NurbsGroup',
    'NurbsPositionInterpolator', 'NurbsSurface', 'NurbsTextureSurface', 'Polyline2D',
    'TrimmedSurface',
)

#: The references every load knows.
KNOWN = KnownPrototypes(
    KnownPrototype(references=[prefix + name for prefix in BLAXXUN_REFERENCES], readAs=name)
    for name in BLAXXUN_NURBS
)
