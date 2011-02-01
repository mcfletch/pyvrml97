"""list sub-class which holds weak references to objects"""
from __future__ import generators
import weakref
import types

class WeakList( list ):
    """list sub-class holding weakrefs to items

    The weak reference list is intended to allow you
    to store references to a list of objects without
    needing to manage weak references directly.

    For the most part, the WeakList operates just
    like a list object, in that it allows for all
    of the standard list operations.  The difference
    is that the WeakList class only stores weak
    references to its items. As a result, adding
    an object to the list does not necessarily mean
    that it will still be there later on during
    execution (if the referent has been garbage
    collected).
    """
    def __init__( self, sequence=() ):
        """Initialize the list, with an optional sequence of objects

        The WeakList will store weak references to objects
        within the sequence.
        """
        super( WeakList, self).__init__( map( self.wrap, sequence))
    def wrap( self, item ):
        """Wrap an individual item in a weak-reference

        If the item is already a weak reference, we store
        a reference to the original item.  We use approximately
        the same weak reference callback mechanism as the
        standard weakref.WeakKeyDictionary object.
        """
        if isinstance( item, weakref.ReferenceType ):
            item = item()
        return weakref.ref( item, self.__remover() )
    def unwrap( self, item ):
        """Unwrap an individual item

        This is a fairly trivial operation at the moment,
        it merely calls the item with no arguments and
        returns the result.
        """
        return item()

    def get( self ):
        """Get all items as a list of strong references
        """
        return map(
            self.unwrap,
            super( WeakList,self).__getslice__(0,len(self))
        )
    def __iter__( self ):
        """Iterate over the list, yielding strong references"""
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __setitem__( self, index, item ):
        """Set the item at the given index"""
        if isinstance( index, types.SliceType ):
            item = [self.wrap(x) for x in item]
        else:
            item = self.wrap(x)
        return super( WeakList,self).__setitem__(
            index, item
        )
    
    def append( self, item ):
        """Append a single item to the list"""
        return super( WeakList,self).append( self.wrap(item))
    def insert( self, index, item ):
        """Insert an item at the given index"""
        return super( WeakList,self).insert(
            index, self.wrap(item)
        )
    def extend( self, sequence ):
        """Extend this list with another sequence"""
        return super( WeakList, self).extend( map( self.wrap, sequence ))
    __iadd__ = extend

    def __getitem__( self, index ):
        """Get the item at the given index"""
        return self.unwrap(super (WeakList,self).__getitem__( index))
    def pop( self, index=-1 ):
        """Pop an item from the list, removing it and returning it"""
        return self.unwrap( super(WeakList,self).pop(index))

    def __contains__( self, item ):
        """Return boolean indicating whether the item is in the list"""
        return item in self.get()
    def count( self, item ):
        """Return integer count of instances of item in list"""
        return self.get().count(item)
    def index( self, item ):
        """Return integer index of item in list"""
        return self.get().index(item)
    def remove( self, item ):
        """Remove the given item from the list"""
        t = self.get()
        result = t.remove( item )
        self[:] = t
        return result
    def sort( self, function = None):
        """Sort the list of objects

        This sorts the objects referenced,
        then rebuilds the list of references!
        """
        t = self.get()
        if function is not None:
            result = t.sort( function )
        else:
            result = t.sort( )
        self[:] = t
        return result
    def __eq__( self, sequence ):
        """Compare the list to another (==)"""
        return self.get() == sequence
    def __ge__( self, sequence ):
        """Compare the list to another (>=)"""
        return self.get() >= sequence
    def __gt__( self, sequence ):
        """Compare the list to another (>)"""
        return self.get() > sequence
        
    def __le__( self, sequence ):
        """Compare the list to another (<=)"""
        return self.get() <= sequence
    def __lt__( self, sequence ):
        """Compare the list to another (<)"""
        return self.get() < sequence

    def __ne__( self, sequence ):
        """Compare the list to another (!=)"""
        return self.get() != sequence

    def __repr__( self ):
        """Return a code-like representation of the weak list"""
        return """%s( %s )"""%( self.__class__.__name__, repr(self.get()))

    def __remover(self):
        """Construct a function callback for eliminating a particular reference"""
        def remove(reference, selfref=weakref.ref(self)):
            """Removes passed reference from the referenced self (selfref)
            Note that the callback does not keep the list alive.
            This approach is taken directly from the WeakKeyDictionary.
            """
            self = selfref()
            if self is not None:
                try:
                    super( WeakList, self).remove( reference )
                except (ValueError, TypeError, NameError):
                    pass
        return remove
        
