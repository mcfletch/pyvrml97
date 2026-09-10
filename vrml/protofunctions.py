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



from typing import Any, List
def _getcls(cls: Any) -> type:
    """Utility function returns class when passed instance or class"""
    if type(cls) is type:
        return cls
    else:
        return cls.__class__


def getPrototype(cls: Any) -> Any:
    """Return the prototype for the node or class
    returns either the argument (if it is a proto)
    or the prototype of the argument
    """
    return _getcls(cls)


def protoName(obj: Any, value: Any=None, *args: Any, **named: Any) -> Any:
    """Get/set the prototype name for the object"""
    obj = _getcls(obj)
    if value is not None:
        return setattr(obj, "PROTO", value)
    elif issubclass(obj, list):
        return '__MFNode__'
    else:
        possible = obj.PROTO
        if not possible:
            return obj.__name__.split(".")[-1]
        return possible


def defName(obj: Any, value: Any=None, *args: Any, **named: Any) -> Any:
    """Get/set the VRML97 defName for the object"""
    from vrml import node

    if value is not None:
        return node.Node.DEF.fset(obj, value, *args, **named)
    else:
        return node.Node.DEF.fget(obj, *args, **named)


def name(obj: Any, value: Any=None, *args: Any, **named: Any) -> Any:
    """Get/set prototype name for prototypes, DEF name for nodes"""
    if type(obj) is type:
        return protoName(obj, value, *args, **named)
    else:
        return defName(obj, value, *args, **named)


def root(obj: Any, value: Any=None, *args: Any, **named: Any) -> Any:
    """Get/set root-node reference for nodes/protos"""
    from vrml import node

    if value is not None:
        return node.Node.rootSceneGraph.fset(obj, value, *args, **named)
    else:
        return node.Node.rootSceneGraph.fget(obj, *args, **named)


def builtin(cls: Any) -> Any:
    """Return whether the class is "built-in" to the system"""
    from vrml import node

    return not issubclass(_getcls(cls), node.PrototypedNode)


def addField(cls: Any, field: Any) -> None:
    """Add a particular field/event to the class/prototype definition

    At present this just calls setattr(cls,field.name,field)
    """
    setattr(_getcls(cls), field.name, field)


def removeField(cls: Any, field: Any) -> None:
    """Remove a particular field/event to the class/prototype definition

    If field is a string, calls delattr(cls,field) for the class
    otherwise calls delattr( cls, field.name )
    """
    if isinstance(field, str):
        delattr(_getcls(cls), field)
    else:
        delattr(_getcls(cls), field.name)


def getField(cls: Any, field: str) -> Any:
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
    """
    cls = _getcls(cls)
    try:
        return getattr(cls, field)
    except (AttributeError, KeyError):
        # OK, may be a space-prefixed name...
        for fieldObject in getFields(cls):
            if fieldObject.name == field:
                return fieldObject
        # OK, may be an event with space-prefixed name
        for fieldObject in getFields(cls, 1):
            if fieldObject.name == field:
                return fieldObject
        # OK, may be one of the "component" events
        # of a field...
        if field.startswith("set_"):
            return getField(cls, field[4:])
        elif field.endswith("_changed"):
            return getField(cls, field[:-8])
    raise AttributeError(
        """The prototype %s does not define a field named %s"""
        % (protoName(cls), field)
    )


def getFields(cls: Any, events: int=0) -> "List[Any]":
    """Get all fields of the definition/prototype

    if events is true, then return events
    instead of fields.
    """
    cls = _getcls(cls)
    from vrml import field

    wanted: type
    if events:
        wanted = field.Event
    else:
        wanted = field.Field
    items = {}
    mro = cls.__mro__[:]
    while mro:
        items.update(
            dict(
                [
                    (key, value)
                    for key, value in mro[-1].__dict__.items()
                    if isinstance(value, wanted)
                ]
            )
        )
        mro = mro[:-1]
    return list(items.values())


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


def setSceneGraph(cls: Any, sg: Any) -> Any:
    """Set the scenegraph associated with a prototype"""
    from vrml import node

    return node.PrototypedNode.scenegraph.fset(cls, sg)


def getSceneGraph(cls: Any) -> Any:
    """Get the scenegraph associated with a prototype (or None)"""
    from vrml import node

    return node.PrototypedNode.scenegraph.fget(cls)


def delSceneGraph(cls: Any) -> Any:
    """Delete the scenegraph associated with a prototype"""
    from vrml import node

    return node.PrototypedNode.scenegraph.fdel(cls)


def setExternalURL(cls: Any, url: Any) -> Any:
    """Set the externproto URL associated with a prototype"""
    from vrml import node

    return node.Node.externalURL.fset(cls, url)


def getExternalURL(cls: Any) -> Any:
    """Get the externproto URL associated with a prototype (or [])"""
    from vrml import node

    return node.Node.externalURL.fget(cls)


def delExternalURL(cls: Any) -> Any:
    """Delete the externproto URL associated with a prototype"""
    from vrml import node

    return node.Node.externalURL.fdel(cls)
