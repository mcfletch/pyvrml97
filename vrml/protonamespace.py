"""Trivial dict sub-class to hold prototype definitions"""

from typing import Any


class ProtoNamespace( dict ):
    """Simple namespace for holding prototypes"""

    def __getattr__( self, key: str ) -> Any:
        """Map attribute access to key access"""
        if key != '__contains__':
            if key in self:
                return self[ key ]
        raise AttributeError( '%r object has no %r attribute'%( self.__class__.__name__, key))
    def __copy__( self ) -> "ProtoNamespace":
        """Produce a ProtoNamespace copy of self

        A dict copies through `copy`; there is no `dict.__copy__` to defer to.
        """
        return self.__class__( self )

