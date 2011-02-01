"""Observable list class"""
from pydispatch.dispatcher import send
import weakref, types
try:
    set 
except NameError, err:
    from sets import Set as set

class OList( list ):
    """List sub-class which generates pydispatch events on changes
    
    Generates 4 types of events:
    
        * NEW_CHILD_EVT, from self, with value=child, for each added child
        * NEW_PARENT_EVT, from child, with parent=self, for each added child 
        * DEL_CHILD_EVT, from self, with value=child, for each removed child 
        * DEL_PARENT_EVT, from child, with parent=self, for each removed child
        
    Note that the OList semantics are a little loose currently, as 
    it sometimes acts as though adding a new duplicate child is not 
    an event and sometimes acts as though it is.  This doesn't cause 
    problems for the OpenGLContext scenegraph.
    
    The OList is intended for situations where slow-write-fast-read 
    is the primary requirement, it allows you to hook writing events 
    in order to recalculate/cache values.
    """
    NEW_CHILD_EVT = 'new'
    NEW_PARENT_EVT = 'added'
    DEL_CHILD_EVT = 'del'
    DEL_PARENT_EVT = 'removed'
    sender = None
    extraArgs = None
    def setSender( self, sender, **named ):
        """Set the (node) from which messages should be sent"""
        if sender is not None:
            sender = weakref.ref(sender)
        self.sender = sender
        self.extraArgs = named
    def _sender( self ):
        sender = self
        if self.sender is not None:
            sender = self.sender()
            if sender is None:
                sender = self
        return sender
    def _sendAdded( self, value ):
        """Send events for adding value to self"""
        sender = self._sender()
        send( self.NEW_CHILD_EVT, sender, value=value, **(self.extraArgs or {}))
        send( self.NEW_PARENT_EVT, value, parent=sender,**(self.extraArgs or {}))
    def _sendRemoved( self, value ):
        """Send events for removing value from self"""
        sender = self._sender()
        send( self.DEL_CHILD_EVT, sender, value=value,**(self.extraArgs or {}))
        send( self.DEL_PARENT_EVT, value, parent=sender,**(self.extraArgs or {}))
    
    def append( self, value ):
        """Append a value and send a message"""
        super( OList,self ).append( value )
        self._sendAdded( value )
        return value 
    def insert( self, index, value ):
        """Insert a new item at index"""
        super( OList,self ).insert( index, value )
        self._sendAdded( value )
        return value 
    def pop( self, index=None ):
        """Pop a single item out of the list"""
        if index is None:
            index = len(self)-1
        value = super( OList,self ).pop( index )
        self._sendRemoved( value )
        return value
    def remove( self, item ):
        """Remove this instance from the list"""
        super(OList,self).remove( item )
        self._sendRemoved( item )
        return item
    def __delitem__( self, index ):
        """Delete a single item"""
        if isinstance( index, types.SliceType ):
            current = self.__getitem__( index )
            for value in current:
                self._sendRemoved( value )
            super( OList,self ).__delitem__( index )
            return current 
        else:
            value = self[index]
            self._sendRemoved( value )
        return value
    def __delslice__( self, i,j):
        return self.__delitem__( slice(i,j))
    def __setitem__( self, index, value ):
        """Set a value and send a message"""
        if isinstance( index, types.SliceType ):
            values = list(value)
            previous = self.__getitem__( index )
            currents = set( previous )
            super(OList,self).__setitem__( index, values )
            for value in values:
                if value not in currents:
                    self._sendAdded( value )
                else:
                    try:
                        previous.remove( value )
                    except ValueError, err:
                        pass
            for current in previous:
                self._sendRemoved( current )
            return values 
        else:
            current = self[index]
            if current is not value:
                self._sendRemoved( current )
            super( OList,self ).__setitem__( index, value )
            if current is not value:
                self._sendAdded( value )
            return value 
    def __setslice__( self, i,j, iterable ):
        return self.__setitem__( slice(i,j), iterable)
    def __iadd__( self, iterable ):
        """Do an in-place add"""
        return self.__setitem__( slice(len(self),len(self)), iterable )
    extend = __iadd__
    
