"""Base-class for scenegraph nodes

Requires Python 2.2.x, as it makes
extensive use of properties
"""

from typing import Any, Callable, Tuple
from vrml import field, fieldtypes
#: The two node field types here are halves of a field type in the same way
#: the ones in `fieldtypes` are, and need the same thing of the `field.Field`
#: they are combined with.
from vrml.fieldtypes import _FieldHost
from vrml import copier as copiermodule
from vrml import olist
from vrml.protofunctions import *
from pydispatch import dispatcher
import weakref


class Node(object):
    #: Bound after `RootScenegraphNode` exists; see the foot of this module.
    rootSceneGraph: Any
    """A generic scene graph node

    Unlike earlier versions of the library,
    this implementation of the Node class is
    basically a regular python class.  This is
    possible because it uses the python 2.2.x
    property/descriptor API extensively.

    Technically this is a multiple-hierarchy DAG
    node, as there can be any number of node
    children attributes, and nodes may appear
    multiple times in the hierarchy.

    Attributes of note:
        " DEF" field
            a simple string field which stores the
            DEF name of a node instance
        " scenegraph" attribute
            pointer to the node's implementation
            scenegraph (at the moment, this is not
            actually used for anything)
        " PROTO" attribute
            stores the PROTO name of the node
        externalURL attribute
            stores the MFString url for the node's
            externproto definition if appropriate
        toString method
            convenience access to the lineariser
            to give VRML97-formatted representation of
            the node
    """

    DEF = fieldtypes.SFString(' DEF', 1, '')
    # scenegraph = None # will be created below...
    # rootSceneGraph = None # will be created below
    externalURL = fieldtypes.MFString('externalURL', 1)
    PROTO = ""

    def __init__(self, **namedarguments: Any) -> None:
        """Initialise the node with appropriate named args

        All properties/attributes must be specified with
        named arguments, and the property/attribute must
        exist within the Node's class/prototype.

        This will raise AttributeError/ValueError/TypeError
        if the values or the property names are inappropriate.

        Note that all Node objects have the attribute/property
            exposedField SFString DEF ""
        defined.  You may therefore specify a DEF name by
        passing it as a named argument.
        """
        for key, value in namedarguments.items():
            try:
                f = getField(self, key)
            except AttributeError:
                raise AttributeError(
                    """Unrecognised attribute %r for node type %r"""
                    % (key, self.__class__.__name__)
                ) from None
            else:
                if not (hasattr(f, '__get__') and hasattr(f, '__set__')):
                    raise TypeError(
                        """Attempt to set a non-field attribute %s to %s for node type %s"""
                        % (key, value, self.__class__.__name__)
                    )
                f.fset(self, value)

    def __str__(self) -> str:
        """Get a friendly representation of the Node"""
        # The field is declared as `DEF` and stored under `' DEF'`, so the
        # stored name is the one to look for.
        if ' DEF' in self.__dict__ and defName(self):
            return """%s( DEF=%r @0x%X )""" % (
                self.__class__.__name__,
                defName(self),
                id(self),
            )
        else:
            return """%s( @0x%X )""" % (
                self.__class__.__name__,
                id(self),
            )

    def __repr__(self) -> str:
        """Get a code-like representation of the Node

        Basically every attribute except for sub-nodes values
        are returned as a full representation.
        """
        attributes = []
        for each_field in getFields(self):
            if each_field.name in self.__dict__:
                value = getattr(self, each_field.name)
                if isinstance(value, Node):
                    representation = str(value)
                else:
                    representation = repr(value)
                attributes.append(
                    """%s = %s"""
                    % (
                        each_field.name,
                        representation,
                    )
                )

        return """%s(\n\t%s\n)""" % (
            self.__class__.__name__,
            ",\n\t".join(attributes),
        )

    def copy(self, copier: Any=None) -> Any:
        """Copy this node for copier"""
        if copier is None:
            copier = copiermodule.Copier()
        previous = copier.use(self)
        if previous is not None:
            return previous
        dictionary = {}
        for each_field in getFields(self):
            if each_field.fhas(self):
                dictionary[each_field.name] = each_field.copy(self, copier)
        newNode = type(self).__new__(type(self))
        newNode.__dict__.update(dictionary)
        copier.use(self, newNode)
        return newNode

    def toString(self, **namedargs: Any) -> Any:
        '''Generate a VRML 97-syntax string representing this Prototype
        **namedargs -- key:value
            passed arguments for the linearisation object
        see lineariser4.Lineariser
        '''
        from vrml.vrml97 import linearise

        return linearise.linearise(self, **namedargs)


class PrototypedNode(object):
    #: Bound after `SFNode` exists; see the foot of this module.
    scenegraph: Any
    """Prototyped node mix-in

    Note the presence of a " scenegraph" property
    for the node created below (due to mutual dependencies).
    This is filled by the instantiate method to provide the
    actual implementation of the node.
    """

    def __init__(self, *arguments: Any, **namedarguments: Any) -> None:
        """Initialise the node with appropriate named args

        Also attempts to instantiate the sub-node scenegraph
        for the PrototypedNode
        """
        PrototypedNode.instantiate(self)
        super(PrototypedNode, self).__init__(*arguments, **namedarguments)

    def instantiate(self) -> None:
        """Make a copy of the class scenegraph-template for this node

        Also needs to bind IS mappings/routes for the template,
        and negotiate not-yet-loaded external prototypes and
        the like.
        """
        from vrml import route

        isMappings = None
        for cls in self.__class__.__mro__[:-1]:
            template = PrototypedNode.scenegraph.fget(cls)
            if template:
                # use ismaps for the instantiated scenegraph
                isMappings = list(ismaps(cls).items())
                break
        if isMappings is None:
            # no scenegraph defined...
            from vrml.vrml97 import scenegraph

            template = scenegraph.SceneGraph()
            PrototypedNode.scenegraph.fset(cls, template)
            isMappings = []
        # 			raise ValueError( """Attempting to instantiate a prototyped node with no scenegraph defined: %s"""%( self,))

        copier = copiermodule.Copier()
        sg = template.copy(copier)
        for fieldName, mappings in isMappings:
            sourceField = getField(self, fieldName)
            hasDefault = hasattr(sourceField, 'getDefault')
            default = sourceField.getDefault() if hasDefault else None
            for destination, destinationField in mappings:
                # The mappings name the *prototype's* nodes, and this
                # instance's body is a copy of those -- so the wiring has to
                # reach the copy the copier just made, or every instance
                # would write into the one body they were all copied from.
                copied = copier.use(destination)
                if copied is not None:
                    destination = copied
                sg.routes.append(
                    route.IS(
                        source=self,
                        sourceField=fieldName,
                        destination=destination,
                        destinationField=destinationField,
                    )
                )
                if hasDefault:
                    try:
                        getField(destination, destinationField).fset(
                            destination,
                            default,
                            notify=0,
                        )
                    except AttributeError:
                        pass
        PrototypedNode.scenegraph.fset(self, sg)

    def renderedChildren(self, types: Any=None) -> Any:
        """Get the rendered children of the scenegraph"""
        if types:
            return [
                node
                for node in PrototypedNode.scenegraph.fget(self).children
                if isinstance(node, types)
            ]
        else:
            return PrototypedNode.scenegraph.fget(self).children


def prototype(
    name: str,
    fields: Any=(),
    sceneGraph: Any=None,
    externalURL: Any=None,
    baseClasses: Any=(PrototypedNode, Node),
) -> type:
    """Build a new prototype class

    name -- string name
    fields -- sequence of vrml.field objects
    sceneGraph -- the source scenegraph for prototyped nodes
    externalURL -- MFString URL or None
    baseClasses -- base classes for the new class
    """
    environment = {
        'PROTO': name,
    }
    for each_field in fields:
        environment[each_field.name] = each_field
    returnValue = type(
        name,
        baseClasses,
        environment,
    )
    if sceneGraph is not None:
        setSceneGraph(returnValue, sceneGraph)
    if externalURL is not None:
        setExternalURL(returnValue, externalURL)
    return returnValue


class NullNode(Node):
    '''NULL SFNode value
    There should only be a single NULL instance for
    any particular system.  It should, for all intents and
    purposes just sit there inertly
    '''

    PROTO = 'NULL'

    def __repr__(self) -> str:
        """Get code-like representation of NULL node"""
        return '<NULL vrml SFNode>'

    def __bool__(self) -> bool:
        """Make the NULL node evaluate to false"""
        return False

    def __eq__(self, other: Any) -> bool:
        """Whether `other` is a NULL node as well"""
        try:
            return bool(protoName(self) == protoName(other))
        except (AttributeError, TypeError, ValueError):
            return False        # not a node, so not this one

    def __hash__(self) -> int:
        """The same for every NULL, as equality is

        Hashable because a copier keeps the nodes it has copied in a
        dictionary, and NULL turns up in one wherever a node field is empty.
        """
        return hash(self.PROTO)

    def clone(self) -> Any:
        """Replicate the null object (return another pointer to it)"""
        return self

    def __str__(self) -> str:
        """Get a human-friendly representation of the NULL node"""
        return "NULL"


NULL = NullNode()


class _SFNode(_FieldHost):
    """Base-class for SFNode-type fields

    The optionally restricted SFNode field type
    allows a node to hold a reference to another node
    within the directed acyclic graph.

    There are two primary attributes:

        requiredTypes -- a type or tuple of types that
            are acceptable as values for the field
        allowNULL -- whether to allow the NULL node as
            a value for the field
    """

    nodes = 1
    #: The types a value must be one of, or empty for no constraint.
    #: Set per field -- `SFNode.requiredTypes = (Node,)` below -- so the
    #: empty tuple here must not fix the element type.
    requiredTypes: Tuple[type, ...] = ()
    allowNULL = 1

    def fset(self, client: Any, value: Any, notify: int=1) -> Any:
        """Set the client's value for this property

        notify -- if true send a notification event

        The SFNode tries to update the value's root
        attribute to point to the root of the client
        *iff* the value doesn't currently point at
        a valid root.  (That is, it only updates root
        if there is no current root).  This is done
        without sending notify events.
        """
        value = super(_SFNode, self).fset(client, value, notify)
        if value:
            _passRootDown(client, [value])
        return value

    def defaultDefault(self) -> Any:
        """Default SFNode value"""
        return NULL

    def coerce(self, value: Any) -> Any:
        """Coerce value to an SFNode reference"""
        if self.requiredTypes and isinstance(value, self.requiredTypes):
            return value
        elif value is None and self.allowNULL:
            return NULL
        elif isinstance(value, str):
            raise ValueError(
                """SFNode field %s was set to a string, not currently supported: %s"""
                % (self, value[:30])
            )
        elif isinstance(value, field.UNPACK_TYPES):
            # No length to measure until the values are drawn out.
            return self.coerce(list(value))
        elif isinstance(value, (tuple, list)) and len(value) == 1:
            return self.coerce(value[0])
        elif not self.requiredTypes:
            return value
        else:
            raise ValueError(
                """Attempted to set value for an %s field which is not compatible: %s, needed instance of %s"""
                % (self.name, repr(value), self.requiredTypes)
            )

    def vrmlstr(self, value: Any, lineariser: Any) -> Any:
        """Convert the given value to a VRML97 representation"""
        return lineariser._linear(value)

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy the node this field points at

        A node's copy is a copy all the way down: a field that pointed at the
        original's child would give the copy no child of its own, so writing
        to one would be seen through the other -- and each instance of a
        prototype is a copy of its body.

        `copier` is what keeps a node reached twice one node in the copy,
        which is what DEF/USE and a prototype's IS wiring both need.
        """
        if value is None or value is NULL:
            return value
        if copier is None:
            copier = copiermodule.Copier()
        return value.copy(copier)


class SFNode(_SFNode, field.Field):
    """(Restricted) SFNode type

    This is the publically available SFNode type,
    a sub-class of _SFNode and field.Field
    """


SFNode.requiredTypes = (Node,)


class SFNodeEvt(_SFNode, field.Event):
    fieldType = 'SFNode'


field.register(SFNode)
field.register(SFNodeEvt)


# `WeakField` and `Field` each carry an `fget`, and this takes the weak one by
# putting it first: reading the field resolves the reference rather than
# answering it.
class WeakSFNode(_SFNode, field.WeakField, field.Field):
    """Weak-referenced SFNode field-type"""

    fieldType = 'WeakSFNode'

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Point at the same node the original pointed at

        What a weak field holds is not part of the node holding it -- the
        scene root a node points back at is the file it is in -- so a copy
        belongs to the same one rather than to a copy of the whole file.
        """
        return value


class RootScenegraphNode(WeakSFNode):
    fieldType = 'RootScenegraphNode'

    def fset(self, client: Any, value: Any, notify: int=1) -> Any:
        """Set the root scenegraph node (recursively)

        TODO: this will blow up on cyclic graphs!
        """
        result = super(RootScenegraphNode, self).fset(client, value, notify)
        for each_field in getFields(client.__class__):
            if (
                isinstance(each_field, SFNode)
                and not isinstance(each_field, RootScenegraphNode)
                and each_field is not PrototypedNode.scenegraph
            ):
                try:
                    child = each_field.__get__(client)
                except ValueError:
                    pass
                else:
                    self.fset(child, value, notify=False)
            elif isinstance(each_field, MFNode):
                try:
                    for child in each_field.__get__(client):
                        self.fset(child, value, notify=False)
                except AttributeError:
                    pass
            elif each_field.name == ' DEF':
                try:
                    DEF = each_field.__get__(client)
                    if DEF:
                        # An unnamed node has no name to register, and an
                        # entry under the empty string would answer
                        # `getDEF('')` with whichever node was last put in.
                        value.regDefName(DEF, client)
                except AttributeError:
                    pass
        return result


field.register(WeakSFNode)
field.register(RootScenegraphNode)

# Attached here rather than in the class bodies: `SFNode` needs `Node`,
# and these two fields need `SFNode`, so the cycle is broken by binding
# them once both exist. The annotations above say they belong to the
# classes all the same.
PrototypedNode.scenegraph = SFNode(' scenegraph', 1, NULL)
Node.rootSceneGraph = RootScenegraphNode(' root', 1, NULL)
assert PrototypedNode.scenegraph.name == " scenegraph", PrototypedNode.scenegraph.name
assert Node.rootSceneGraph.name == " root", Node.rootSceneGraph.name


def _passRootDown(client: Any, values: Any) -> None:
    """Give each of `values` the client's scene root, where it has none

    A node learns which file it is in from whatever it is attached to, and
    that is how the DEF names and the prototype declarations reach it. Only a
    node with no root of its own is given one, so that attaching a node that
    belongs to another scene does not take it out of that one.

    Anything in `values` that is not a node is passed over: an observable list
    holds routes as readily as nodes, and a field with no required types holds
    whatever it was given.
    """
    clientRoot = Node.rootSceneGraph.fget(client)
    if not clientRoot:
        return
    for value in values:
        if isinstance(value, Node) and not Node.rootSceneGraph.fget(value):
            Node.rootSceneGraph.fset(value, clientRoot, notify=0)


def _changeSender(nodeRef: Any, field: Any) -> "Callable[..., Any]":
    """Utility function to send node-change messages on olist updates"""

    def onOListChange(sender: Any, signal: Any, value: Any) -> None:
        client = nodeRef()
        if client:
            if signal == olist.OList.NEW_CHILD_EVT:
                # A child appended to the list is attached as much as one
                # assigned into it, so it learns the scene the same way.
                _passRootDown(client, [value])
            dispatcher.send(
                ('set', field),
                client,
                value=sender,
                subsignal=signal,
                subvalue=value,
            )

    return onOListChange


class _MFNode(_FieldHost):
    """(Restricted) MFNode field-type-definition"""

    nodes = 1
    defaultDefault = olist.OList
    baseSFNode = SFNode('GeneralSFNode')
    baseObjectType = olist.OList

    def fset(self, client: Any, value: Any, notify: int=1) -> Any:
        """Set the client's value for this property

        notify -- if true send a notification event

        The MFNode tries to update the value's root
        attribute to point to the root of the client
        *iff* the value doesn't currently point at
        a valid root.  (That is, it only updates root
        if there is no current root).  This is done
        without sending notify events.
        """
        previous = client.__dict__.get(self.name)
        if previous is not None:
            previous[:] = self.coerce(value)
            value = previous
        else:
            value = super(_MFNode, self).fset(client, value, notify)
            # register for updates to the list...
            # we just send "changed" events for the field whenever
            # there's an update to the list... a bit wasteful, as
            # our clients might want to know about just the changed
            # values, but for now...
            value.setSender(client, field=self)
            cs = _changeSender(weakref.ref(client), self)
            dispatcher.connect(
                cs,
                sender=client,
                signal=olist.OList.DEL_CHILD_EVT,
                weak=False,  # don't weakref receiver so it will hang around...
            )
            dispatcher.connect(
                cs,
                sender=client,
                signal=olist.OList.NEW_CHILD_EVT,
                weak=False,  # don't weakref receiver so it will hang around...
            )
        if value:
            _passRootDown(client, value)
        return value

    def getDefault(self, client: Any=None) -> Any:
        """The empty child list a node starts with, wired to that node.

        A field read before it is ever written materialises its default here,
        and for an MFNode that default *is* the observable list its node's
        children live in. Installed the quick way it arrives with no idea which
        node it belongs to, and everything that list does afterwards -- every
        child added or removed -- is announced by a bare list that no listener
        recognises. So the default goes in through ``fset`` like any other
        value, quietly: arriving at a default is not a change anyone asked to
        be told about.
        """
        if self.call_default:
            defaultobj = self.defaultobj()
        else:
            defaultobj = self.defaultobj
        if client is not None and not isinstance(client, type):
            defaultobj = self.fset(client, defaultobj, notify=0)
        return defaultobj

    def coerce(self, value: Any) -> Any:
        """Coerce value to an MFNode list-of-objects"""
        SF = self.__class__.baseSFNode
        if SF.requiredTypes and isinstance(value, SF.requiredTypes):
            return self.baseObjectType([value])
        elif not value:
            return self.baseObjectType([])
        elif isinstance(value, field.SEQUENCE_TYPES):
            return self.baseObjectType([SF.coerce(item) for item in value])
        else:
            raise ValueError(
                """Attempted to set value for an %s field which is not compatible: %s"""
                % (self.name, repr(value))
            )

    def vrmlstr(self, value: Any, lineariser: Any) -> Any:
        """Convert the given value to a VRML97 representation"""
        return lineariser._mfnode(value)

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        SF = self.__class__.baseSFNode
        return [SF.copyValue(node, copier) for node in value]


##class WeakMFNode( MFNode ):
##	"""Weak-referencing version of an MFNode field-type"""
##	baseObjectType = weaklist.WeakList
##	fieldType = 'WeakMFNode'


class MFNode(_MFNode, field.Field):
    """MFNode Field class"""


class MFNodeEvt(_MFNode, field.Event):
    """MFNode Event class"""

    fieldType = 'MFNode'


field.register(MFNode)
##field.register( WeakMFNode )
field.register(MFNodeEvt)

#: Which of a prototype's fields each node's own fields are wired to, keyed
#: weakly on the node so an entry does not keep a scene graph alive.
ISMAPS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def ismaps(node: Any) -> Any:
    """Get the isMaps for the given node

    Returns a field-name:(sub-node,field) mapping
    Not currently functional
    """
    current = ISMAPS.setdefault(node, {})
    return current
