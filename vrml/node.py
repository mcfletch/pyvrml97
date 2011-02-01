"""Base-class for scenegraph nodes

Requires Python 2.2.x, as it makes
extensive use of properties
"""
from vrml import field, fieldtypes, weaklist, weakkeydictfix
from vrml import copier as copiermodule
from vrml import olist
from vrml.protofunctions import *
from pydispatch import dispatcher
import weakref

class Node( object ):
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
    DEF = fieldtypes.SFString(' DEF',1, '')
    #scenegraph = None # will be created below...
    #rootSceneGraph = None # will be created below
    externalURL = fieldtypes.MFString( 'externalURL', 1)
    PROTO = ""
    def __init__( self, **namedarguments ):
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
        for key,value in namedarguments.items():
            try:
                f = getField(self, key)
            except AttributeError:
                raise AttributeError( """Unrecognised attribute %r for node type %r"""%(key, self.__class__.__name__))
            else:
                if not (hasattr( f, '__get__') and hasattr( f, '__set__')):
                    raise TypeError ("""Attempt to set a non-field attribute %s to %s for node type %s"""%(key, value, self.__class__.__name__))
                f.fset( self, value )
    def __str__( self ):
        """Get a friendly representation of the Node"""
        if 'DEF' in self.__dict__ and defName(self):
            return """%s( DEF=%r @0x%X )"""%(
                self.__class__.__name__,
                defName( self ),
                id(self),
            )
        else:
            return """%s( @0x%X )"""%(
                self.__class__.__name__,
                id(self),
            )
    def __repr__( self ):
        """Get a code-like representation of the Node

        Basically every attribute except for sub-nodes values
        are returned as a full representation.
        """
        attributes = []
        for field in getFields( self ):
            if field.name in self.__dict__:
                value = getattr( self, field.name)
                if isinstance( value, Node ):
                    representation = str(value)
                else:
                    representation = repr( value)
                attributes.append (
                    """%s = %s"""%(
                        field.name,
                        representation,
                    )
                )
                
        return """%s(\n\t%s\n)"""%(
            self.__class__.__name__,
            ",\n\t".join(attributes),
        )
    def copy( self, copier=None ):
        """Copy this node for copier"""
        if copier is None:
            copier = copiermodule.Copier()
        previous = copier.use( self )
        if previous is not None:
            return previous
        dictionary = {}
        for field in getFields( self ):
            if field.fhas( self ):
                dictionary[field.name] = field.copy( self, copier )
        newNode = type(self).__new__( type(self))
        newNode.__dict__.update( dictionary )
        copier.use( self, newNode )
        return newNode

    def toString( self, **namedargs ):
        '''Generate a VRML 97-syntax string representing this Prototype
        **namedargs -- key:value
            passed arguments for the linearisation object
        see lineariser4.Lineariser
        '''
        from vrml.vrml97 import linearise
        return linearise.linearise( self, **namedargs )

class PrototypedNode( object ):
    """Prototyped node mix-in

    Note the presence of a " scenegraph" property
    for the node created below (due to mutual dependencies).
    This is filled by the instantiate method to provide the
    actual implementation of the node.
    """
    def __init__( self, *arguments, **namedarguments ):
        """Initialise the node with appropriate named args

        Also attempts to instantiate the sub-node scenegraph
        for the PrototypedNode
        """
        PrototypedNode.instantiate(self)
        super( PrototypedNode, self).__init__( *arguments, **namedarguments )
    def instantiate( self ):
        """Make a copy of the class scenegraph-template for this node

        Also needs to bind IS mappings/routes for the template,
        and negotiate not-yet-loaded external prototypes and
        the like.
        """
        from vrml import route
        isMappings = None
        for cls in self.__class__.__mro__[:-1]:
            template = PrototypedNode.scenegraph.fget( cls )
            if template:
                # use ismaps for the instantiated scenegraph
                isMappings = ismaps(cls).items()
                break
        if isMappings is None:
            # no scenegraph defined...
            from vrml.vrml97 import scenegraph
            template = scenegraph.SceneGraph()
            PrototypedNode.scenegraph.fset( cls, template )
            isMappings = []
#			raise ValueError( """Attempting to instantiate a prototyped node with no scenegraph defined: %s"""%( self,))

        copier = copiermodule.Copier()
        sg = template.copy( copier )
        for fieldName, mappings in isMappings:
            sourceField = getField( self, fieldName )
            for (destination, destinationField) in mappings:
                r = route.IS(
                    source = self,
                    sourceField = fieldName,
                    destination = destination,
                    destinationField = destinationField,
                )
                sg.routes.append( r )
            if hasattr( sourceField, 'getDefault' ):
                default = sourceField.getDefault()
                try:
                    getField( destination, destinationField ).fset(
                        destination,
                        default,
                        notify = 0,
                    )
                except AttributeError:
                    pass
        PrototypedNode.scenegraph.fset( self, sg )
    def renderedChildren( self, types = None ):
        """Get the rendered children of the scenegraph"""
        if types:
            return [
                node for node in PrototypedNode.scenegraph.fget( self ).children
                if isinstance(node, types )
            ]
        else:
            return PrototypedNode.scenegraph.fget( self ).children
            

def prototype(
    name,
    fields=(),
    sceneGraph=None,
    externalURL= None,
    baseClasses = (PrototypedNode, Node),
):
    """Build a new prototype class

    name -- string name
    fields -- sequence of vrml.field objects
    sceneGraph -- the source scenegraph for prototyped nodes
    externalURL -- MFString URL or None
    baseClasses -- base classes for the new class
    """
    environment = {
        'PROTO':name,
    }
    for field in fields:
        environment[field.name] = field
    returnValue = type(
        name,
        baseClasses,
        environment,
    )
    if sceneGraph is not None:
        setSceneGraph( returnValue, sceneGraph )
    if externalURL is not None:
        setExternalURL( returnValue, externalURL )
    return returnValue

class NullNode(Node):
    '''NULL SFNode value
    There should only be a single NULL instance for
    any particular system.  It should, for all intents and
    purposes just sit there inertly
    '''
    PROTO = 'NULL'
    def __repr__(self):
        """Get code-like representation of NULL node"""
        return '<NULL vrml SFNode>'
    def __nonzero__(self ):
        """Make the NULL node evaluate to false"""
        return 0
    def __eq__( self, other ):
        """Compare the NULL node to other objects"""
        try:
            if protoName( self ) == protoName( other ):
                return 0
        except (AttributeError,TypeError,ValueError):
            return -1 # could be 1, doesn't really matter
    def clone( self ):
        """Replicate the null object (return another pointer to it)"""
        return self
    def __str__( self ):
        """Get a human-friendly representation of the NULL node"""
        return "NULL"
    __repr__ = __str__

NULL = NullNode()

class _SFNode( object ):
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
    name = "SFNode"
    nodes = 1
    requiredTypes = ()
    allowNULL = 1

    def fset( self, client, value, notify = 1 ):
        """Set the client's value for this property

        notify -- if true send a notification event

        The SFNode tries to update the value's root
        attribute to point to the root of the client
        *iff* the value doesn't currently point at
        a valid root.  (That is, it only updates root
        if there is no current root).  This is done
        without sending notify events.
        """
        value = super( _SFNode, self).fset( client, value, notify )
        if value:
            clientRoot = Node.rootSceneGraph.fget( client )
            if clientRoot:
                valueRoot = Node.rootSceneGraph.fget( value )
                if not valueRoot:
                    Node.rootSceneGraph.fset( value, clientRoot, notify=0)
        return value

    def defaultDefault( self ):
        """Default SFNode value"""
        return NULL
    def coerce( self, value ):
        """Coerce value to an SFNode reference"""
        if self.requiredTypes and isinstance( value, self.requiredTypes ):
            return value
        elif value is None and self.allowNULL:
            return NULL
        elif isinstance( value, str ):
            raise ValueError(
                """SFNode field %s was set to a string, not currently supported: %s"""%(
                    self, value[:30]
                )
            )
        elif isinstance( value, field.SEQUENCE_TYPES ) and len(value) == 1:
            return self.coerce( value[0])
        elif not self.requiredTypes:
            return value
        else:
            raise ValueError( """Attempted to set value for an %s field which is not compatible: %s, needed instance of %s"""%( self.name, repr(value), self.requiredTypes ))
    def vrmlstr( self, value, lineariser):
        """Convert the given value to a VRML97 representation"""
        return lineariser._linear( value )

class SFNode( _SFNode, field.Field ):
    """(Restricted) SFNode type

    This is the publically available SFNode type,
    a sub-class of _SFNode and field.Field
    """
SFNode.requiredTypes = (Node,)

class SFNodeEvt( _SFNode, field.Event ):
    fieldType = 'SFNode'

field.register( SFNode )
field.register( SFNodeEvt )

class WeakSFNode( _SFNode, field.WeakField, field.Field):
    """Weak-referenced SFNode field-type"""
    fieldType = 'WeakSFNode'

class RootScenegraphNode( WeakSFNode ):
    fieldType = 'RootScenegraphNode'
    def fset( self, client, value, notify = 1 ):
        """Set the root scenegraph node (recursively)
        
        TODO: this will blow up on cyclic graphs!
        """
        result = super( RootScenegraphNode, self ).fset( 
            client, value, notify 
        )
        for field in getFields( client.__class__ ):
            if isinstance( field, SFNode ) and not isinstance( field, RootScenegraphNode ):
                try:
                    child = field.__get__( client )
                except ValueError, err:
                    pass 
                else:
                    self.fset( child, value, notify=False )
            elif isinstance( field, MFNode ):
                try:
                    for child in field.__get__( client ):
                        self.fset( child, value, notify=False )
                except AttributeError, err:
                    pass 
            elif field.name == ' DEF':
                try:
                    DEF = field.__get__( client )
                    value.regDefName( DEF, client )
                except AttributeError, err:
                    pass 
field.register( WeakSFNode )
field.register( RootScenegraphNode )

PrototypedNode.scenegraph = SFNode(' scenegraph', 1, NULL)
Node.rootSceneGraph = RootScenegraphNode(
    ' root',
    1,
    NULL
)

def _changeSender( nodeRef, field ):
    """Utility function to send node-change messages on olist updates"""
    def onOListChange( sender, signal, value ):
        client = nodeRef()
        if client:
            dispatcher.send( 
                ('set',field), 
                client, 
                value=sender, 
                subsignal=signal, 
                subvalue=value,
            )
    return onOListChange

class _MFNode( object ):
    """(Restricted) MFNode field-type-definition"""
    nodes = 1
    defaultDefault = olist.OList
    baseSFNode = SFNode('GeneralSFNode')
    baseObjectType = olist.OList
    def fset( self, client, value, notify = 1 ):
        """Set the client's value for this property

        notify -- if true send a notification event

        The MFNode tries to update the value's root
        attribute to point to the root of the client
        *iff* the value doesn't currently point at
        a valid root.  (That is, it only updates root
        if there is no current root).  This is done
        without sending notify events.
        """
        previous = client.__dict__.get( self.name )
        if previous is not None:
            previous[:] = self.coerce(value)
            value = previous 
        else:
            value = super( _MFNode, self).fset( client, value, notify )
            # register for updates to the list...
            # we just send "changed" events for the field whenever 
            # there's an update to the list... a bit wasteful, as 
            # our clients might want to know about just the changed 
            # values, but for now...
            value.setSender( client, field=self )
            cs = _changeSender( weakref.ref( client ), self )
            dispatcher.connect( 
                cs, 
                sender = client,
                signal = olist.OList.DEL_CHILD_EVT,
                weak=False, # don't weakref receiver so it will hang around...
            )
            dispatcher.connect( 
                cs, 
                sender = client,
                signal = olist.OList.NEW_CHILD_EVT,
                weak=False, # don't weakref receiver so it will hang around...
            )
        if value:
            clientRoot = Node.rootSceneGraph.fget( client )
            if clientRoot:
                for val in value:
                    valueRoot = Node.rootSceneGraph.fget( val )
                    if not valueRoot:
                        Node.rootSceneGraph.fset( val, clientRoot, notify=0)
        return value
        
    def coerce( self, value ):
        """Coerce value to an MFNode list-of-objects"""
        SF = self.__class__.baseSFNode
        if SF.requiredTypes and isinstance( value, SF.requiredTypes ):
            return self.baseObjectType([value])
        elif not value:
            return self.baseObjectType([])
        elif isinstance( value, field.SEQUENCE_TYPES ):
            return self.baseObjectType([
                SF.coerce( item)
                for item in value
            ])
        else:
            raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.name, repr(value)))
    def vrmlstr( self, value, lineariser):
        """Convert the given value to a VRML97 representation"""
        return lineariser._mfnode( value )
    def copyValue( self, value, copier=None ):
        """Copy a value for copier"""
        SF = self.__class__.baseSFNode
        return [ SF.copyValue( node, copier ) for node in value ]

##class WeakMFNode( MFNode ):
##	"""Weak-referencing version of an MFNode field-type"""
##	baseObjectType = weaklist.WeakList
##	fieldType = 'WeakMFNode'

class MFNode( _MFNode, field.Field ):
    """MFNode Field class"""
class MFNodeEvt( _MFNode, field.Event ):
    """MFNode Event class"""
    fieldType = 'MFNode'

field.register( MFNode )
##field.register( WeakMFNode )
field.register( MFNodeEvt )

ISMAPS = weakkeydictfix.WeakKeyDictionary()
def ismaps( node ):
    """Get the isMaps for the given node

    Returns a field-name:(sub-node,field) mapping
    Not currently functional
    """
    current = ISMAPS.setdefault(node, {})
    return current
