"""list sub-class which holds weak references to objects"""

import weakref

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

        An item whose referent has been collected is left out: a list's
        membership is not fixed, so a shorter list is a sensible answer where
        :class:`~vrml.weaktuple.WeakTuple` has none and raises instead.
        """
        held = super( WeakList,self).__getitem__( slice( None ) )
        found = []
        for reference in held:
            item = reference()
            if item is not None:
                found.append( item )
        return found
    def __iter__( self ):
        """Iterate over the list, yielding strong references"""
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __setitem__( self, index, item ):
        """Set the item at the given index"""
        if isinstance( index, slice ):
            item = [self.wrap(each) for each in item]
        else:
            item = self.wrap(item)
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
        return super( WeakList, self).extend([
            self.wrap(obj) for obj in sequence
        ])
    __iadd__ = extend

    def __getitem__( self, index ):
        """Get the item, or the items of the slice, at the given index"""
        held = super (WeakList,self).__getitem__( index )
        if isinstance( index, slice ):
            return [self.unwrap(obj) for obj in held]
        return self.unwrap(held)
    def pop( self, index=-1 ):
        """Pop an item from the list, removing it and returning it"""
        return self.unwrap( super(WeakList,self).pop(index))

    def __contains__( self, item ):
        """Return boolean indicating whether the item is in the list"""
        return item in self.get()
    def count( self, item ):
        """Return integer count of instances of item in list"""
        return self.get().count(item)
    def index( self, item, start = 0, stop = None ):
        """Return integer index of item in list

        Raises ValueError where there is no such item, as `list.index` does.
        """
        found = self.get()
        if stop is None:
            return found.index(item, start)
        return found.index(item, start, stop)
    def remove( self, item ):
        """Remove the given item from the list"""
        t = self.get()
        result = t.remove( item )
        self[:] = t
        return result
    def sort( self, *, key = None, reverse = False ):
        """Sort the referents, then rebuild the list of references

        Takes ``key`` and ``reverse``, as :meth:`list.sort` does.  Sorting the
        references themselves would order them by address, which is no order at
        all from the caller's side.
        """
        found = self.get()
        found.sort( key = key, reverse = reverse )
        self[:] = found
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
        def remove(reference, selfref=weakref.ref(self)):  # noqa: B008 - the default is the weak ref
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

