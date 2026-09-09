import unittest
from vrml import olist
from vrml.olist import OList
from pydispatch.dispatcher import connect

class TestOList( unittest.TestCase ):
    def setUp( self ):
        self.out = []
        self.olist = olist.OList()
        connect( self.on_new, sender=self.olist )
    def on_new( self, signal, value ):
        self.out.append( (signal,value) )
    def test_append( self ):
        self.olist.append( 'this' )
        assert self.out == [('new','this')], self.out
    def test_setitem( self ):
        self.olist[:] = [ 'those','them','their' ]
        del self.out[:]
        self.olist[1] = 'that'
        assert self.out == [('del','them'),('new','that')], self.out
    def test_pop( self ):
        self.olist[:] = [ 'those','them','that' ]
        del self.out[:]
        popped = self.olist.pop( )
        assert popped == 'that', popped
        assert self.out == [('del','that')]
    def test_insert( self ):
        self.olist.insert( 0, 'those' )
        assert self.out == [('new','those')]
    def test_remove( self ):
        self.olist[:] = [ 'those','them','their' ]
        del self.out[:]
        self.olist.remove( 'those' )
        assert self.out == [('del','those')]
    def test_delslice( self ):
        self.olist[:] = [ 'those','them','their' ]
        del self.out[:]
        del self.olist[1:2]
        assert self.out == [('del','them')], self.out
    def test_setslice( self ):
        self.olist[:] = [ 'those','them','their','thou' ]
        del self.out[:]
        self.olist[1:3] = ['them','those','that','them']
        assert self.out == [('new','those'),('new','that'),('del','their')], self.out


class TestInPlaceAdd:
    """`+=` has to leave the name bound to the list.

    `__iadd__` returned whatever `__setitem__` gave back -- the value that was
    inserted -- so `items += [x]` rebound `items` to a plain list of just the
    new entries. The underlying OList was extended correctly, so nothing
    looked wrong until the next thing to watch it never fired.
    """

    def test_the_name_is_still_the_olist(self):
        items = OList([1, 2, 3])
        original = items
        items += [4, 5]
        assert items is original
        assert isinstance(items, OList)

    def test_the_entries_are_appended(self):
        items = OList([1, 2, 3])
        items += [4, 5]
        assert list(items) == [1, 2, 3, 4, 5]

    def test_extend_appends_too(self):
        items = OList([1])
        items.extend([2, 3])
        assert list(items) == [1, 2, 3]
