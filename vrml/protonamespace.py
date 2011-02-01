"""Trivial dict sub-class to hold prototype definitions"""
class ProtoNamespace( dict ):
    """Simple namespace for holding prototypes"""
    def __getattr__( self, key ):
        """Map attribute access to key access"""
        if key != '__contains__':
            if key in self:
                return self[ key ]
        raise AttributeError( '%r object has no %r attribute'%( self.__class__.__name__, key))
    def __copy__( self ):
        """Produce a ProtoNamespace copy of self"""
        return self.__class__( super(ProtoNamespace,self).__copy__())
    
