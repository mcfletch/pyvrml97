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


class TestDeletingOneItem(unittest.TestCase):
    """`del olist[0]` announces the item that went, as every other way of
    taking one out does."""

    def setUp(self):
        self.out = []
        self.olist = olist.OList(['first', 'second'])
        connect(self.on_change, sender=self.olist)

    def on_change(self, signal, value):
        self.out.append((signal, value))

    def test_it_is_announced(self):
        del self.olist[0]
        self.assertEqual(self.out, [('del', 'first')])

    def test_the_item_is_gone(self):
        del self.olist[0]
        self.assertEqual(list(self.olist), ['second'])


class TestWhereTheAnnouncementComesFrom(unittest.TestCase):
    """A list announces itself unless it was told which node it belongs to,
    and it holds that node weakly."""

    def test_by_default_the_list_is_the_sender(self):
        held = olist.OList()
        self.assertIs(held._sender(), held)

    def test_a_named_sender_is_used_instead(self):
        held = olist.OList()
        owner = TestWhereTheAnnouncementComesFrom
        held.setSender(owner)
        self.assertIs(held._sender(), owner)

    def test_a_sender_that_has_gone_leaves_the_list_as_the_sender(self):
        held = olist.OList()
        held.setSender(None)
        held.sender = lambda: None      # the weak reference, now empty
        self.assertIs(held._sender(), held)


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


class TestExtendAndInPlaceAdd(unittest.TestCase):
    """The two answer different things, as `list`'s do.

    `items += [x]` binds the name to whatever `__iadd__` answers, so that one
    has to answer the list itself. `extend` answers nothing, which is what
    `list.extend` does and what a caller writing `x = items.extend(...)`
    would otherwise get a list from.
    """

    def setUp(self):
        self.messages = []

        class Watched(olist.OList):
            def _sendAdded(inner, value):
                self.messages.append(('added', value))

            def _sendRemoved(inner, value):
                self.messages.append(('removed', value))

        self.list = Watched([1, 2])

    def test_extend_answers_nothing(self):
        self.assertIsNone(self.list.extend([3, 4]))

    def test_extend_adds_the_items(self):
        self.list.extend([3, 4])
        self.assertEqual(list(self.list), [1, 2, 3, 4])

    def test_extend_announces_each_item(self):
        self.list.extend([3, 4])
        self.assertEqual(self.messages, [('added', 3), ('added', 4)])

    def test_in_place_add_answers_the_list_itself(self):
        original = self.list
        self.list += [3]
        self.assertIs(self.list, original)
        self.assertEqual(list(self.list), [1, 2, 3])

    def test_in_place_add_announces_the_item(self):
        self.list += [3]
        self.assertEqual(self.messages, [('added', 3)])
