"""Functions for manipulating prototypes (node classes)

Prototypes are implemented as classes, and so are
available from every instance node, but we often
want to be able to manipulate the classes themselves
without needing lots of class-methods

The protofunctions module allows us to abstract the
actual implementation of the prototype away.  If we
at some point want to create a real "prototype" class,
we could do so with most changes confined to this
module.
"""
from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Any, Literal, Optional, overload
from vrml import field
from vrml import field as fieldmodule
if TYPE_CHECKING:
    # typing has TypeAlias from Python 3.10; the annotations naming it are
    # not evaluated, so only the checker needs the name.
    from typing import TypeAlias
    # Under a private name: the modules that star-import this one include
    # vrml.node, which defines Node.
    from vrml import node as _node

#: What a prototype declares under a name.
FieldOrEvent: TypeAlias = 'fieldmodule.Field | fieldmodule.Event'
#: A prototype, or an instance of one.
Prototyped: TypeAlias = 'type[_node.PrototypedNode] | _node.PrototypedNode'
#: A node class, or a node.
NodeOrClass: TypeAlias = 'type[_node.Node] | _node.Node'


def _getcls(cls: object) -> type:
    """Utility function returns class when passed instance or class

    Any object will do: a field is a descriptor, so a class that is not a
    Node, such as a mix-in, declares fields in the same way.
    """
    if type(cls) is type:
        return cls
    else:
        return cls.__class__


def getPrototype(cls: object) -> type:
    """Return the prototype for the node or class

    returns either the argument (if it is a proto)
    or the prototype of the argument
    """
    return _getcls(cls)


def protoName(obj: Any, value: Optional[str]=None, *args: Any, **named: Any) -> str:  # noqa: ARG001 public; the get/set signature it shares with name() and defName()
    """Get/set the prototype name for the object

    returns the prototype name
    """
    obj = _getcls(obj)
    if value is not None:
        obj.PROTO = value
        return value
    elif issubclass(obj, list):
        return '__MFNode__'
    else:
        possible: str = obj.PROTO
        if not possible:
            return obj.__name__.split(".")[-1]
        return possible


def defName(obj: object, value: Optional[str]=None, *args: Any, **named: Any) -> str:
    """Get/set the VRML97 defName for the object

    returns the DEF name, which is empty for an unnamed node
    """
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    current: str
    if value is not None:
        current = node.Node.DEF.fset(obj, value, *args, **named)
    else:
        current = node.Node.DEF.fget(obj, *args, **named)
    return current


def name(obj: object, value: Optional[str]=None, *args: Any, **named: Any) -> str:
    """Get/set prototype name for prototypes, DEF name for nodes"""
    if type(obj) is type:
        return protoName(obj, value, *args, **named)
    else:
        return defName(obj, value, *args, **named)


def root(obj: object, value: Any=None, *args: Any, **named: Any) -> Any:
    """Get/set root-node reference for nodes/protos"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    if value is not None:
        return node.Node.rootSceneGraph.fset(obj, value, *args, **named)
    else:
        return node.Node.rootSceneGraph.fget(obj, *args, **named)


def builtin(cls: object) -> bool:
    """Return whether the class is "built-in" to the system"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return not issubclass(_getcls(cls), node.PrototypedNode)


def addField(cls: object, field: FieldOrEvent) -> None:
    """Add a particular field/event to the class/prototype definition

    At present this just calls setattr(cls,field.name,field)
    """
    global _declarations
    setattr(_getcls(cls), field.name, field)
    _declarations += 1


def removeField(cls: object, field: 'str | FieldOrEvent') -> None:
    """Remove a particular field/event to the class/prototype definition

    If field is a string, calls delattr(cls,field) for the class
    otherwise calls delattr( cls, field.name )
    """
    global _declarations
    if isinstance(field, str):
        delattr(_getcls(cls), field)
    else:
        delattr(_getcls(cls), field.name)
    _declarations += 1


def getField(cls: object, field: str) -> FieldOrEvent:
    """Get a field/event object for the given name

    field -- a field-name specifier, which may be any of
        the following, (with the various options checked in
        order, so that earlier options will take
        precedence over later options):

        * the exact name of the field/demand as specified
            in the class's namespace (fastest and first
            checked)
        * the "storage" name of a field, that is, the "name"
            attribute of a field where that name does not
            match the previous definition (commonly seen in
            non-standard fields on VRML97 standard nodes)
        * the "storage" name of an event
        * a pseudo-event with the prefix "set_" or the
            suffix "_changed", which will return the
            associated field/event as if the suffix were
            not present (does a recursive call with the
            truncated name)

    Raises AttributeError for a name that is none of these. A class
    attribute that is not a field or an event is none of them, and hides an
    inherited field of its name.
    """
    cls = _getcls(cls)
    try:
        found = getattr(cls, field)
    except (AttributeError, KeyError):
        # OK, may be a space-prefixed name...
        for fieldObject in getFields(cls):
            if fieldObject.name == field:
                return fieldObject
        # OK, may be an event with space-prefixed name
        for eventObject in getFields(cls, 1):
            if eventObject.name == field:
                return eventObject
        # OK, may be one of the "component" events
        # of a field...
        if field.startswith("set_"):
            return getField(cls, field[4:])
        elif field.endswith("_changed"):
            return getField(cls, field[:-8])
    else:
        if isinstance(found, fieldmodule.AliasField):
            return getField(cls, found.target)
        if isinstance(found, (fieldmodule.Field, fieldmodule.Event)):
            return found
    raise AttributeError(
        """The prototype %s does not define a field named %s"""
        % (protoName(cls), field)
    )


#: Moved by addField and removeField; part of what a class's fields are held against.
_declarations = 0
#: Each class's fields and events, with what they were found against. The
#: lists are of Field under 0 and of Event under 1, which a dict's value type
#: cannot say.
_FOUND: "weakref.WeakKeyDictionary[type, dict[int, tuple[tuple[int, tuple[int, ...]], list[Any]]]]" = (
    weakref.WeakKeyDictionary())


@overload
def getFields(cls: object, events: Literal[0, False]=0) -> 'list[fieldmodule.Field]': ...
@overload
def getFields(cls: object, events: Literal[1, True]) -> 'list[fieldmodule.Event]': ...
@overload
def getFields(cls: object, events: int) -> 'list[fieldmodule.Field] | list[fieldmodule.Event]': ...
def getFields(cls: object, events: int=0) -> 'list[fieldmodule.Field] | list[fieldmodule.Event]':
    """Get all fields of the definition/prototype

    if events is true, then return events
    instead of fields.

    Kept for each class against the number of attributes each class of its
    MRO has and the count addField and removeField move, so a field added to
    the class or a base, by either, is found. A field replaced under its own
    name goes through addField to be found.
    """
    cls = _getcls(cls)
    held = _FOUND.get(cls)
    stamp = (_declarations, tuple(len(klass.__dict__) for klass in cls.__mro__))
    found = held.get(events) if held is not None else None
    if found is not None and found[0] == stamp:
        return list(found[1])
    wanted: 'type[FieldOrEvent]' = field.Event if events else field.Field
    items: 'dict[str, FieldOrEvent]' = {}
    for klass in reversed(cls.__mro__):
        items.update((key, value) for key, value in klass.__dict__.items()
                     if isinstance(value, wanted))
    answer: 'list[Any]' = list(items.values())
    _FOUND.setdefault(cls, {})[events] = (stamp, answer)
    return list(answer)


##def clonePROTO( cls ):
##	"""Clone the prototype/class
##
##	This allows you to create a new prototype from the
##	current prototype.  The entire prototype is cloned,
##	including all fields, and the scene graph.
##	"""
##	cls = _getcls(cls)
##	fields = [ item.clone() for item in cls.__dict__.values() if isinstance(item, field.Field)]
##	return prototype(
##		cls.PROTO,
##		fields,
##		cls.sceneGraph.clone(),
##	)


def stands_for(node: Any) -> Any:
    """The node `node` is used as

    A prototype instance stands for the first node of its body (VRML97 4.8.3,
    X3D 4.4.4), followed through an instance there; any other node, and an
    instance whose body is empty, stands for itself.
    """
    from vrml import node as nodes  # noqa: PLC0415 cycle: vrml.node star-imports this module

    followed: "list[Any]" = []
    while isinstance(node, nodes.PrototypedNode) and not any(node is seen for seen in followed):
        followed.append(node)
        body = nodes.PrototypedNode.scenegraph.fget(node)
        children = getattr(body, 'children', None) or ()
        if not children:
            break
        node = children[0]
    return node


def setSceneGraph(cls: Prototyped, sg: Any) -> Any:
    """Set the scenegraph associated with a prototype"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return node.PrototypedNode.scenegraph.fset(cls, sg)


def getSceneGraph(cls: Prototyped) -> Any:
    """Get the scenegraph associated with a prototype (or None)"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return node.PrototypedNode.scenegraph.fget(cls)


def delSceneGraph(cls: Prototyped) -> Any:
    """Delete the scenegraph associated with a prototype"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return node.PrototypedNode.scenegraph.fdel(cls)


def setExternalURL(cls: NodeOrClass, url: Any) -> Any:
    """Set the externproto URL associated with a prototype"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return node.Node.externalURL.fset(cls, url)


def getExternalURL(cls: NodeOrClass) -> Any:
    """Get the externproto URL associated with a prototype (or [])"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return node.Node.externalURL.fget(cls)


def delExternalURL(cls: NodeOrClass) -> Any:
    """Delete the externproto URL associated with a prototype"""
    from vrml import node  # noqa: PLC0415 cycle: vrml.node star-imports this module

    return node.Node.externalURL.fdel(cls)
