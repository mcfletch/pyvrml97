"""Node types an application adds to the X3D vocabulary, in components of its own

X3D groups its nodes in components, and a document names the ones it uses
beyond its profile with COMPONENT statements. An application whose nodes X3D
has no node for registers their classes here. A registered node is then read
from an X3D document of any encoding, and written to one with the COMPONENT
statement that names its component. Another browser reading that document
finds a component it does not have.

A class says where it belongs with three attributes:

- `PROTO`, the node's name, which X3D and X_ITE have no node of;
- `COMPONENT`, the component's name and the node's level in it;
- `SINCE`, the first X3D version a document may hold the node in ('3.0'
  where the class names none).

VRML97 has no components, so a VRML97 document holds none of these nodes.
X_ITE's own nodes are declared in `vrml.x3d.xite`, not here.
"""

from typing import Any

from vrml import protofunctions
from vrml.x3d import profiles, xite

__all__ = ['component_of', 'declaration', 'nodes', 'register', 'types_in', 'unregister',
           'vocabulary_class']

#: The registered classes, by node name.
_NODES: "dict[str, type]" = {}


def _version(text: str) -> "tuple[int, ...]":
    return tuple(int(part) for part in text.split('.'))


def _levels() -> None:
    """Give `profiles.EXTENSION_COMPONENTS` each registered component's highest level"""
    highest: "dict[str, int]" = {}
    for cls in _NODES.values():
        name, level = component_of(str(protofunctions.protoName(cls)))
        highest[name] = max(level, highest.get(name, 0))
    for name in [name for name in _OWNED if name not in highest]:
        profiles.EXTENSION_COMPONENTS.pop(name, None)
        _OWNED.discard(name)
    for name, level in highest.items():
        profiles.EXTENSION_COMPONENTS[name] = level
        _OWNED.add(name)


#: The component names this module has put in `profiles.EXTENSION_COMPONENTS`.
_OWNED: "set[str]" = set()


def register(*classes: type) -> None:
    """Add node classes to the vocabulary

    Raises ValueError for a class whose name X3D or X_ITE has a node of, one
    that names no component, and a component name X3D or X_ITE has.
    """
    for cls in classes:
        name = str(protofunctions.protoName(cls))
        if xite.declaration(name) is not None:
            raise ValueError('X3D has a node %s' % name)
        component: Any = getattr(cls, 'COMPONENT', None)
        if not component:
            raise ValueError('%s names no COMPONENT' % name)
        if component[0] in profiles.COMPONENTS or (
                component[0] in profiles.EXTENSION_COMPONENTS and component[0] not in _OWNED):
            raise ValueError('X3D has a component %s' % component[0])
        _NODES[name] = cls
        _OWNED.add(str(component[0]))
    _levels()


def unregister(*classes: type) -> None:
    """Take node classes out of the vocabulary; a class not in it is passed over"""
    for cls in classes:
        name = str(protofunctions.protoName(cls))
        if _NODES.get(name) is cls:
            del _NODES[name]
    _levels()


def nodes() -> "dict[str, type]":
    """The registered classes, by node name"""
    return dict(_NODES)


def declaration(type_name: str) -> "type | None":
    """The registered class for the node type `type_name`, or None"""
    return _NODES.get(type_name)


def component_of(type_name: str) -> "tuple[str, int]":
    """The component and level the registered node type `type_name` is in"""
    name, level = _NODES[type_name].COMPONENT  # type: ignore[attr-defined]  # register() requires it
    return str(name), int(level)


def types_in(version: str) -> "frozenset[str]":
    """The registered node types a document of X3D `version` may hold

    None in VRML97, and all of them for a dialect naming no version.
    """
    if not version:
        return frozenset(_NODES)
    if _version(version) < (3, 0):
        return frozenset()
    return frozenset(name for name, cls in _NODES.items()
                     if _version(str(getattr(cls, 'SINCE', '3.0'))) <= _version(version))


def vocabulary_class(type_name: str) -> "type | None":
    """The class declaring `type_name`'s fields: X3D's, X_ITE's or a registered one"""
    found = xite.VOCABULARY.get(type_name)
    return found if found is not None else _NODES.get(type_name)

