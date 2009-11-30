"""ROUTE and ISRoute Implementations (event-processing)"""
import traceback
from vrml import field, fieldtypes, protofunctions, node
from pydispatch import dispatcher

class ROUTE( node.Node ):
    """Representation and implementation of a VRML97 ROUTE

    This implementation uses the dispatcher module to create
    an approximation of the VRML97 event model.  It allows nodes
    to forward events via the ROUTE objects, and watches for
    event cycles.
    """
    PROTO = "ROUTE"
    source = node.SFNode('source',)
    sourceField = fieldtypes.SFString('sourceField',)
    destination = node.SFNode('destination',)
    destinationField = fieldtypes.SFString( 'destinationField',)
    def __init__( self, *arguments, **named ):
        """Initialize the route object

        Calls self.bind() after normal node.Node
        argument processing.
        """
        if arguments:
            if len(arguments) == 4:
                named['source'] = arguments[0]
                named['sourceField'] = arguments[1]
                named['destination'] = arguments[2]
                named['destinationField'] = arguments[3]
                arguments = ()
        super( ROUTE, self ).__init__( *arguments, **named )
        self.bind()
    def bind( self ):
        """Bind this ROUTE node's source to destination

        Should also setup notification for changes to our
        values to cause changes to the ROUTING table in
        dispatcher.
        """
        return self._bind( self.source, self.sourceField )
    def _bind( self, source, field ):
        """Low-level binding of the source,field key

        This method allows sub-classes to do multiple
        bindings when bind() is called.
        """
        if source and field:
            try:
                sf = protofunctions.getField( source, field )
            except (AttributeError, KeyError):
                print """%s: field %s doesn't exist on %s"""%(protofunctions.protoName(self), field, source)
            else:
                for message in ('set','del','route'):
                    dispatcher.connect(
                        receiver = self.forward,
                        sender = source,
                        signal = (message,sf),
                    )
        else:
            print """NULL ROUTE bound""", self
    def forward( 
        self, signal, sender, event=None, value=None, **arguments 
    ):
        """Forward a value update to our destination
        """
        return self._forward(
            sender, signal, 
            self.destination, self.destinationField,
            event, value, **arguments
        )
    def _forward(
        self,
        sender, signal,
        destination, destinationField,
        event=None, value=None, **arguments
    ):
        """Do the low-level forwarding of the value to a target field"""
        if event is None:
            from vrml import event as eventmodule
            event = eventmodule.Event()
        signal, sourceField = signal
        if signal == 'del':
            value = sourceField.fget( sender )
        if destination and destinationField:
            destinationField = protofunctions.getField( destination, destinationField )
            if event and hasattr(event, "visited"):
                if event.visited((destination, destinationField),):
                    ### Short-circuit before a cycle is created...
                    return
                event.visited( (destination,destinationField), 1)
            if isinstance( destinationField, field.Field ):
                try:
                    value = destinationField.fset( destination, value, notify = 0 )
                except (ValueError, TypeError):
                    traceback.print_exc()
            else:
                try:
                    value = destinationField.__set__( destination, value )
                except (ValueError, TypeError):
                    traceback.print_exc()
            dispatcher.send(
                signal = ('route',destinationField),
                sender = destination,
                value = value,
                event = event,
            )
    def copy( self, copier ):
        """Copy the route for the copier object"""
        source = self.source.copy(copier)
        destination = self.destination.copy( copier )
        return self.__class__(
            source = source,
            destination = destination,
            sourceField = self.sourceField,
            destinationField = self.destinationField,
        )
    def __str__( self ):
        """Get a friendly representation of the Node"""
        return """%s %r.%s TO %r.%s"""%(
            self.__class__.__name__,
            self.source,
            self.sourceField,
            self.destination,
            self.destinationField,
        )
        

### Field-type for multi-field route objects...
class SFRoute( node.SFNode ):
    """Single-field ROUTE value"""
    requiredTypes = (ROUTE,)

class MFRoute( node.MFNode ):
    """Multiple-value-field ROUTEs"""
    baseSFNode = SFRoute( "GeneralSFRoute" )

class IS( ROUTE ):
    """An is-mapping for a field/event

    Functionally, an instantiated IS is just a
    multi-directional ROUTE (that is, it's a route
    to and from a given field on the base node to
    the sub-nodes.
    """
    PROTO = "IS"
    def bind( self ):
        """Bind the in and out routes for the IS mapping
        """
        self._bind( self.source, self.sourceField )
        self._bind( self.destination, self.destinationField )
    def forward( self, signal, sender, event=None, value=None, **arguments ):
        """Forward a value update to our destination (or source)
        """
        if sender is self.source:
            return self._forward(
                sender, signal, 
                self.destination, self.destinationField,
                event, value, **arguments
            )
        elif sender is self.destination:
            return self._forward(
                sender, signal, 
                self.source, self.sourceField,
                event, value, **arguments
            )
        