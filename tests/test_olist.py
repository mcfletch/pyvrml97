import unittest
from vrml import olist
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
    def test_setslice( self ):
        self.olist[0:2] = [ 'those','them' ]
        assert self.out == [('new','those'),('new','them'),('del','this'),], self.out
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