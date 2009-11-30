"""tuple sub-class which holds weak references to objects"""
from __future__ import generators
import weakref

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
    def __init__( self, sequence=() ):
        """Initialize the tuple

        The WeakTuple will store weak references to objects
        within the sequence.
        """
        super( WeakTuple, self).__init__( map( self.wrap, sequence))

    def valid( self ):
        """Explicit validity check for the tuple

        Checks whether all references can be resolved,
        basically just sees whether calling list(self)
        raises a ReferenceError
        """
        try:
            list( self )
            return 1
        except weakref.ReferenceError:
            return 0
        
    def wrap( self, item ):
        """Wrap an individual item in a weak-reference

        If the item is already a weak reference, we store
        a reference to the original item.  We use approximately
        the same weak reference callback mechanism as the
        standard weakref.WeakKeyDictionary object.
        """
        if isinstance( item, weakref.ReferenceType ):
            item = item()
        return weakref.ref( item )
    def unwrap( self, item ):
        """Unwrap an individual item

        This is a fairly trivial operation at the moment,
        it merely calls the item with no arguments and
        returns the result.
        """
        ref = item()
        if ref is None:
            raise weakref.ReferenceError( """%s instance no longer valid (item %s has been collected)"""%( self.__class__.__name__, item))
        return ref

    def __iter__( self ):
        """Iterate over the tuple, yielding strong references"""
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __getitem__( self, index ):
        """Get the item at the given index"""
        return self.unwrap(super (WeakTuple,self).__getitem__( index ))
    def __getslice__( self, start, stop ):
        """Get the items in the range start to stop"""
        return map(
            self.unwrap,
            super (WeakTuple,self).__getslice__( start, stop)
        )
    def __contains__( self, item ):
        """Return boolean indicating whether the item is in the tuple"""
        for node in self:
            if item is node:
                return 1
        return 0
    def count( self, item ):
        """Return integer count of instances of item in tuple"""
        count = 0
        for node in self:
            if item is node:
                count += 1
        return count
    def index( self, item ):
        """Return integer index of item in tuple"""
        count = 0
        for node in self:
            if item is node:
                return count
            count += 1
        return -1

    def __add__(self, other):
        """Return a new path with other as tail"""
        return tuple(self) + other
    
    def __eq__( self, sequence ):
        """Compare the tuple to another (==)"""
        return list(self) == sequence
    def __ge__( self, sequence ):
        """Compare the tuple to another (>=)"""
        return list(self) >= sequence
    def __gt__( self, sequence ):
        """Compare the tuple to another (>)"""
        return list(self) > sequence
        
    def __le__( self, sequence ):
        """Compare the tuple to another (<=)"""
        return list(self) <= sequence
    def __lt__( self, sequence ):
        """Compare the tuple to another (<)"""
        return list(self) < sequence

    def __ne__( self, sequence ):
        """Compare the tuple to another (!=)"""
        return list(self) != sequence

    def __repr__( self ):
        """Return a code-like representation of the weak tuple"""
        return """%s( %s )"""%( self.__class__.__name__, super(WeakTuple,self).__repr__())
        