from pydispatch.dispatcher import send
_NULL = object()

cdef class BaseField( object ):
    cdef public str name
    cdef public object defaultobj
    cdef public int call_default
    def __init__( self, str name, object default ):
        """Initialize the BaseField parameters"""
        self.name = name 
        self.defaultobj = default
        if hasattr(default, '__call__' ):
            self.call_default = True
        else:
            self.call_default = False
    def __get__( self, client, cls ):
        """Retrieve value for given instance (or self for cls)"""
        cdef dict idict
        cdef object current 
        if client is None:
            return self 
        idict = client.__dict__
        current = idict.get( self.name, _NULL )
        if current is _NULL:
            return self.getDefault( client )
        return current 
    def __set__( self, client, value ):
        """Set value for given instance (notifies)"""
        self._set( client, value, True )
    def __del__( self, client=None ):
        """Delete our value from client's dictionary (notifies)"""
        if client is not None:
            self._del( client, True )
    # Protocols with notification suppression...
    def fset( self, client, value, int notify=True ):
        """Set value, with option to notify"""
        return self._set( client, value, bool(notify) )
    def fdel( self, client, int notify=True ):
        """Delete with option to notify"""
        return self._del( client, bool(notify) )
    fget = __get__ 
        
    def coerce( self, value ):
        """Coerce the given value to our type"""
        return value
    def check( self, value ):
        "Raise ValueError if isn't correct type"
        return value
    def getDefault( self, client = None ):
        """Get the default value of this field

        if client, set client's attribute to default
        without sending a notification event.
        """
        cdef object defaultobj
        if self.call_default:
            defaultobj = self.defaultobj()
        else:
            defaultobj = self.defaultobj
        if client is not None:
            defaultobj = self._set( client, defaultobj, 0 )
        return defaultobj

    cdef _del(self, client, int notify):
        """Delete the value, with notifications"""
        try:
            value = client.__dict__.pop( self.name )
        except KeyError, err:
            raise AttributeError( self.name )
        if notify:
            send(
                ('del',self), 
                client, 
            )
        return value
    cdef _set(self, client, value, int notify ):
        """Set value to give value, with coercion"""
        try:
            value = self.coerce( value )
        except ValueError, x:
            raise ValueError( """Field %s could not accept value %s (%s)"""%( self, value, x))
        except TypeError, x:
            raise ValueError( """Field %s could not accept value %s of type %s (%s)"""%( self, value, type(value), x))
        if isinstance( client, type ):
            setattr( client, self.name, value )
        else:
            client.__dict__[self.name] = value
        if notify:
            send( 
                ('set',self), 
                client, 
                value=value,
            )
        return value 
