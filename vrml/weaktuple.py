"""tuple sub-class which holds weak references to objects"""

import operator
import weakref
from typing import Any, Optional, SupportsIndex, Union

def _reference( item: Any ):
    """A weak reference to `item`, whether or not it is one already.

    A free function rather than a method because :meth:`WeakTuple.__new__`
    needs it before there is an instance to call a method on.
    """
    if isinstance( item, weakref.ReferenceType ):
        item = item()
    return weakref.ref( item )


class WeakTuple( tuple ):
    """tuple sub-class holding weakrefs to items

    The weak reference tuple is intended to allow you
    to store references to a list of objects without
    needing to manage weak references directly.

    For the most part, the WeakTuple operates just
    like a tuple object, in that it allows for all
    of the standard tuple operations.  The difference
    is that the WeakTuple class only stores weak
    references to its items. As a result, adding
    an object to the tuple does not necessarily mean
    that it will still be there later on during
    execution (if the referent has been garbage
    collected).

    Because WeakTuple's are static (their membership
    doesn't change), they will raise ReferenceError
    when a sub-item is missing rather than skipping
    missing items as does the WeakList.  This can
    occur for basically _any_ use of the tuple.
    """
    def __new__( cls, sequence: Any=() ):
        """Build the tuple, holding a weak reference to each item

        In ``__new__`` rather than ``__init__`` because a tuple is immutable:
        its contents are settled as it is created, and ``tuple.__init__`` is
        ``object.__init__``, which takes nothing.
        """
        return super( WeakTuple, cls).__new__(
            cls, [_reference( obj ) for obj in sequence]
        )

    def valid( self ):
        """Explicit validity check for the tuple

        Checks whether all references can be resolved,
        basically just sees whether calling list(self)
        raises a ReferenceError
        """
        try:
            list( self )
            return 1
        except ReferenceError:
            return 0

    def wrap( self, item: Any ):
        """Wrap an individual item in a weak-reference

        If the item is already a weak reference, we store
        a reference to the original item.
        """
        return _reference( item )
    def unwrap( self, item: Any ):
        """Unwrap an individual item

        This is a fairly trivial operation at the moment,
        it merely calls the item with no arguments and
        returns the result.
        """
        ref = item()
        if ref is None:
            raise ReferenceError(
                """%s instance no longer valid (item %s has been collected)"""
                % ( self.__class__.__name__, item)
            )
        return ref

    def __iter__( self ):
        """Iterate over the tuple, yielding strong references"""
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __getitem__( self, index: "Union[SupportsIndex, slice]" ) -> Any:
        """Get the item, or the items of the slice, at the given index"""
        held = super (WeakTuple,self).__getitem__( index )
        if isinstance( index, slice ):
            return [self.unwrap(obj) for obj in held]
        return self.unwrap(held)
    def __contains__( self, item: Any ):
        """Return boolean indicating whether the item is in the tuple"""
        for node in self:
            if item is node:
                return 1
        return 0
    def count( self, item: Any ):
        """Return integer count of instances of item in tuple"""
        count = 0
        for node in self:
            if item is node:
                count += 1
        return count
    def index( self, item: Any, start: "SupportsIndex" = 0,
               stop: "Optional[SupportsIndex]" = None ) -> int:
        """Return integer index of item in tuple

        By identity, as ``__contains__`` and :meth:`count` are: a node is the
        node it is, and asking a scenegraph node whether it equals another can
        mean comparing every field on it.

        Raises ValueError where there is no such item, which is what a tuple
        does and what a caller writing ``try: index(...) except ValueError``
        expects.
        """
        held = list(self)
        first = operator.index( start )
        for offset, node in enumerate( held[first:stop] ):
            if item is node:
                return first + offset
        raise ValueError(
            """%r is not in this %s"""%( item, self.__class__.__name__ )
        )

    def __add__(self, other: Any):
        """Return a new path with other as tail"""
        return tuple(self) + other

    def __eq__( self, sequence: Any ):
        """Compare the tuple to another (==)"""
        return list(self) == sequence
    def __ge__( self, sequence: Any ):
        """Compare the tuple to another (>=)"""
        return list(self) >= sequence
    def __gt__( self, sequence: Any ):
        """Compare the tuple to another (>)"""
        return list(self) > sequence

    def __le__( self, sequence: Any ):
        """Compare the tuple to another (<=)"""
        return list(self) <= sequence
    def __lt__( self, sequence: Any ):
        """Compare the tuple to another (<)"""
        return list(self) < sequence

    def __ne__( self, sequence: Any ):
        """Compare the tuple to another (!=)"""
        return list(self) != sequence

    def __repr__( self ):
        """Return a code-like representation of the weak tuple"""
        return """%s( %s )"""%( self.__class__.__name__, super(WeakTuple,self).__repr__())

