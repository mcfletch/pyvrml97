"""property sub-class providing VRML field semantics"""

from typing import Any, List, Optional, TYPE_CHECKING
from pydispatch import dispatcher, robustapply
import weakref
from vrml import protonamespace

# conditional import via package entry points
try:
    from vrml_accelerate import fieldaccel2
except Exception as err:
    fieldaccel2 = None


baseFieldTypes = protonamespace.ProtoNamespace({})
baseEventTypes = protonamespace.ProtoNamespace({})

### stuff used by the various field sub-types
NUMERIC_TYPES = (int, float)
MAP_TYPE = map
ZIP_TYPE = zip
RANGE_TYPE = range
#: The lazy iterables a field coerces to a sequence before storing.
UNPACK_TYPES = (MAP_TYPE, ZIP_TYPE, RANGE_TYPE)
#: What a field will take a multi-value from.  Written as one expression, and
#: with the classes named rather than derived from a sample -- `type(map(...))`
#: *is* `map`, and a checker reading `isinstance(value, SEQUENCE_TYPES)` can
#: only narrow the value where it can see which classes are in the tuple.
SEQUENCE_TYPES = (tuple, list) + UNPACK_TYPES
_NULL: List[Any] = []


def register(cls: Any) -> None:
    """Register a new Field or Event class"""
    name = typeName(cls)
    if issubclass(cls, Event):
        dictionary = baseEventTypes
    else:
        dictionary = baseFieldTypes
    if name in dictionary:
        print(
            'Warning: redefining field-type %s from %s to %s'
            % (name, dictionary.get(name), cls)
        )
    dictionary[name] = cls


def typeName(cls: Any) -> str:
    """Get the name of a field/event"""
    if hasattr(cls, 'fieldType'):
        return cls.fieldType
    else:
        return cls.__name__.split('.')[-1]


def newField(name: str, dataType: Any, exposure: int=1, default: Any=_NULL) -> Any:
    """Create a new field with support for using strings to specify type

    name -- string name
    dataType -- string (or Field sub-class) specifying datatype
    exposure -- boolean (0/1) indicating whether this is an exposed field
    default -- default value for the field
    """
    if isinstance(dataType, (bytes, str)):
        dataType = baseFieldTypes[dataType]
    return dataType(name, exposure, default)


def newEvent(name: str, dataType: Any, direction: int=1) -> Any:
    """Create a new event object (a specialised Field)
    name -- string name
    dataType --
    direction -- 0 == in, 1 == out
    """
    if isinstance(dataType, (bytes, str)):
        dataType = baseEventTypes[dataType]
    return dataType(name, direction)


class BaseField(object):
    def __init__(self, name: str, default: Any) -> None:
        self.name = name
        self.defaultobj = default
        if callable(default):
            self.call_default = True
        else:
            self.call_default = False

    def __get__(self, client: Any, cls: Any=None) -> Any:
        """Retrieve value for given instance (or self for cls)"""
        if client is None:
            return self
        idict = client.__dict__
        current = idict.get(self.name, _NULL)
        if current is _NULL:
            return self.getDefault(client)
        return current

    fget = __get__

    def __set__(self, client: Any, value: Any) -> None:
        """Set value for given instance"""
        value = self._set(client, value)
        dispatcher.send(
            ('set', self),
            client,
            value=value,
        )
        # return value

    def fset(self, client: Any, value: Any, notify: bool=True) -> Any:
        value = self._set(client, value)
        if notify:
            dispatcher.send(
                ('set', self),
                client,
                value=value,
            )
        return value

    def _set(self, client: Any, value: Any) -> Any:
        try:
            value = self.coerce(value)
        except ValueError as x:
            raise ValueError(
                """Field %s could not accept value %s (%s)""" % (self, value, x)
            ) from x
        except TypeError as x:
            raise ValueError(
                """Field %s could not accept value %s of type %s (%s)"""
                % (self, value, type(value), x)
            ) from x
        if isinstance(client, type):
            setattr(client, self.name, value)
        else:
            client.__dict__[self.name] = value
        return value

    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type"""
        return value

    def check(self, value: Any) -> Any:
        "Whether the value is already of this field's type"
        return value

    def getDefault(self, client: Any=None) -> Any:
        """Get the default value of this field

        if client, set client's attribute to default
        without sending a notification event.
        """
        if self.call_default:
            defaultobj = self.defaultobj()
        else:
            defaultobj = self.defaultobj
        if client is not None:
            defaultobj = self._set(client, defaultobj)
        return defaultobj

    def _del(self, client: Any) -> Any:
        """Remove the client's own value and answer it

        A read answers the default again afterwards.  The counterpart of
        :meth:`_set`, and the primitive both the descriptor protocol and
        :meth:`fdel` go through -- each of those is the other's caller in one
        direction or the other, so neither can be the one that does the work.
        """
        if isinstance(client, type):
            try:
                value = getattr(client, self.name)
                delattr(client, self.name)
            except AttributeError:
                raise AttributeError(self.name) from None
        else:
            try:
                value = client.__dict__.pop(self.name)
            except KeyError:
                raise AttributeError(self.name) from None
        return value

    def __delete__(self, client: Any) -> None:
        """Delete our value from client's dictionary, and say so"""
        self.fdel(client, True)

    def fdel(self, client: Any, notify: bool=True) -> Any:
        """Delete with notify, answering the value that was there"""
        value = self._del(client)
        if notify:
            dispatcher.send(
                ('del', self),
                client,
            )
        return value



#: The Python implementation of the field primitives, under a name that always
#: reaches it.  `BaseField` is this class where the accelerator is not
#: installed and the compiled one where it is; both answer the same calls, and
#: `tests/test_basefield.py` holds the two to that.
PyBaseField = BaseField

if fieldaccel2:
    # The compiled accelerator answers the same calls and replaces it where
    # it is installed. A checker reads the Python class above, which is the
    # implementation that is always here.
    BaseField = fieldaccel2.BaseField  # type: ignore[misc]


class Field(BaseField):
    """Property sub-class with VRML field semantics

    The field basically binds a name, a dataType, and
    a default value (with some other meta-data that isn't
    actually used by the current implementation).

    Fields are normally accessed through the protofunctions
    module, which retrieves field objects from node or
    prototype objects.

    The field offers vrml.dispatcher notification of
    changes to values (see fget, fset and fdel methods).
    Which allows code to watch for those changes, a
    facility you can see in the OpenGLContext.scenegraph.cache
    module.
    """

    nodes = 0
    #: What `default` becomes when a field is declared without one. Each field
    #: type supplies its own -- `0` for an SFInt32, `""` for an SFString, the
    #: `list` constructor for a multi-valued one -- so the base says `Any`
    #: rather than letting `None` here make every one of those a narrowing.
    defaultDefault: Any = None

    def __set__(self, client: Any, value: Any) -> None:
        """Assignment goes through ``fset``, so subclasses are heard.

        The C accelerator supplies a ``__set__`` that calls a ``cdef`` setter
        directly, and a ``cdef`` method cannot be overridden from Python. On an
        accelerated build that silently skipped every field class that does real
        work when it is set -- an MFNode keeping its observable list in place so
        the scenegraph's change notifications keep flowing, an SFNode passing
        the scene root down, a weak field storing a reference. Routing
        assignment back through ``fset`` costs one Python call per *write*,
        which is the price of the two behaving the same way; reads, which
        dominate, keep the accelerated path.
        """
        self.fset(client, value, True)

    def __delete__(self, client: Any) -> None:
        """Deletion likewise, so a field that cleans up on delete still does."""
        self.fdel(client, True)

    def __init__(
        self,
        name: str,
        exposure: int=1,
        default: Any=_NULL,
    ) -> None:
        """Initialise the field object

        name -- string name
        exposure -- boolean (0/1) indicating whether this is an exposed field
        default -- default value for the field
        """
        self.exposure = exposure
        if default is _NULL:
            default = self.defaultDefault
        super(Field, self).__init__(name, default)
        self.__doc__ = str(self)

    def fhas(self, client: Any) -> bool:
        """Determine whether the client currently has a non-default value"""
        if isinstance(client, type):
            return hasattr(client, self.name)
        return self.name in client.__dict__

    def copy(self, client: Any=None, copier: Any=None) -> Any:
        """Copy this property's value/definition for client node/proto

        if client is a prototype, copy this field definition
        for use in a new prototype.

        if client is a node, and it has a set value for this
        field, then returns self.copyValue( currentValue )

        otherwise returns _NULL, a singleton object which
        shouldn't turn up anywhere else.
        """
        if isinstance(client, type):
            # copy the field definition itself...
            return self.__class__(
                self.name,
                self.exposure,
                self.copyValue(self.defaultobj, copier),
            )
        elif self.fhas(client):
            return self.copyValue(self.fget(client), copier)
        else:
            return _NULL

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return value

    def typeName(self) -> str:
        """Get the typeName of this field"""
        return typeName(self.__class__)

    def __str__(self) -> str:
        """Get a human-friendly representation of the field"""
        if self.exposure:
            exposed = "exposedField"
        else:
            exposed = "field"
        if self.defaultobj is list:
            default = '[]'
        else:
            default = str(self.defaultobj)[:20]
        return '%s %s %s %s' % (
            exposed,
            self.typeName(),
            self.name,
            default,
        )

    def vrmlstr(self, value: Any, lineariser: Any) -> Any:
        """Convert the given value to a VRML97 representation"""
        return ""

    def fieldVrmlstr(self, lineariser: Any) -> None:
        """Write the field's definition to the lineariser

        Basically this gives you a VRML97 fragment
        which can be used for creating a PROTO which
        will have the equivalent of this field available.
        """
        if self.exposure:
            exposed = "exposedField"
        else:
            exposed = "field"
        lineariser.buffer.write(
            '%s %s %s '
            % (
                exposed,
                self.typeName(),
                self.name,
            )
        )
        result = self.vrmlstr(
            # coerce is necessary because the
            # default values are often not in
            # the canonical representation
            self.coerce(self.getDefault()),
            lineariser,
        )
        if result:
            lineariser.buffer.write(result)
        return

    def watch(self, node: Any, receiver: Any, signal: Any=dispatcher.Any) -> Any:
        """Make receiver receive all update events for this field+node

        receiver( signal, sender, value=None )

            signal -- ('del',self), ('set',self) etc...
            sender -- node
            value -- new value set (for set values)
        """
        return dispatcher.connect(
            receiver=receiver,
            sender=node,
            signal=signal,
        )

    def __lt__(self, other: Any) -> Any:
        if isinstance(other, Field):
            return (self.__class__.__name__, self.name) < (
                other.__class__.__name__,
                other.name,
            )
        return False


if TYPE_CHECKING:
    class _WeakFieldHost:
        """What `WeakField` needs of the field beside it.

        `WeakField` is one half of a field type: it wraps the value in a weak
        reference on the way in and resolves it on the way out, and the
        `Field` it is combined with does the storing --
        ``class WeakSFNode(_SFNode, field.WeakField, field.Field)``.  Declaring
        the half's side of that is what lets its `super()` calls be read.

        `object` at run time, so the mix-in has the base it always had.
        """

        def fget(self, client: Any, cls: Any = None) -> Any: ...
        def fset(self, client: Any, value: Any, notify: Any = True) -> Any: ...
        def fdel(self, client: Any, notify: Any = True) -> Any: ...
else:
    _WeakFieldHost = object


class WeakField(_WeakFieldHost):
    """A Mix-in for fields which stores weak-references to values"""

    def fset(self, client: Any, value: Any, notify: int=1) -> Any:
        """Set the client's value for this property

        if notify is true send a notification event.
        """
        if isinstance(value, weakref.ReferenceType):
            value = value()
        if not value:
            if not isinstance(client, type):
                self.fdel(client, notify=notify)
            return None
        value = weakref.ref(value)
        value = super(WeakField, self).fset(client, value, notify=notify)
        return value()

    def fget(self, client: Any, cls: Any=None) -> Any:
        """Get the client's value for this property, resolving the reference

        Takes `cls` because `BaseField` aliases `fget` to `__get__`, and the
        descriptor protocol passes the owning class: an override that did not
        accept it could not stand in for the field it is mixed into.
        """
        value = super(WeakField, self).fget(client, cls)
        if not value:
            # is already default value, since refs are always non-null
            return value
        if isinstance(value, weakref.ReferenceType):
            value = value()
        # value now really is the ref'd value, or None
        if value is None:
            if not isinstance(client, type):
                self.fdel(client, notify=0)
            return None  # super( WeakField, self).fget( client )
        return value


class Event(object):
    """An Event-handling Port definition

    The event is currently non-functional, it's just
    here to allow VRML content to parse and be represented
    in-memory.
    """

    def __init__(self, name: str, direction: int=1) -> None:
        """Initialise the field object

        name -- string name
        direction -- 0 == in, 1 == out
        """
        self.name = name
        self.direction = direction

    def __set__(self, client: Any, value: Any, notify: int=1) -> None:
        """Set an event value"""
        method = getattr(client, 'on_%s' % (self.name,), None)
        if method is not None:
            robustapply.robustApply(
                method,
                value,
                event=self,
            )
        # now set as a normal property...
        client.__dict__[self.name] = value
        # and then send event letting world know...
        if notify:
            dispatcher.send(('set', self), client, value=value)

    def __get__(self, client: Any=None, cls: Any=None) -> Any:
        """Get an event's last value"""
        if client is None:
            return self
        try:
            return client.__dict__[self.name]
        except KeyError:
            raise AttributeError(
                """Event %s doesn't have a value for %s"""
                % (
                    self.name,
                    client,
                )
            ) from None

    def clone(self, name: "Optional[str]" = None, direction: Any = None) -> Any:
        """Clone this property"""
        if name is None:
            name = self.name
        if direction is None:
            direction = self.direction
        return self.__class__(name, direction)

    def typeName(self) -> str:
        """Get the typeName of this field"""
        return typeName(self.__class__)

    def __str__(self) -> str:
        """Get a human-friendly representation of the event"""
        if self.direction:
            exposed = "eventOut"
        else:
            exposed = "eventIn"
        return '%s %s %s' % (exposed, self.typeName(), self.name)

    def eventVrmlstr(self, lineariser: Any) -> Any:
        """Write the event's definition to the lineariser

        Basically this gives you a VRML97 fragment
        which can be used for creating a PROTO which
        will have the equivalent of this event available.
        """
        if self.direction:
            exposed = "eventOut"
        else:
            exposed = "eventIn"
        base = '%s %s %s' % (
            exposed,
            self.typeName(),
            self.name,
        )
        lineariser.buffer.write(base)
        return base

    def watch(self, node: Any, receiver: Any, signal: Any=dispatcher.Any) -> Any:
        """Make receiver receive all update events for this field+node

        receiver( signal, sender, value=None )

            signal -- ('del',self), ('set',self) etc...
            sender -- node
            value -- new value set (for set values)
        """
        return dispatcher.connect(
            receiver=receiver,
            sender=node,
            signal=signal,
        )
