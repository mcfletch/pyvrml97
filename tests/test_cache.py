"""What a renderer keeps beside a node, and when it is thrown away.

A display list, a texture object, a compiled array -- none of it belongs on
the node, and all of it has to go the moment the node it was built from
changes or is collected. The cache is what holds it: keyed by the node's
identity, invalidated from the field notifications the node already sends,
and let go of by weak reference when the node is.

`vrml/cache.py`'s module docstring says what it is for; this says what it
does.
"""

import gc
import unittest

from vrml import cache, field, node


class Watched(node.Node):
    PROTO = 'Watched'
    size = field.newField('size', 'SFFloat', 1, 1.0)
    label = field.newField('label', 'SFString', 1, '')


class TestKeepingSomethingBesideANode(unittest.TestCase):
    def setUp(self):
        self.cache = cache.Cache()
        self.node = Watched()

    def test_what_was_put_there_reads_back(self):
        self.cache.holder(self.node, 'compiled')
        self.assertEqual(self.cache.getData(self.node), 'compiled')

    def test_a_node_nothing_was_kept_for_answers_the_default(self):
        self.assertIsNone(self.cache.getData(Watched()))
        self.assertEqual(self.cache.getData(Watched(), default='none'), 'none')

    def test_a_key_nobody_used_answers_the_default(self):
        self.cache.holder(self.node, 'compiled')
        self.assertIsNone(self.cache.getData(self.node, 'shadow'))

    def test_two_keys_are_two_things(self):
        """Which is what the key is for: a shadow's compilation and a
        geometry's are both kept for the one node."""
        self.cache.holder(self.node, 'geometry', 'shape')
        self.cache.holder(self.node, 'shadow map', 'shadow')
        self.assertEqual(self.cache.getData(self.node, 'shape'), 'geometry')
        self.assertEqual(self.cache.getData(self.node, 'shadow'), 'shadow map')

    def test_the_holder_reads_back_too(self):
        held = self.cache.holder(self.node, 'compiled')
        self.assertIs(self.cache.getHolder(self.node), held)

    def test_a_node_nothing_was_kept_for_has_no_holder(self):
        self.assertIsNone(self.cache.getHolder(Watched()))

    def test_a_value_can_be_replaced_after_it_is_held(self):
        held = self.cache.holder(self.node, 'first')
        held.set('second')
        self.assertEqual(self.cache.getData(self.node), 'second')


class TestThrowingItAway(unittest.TestCase):
    def setUp(self):
        self.cache = cache.Cache()
        self.node = Watched()

    def test_a_changed_field_clears_what_depended_on_it(self):
        held = self.cache.holder(self.node, 'compiled')
        held.depend(self.node, 'size')
        self.node.size = 2.0
        self.assertIsNone(self.cache.getData(self.node))

    def test_a_field_named_as_bytes_is_the_same_field(self):
        """A generated module may name one either way."""
        held = self.cache.holder(self.node, 'compiled')
        held.depend(self.node, b'size')
        self.node.size = 3.0
        self.assertIsNone(self.cache.getData(self.node))

    def test_a_field_object_may_be_named_instead_of_its_name(self):
        held = self.cache.holder(self.node, 'compiled')
        held.depend(self.node, Watched.size)
        self.node.size = 4.0
        self.assertIsNone(self.cache.getData(self.node))

    def test_a_deleted_field_clears_it_too(self):
        """Deleting a field puts its default back, which is as much a change
        as writing one."""
        self.node.size = 2.0
        held = self.cache.holder(self.node, 'compiled')
        held.depend(self.node, 'size')
        del self.node.size
        self.assertIsNone(self.cache.getData(self.node))

    def test_a_field_nothing_depended_on_leaves_it_alone(self):
        held = self.cache.holder(self.node, 'compiled')
        held.depend(self.node, 'size')
        self.node.label = 'renamed'
        self.assertEqual(self.cache.getData(self.node), 'compiled')

    def test_removing_it_says_it_found_one(self):
        held = self.cache.holder(self.node, 'compiled')
        self.assertEqual(held(), 1)
        self.assertIsNone(self.cache.getData(self.node))

    def test_removing_it_twice_says_there_was_nothing_the_second_time(self):
        held = self.cache.holder(self.node, 'compiled')
        held()
        self.assertEqual(held(), 0)

    def test_removing_the_last_key_drops_the_node_from_the_cache(self):
        held = self.cache.holder(self.node, 'compiled')
        held()
        self.assertNotIn(id(self.node), self.cache)

    def test_removing_one_of_two_keys_keeps_the_other(self):
        first = self.cache.holder(self.node, 'geometry', 'shape')
        self.cache.holder(self.node, 'shadow map', 'shadow')
        first()
        self.assertEqual(self.cache.getData(self.node, 'shadow'), 'shadow map')

    def test_a_holder_whose_cache_is_gone_removes_nothing(self):
        """The cache is held weakly, so a holder can outlive it -- and asking
        one to remove itself then has nowhere to remove itself from."""
        store = cache.Cache()
        held = store.holder(self.node, 'compiled')
        held.cache = lambda: None       # the weak reference, now empty
        self.assertEqual(held(), 0)

    def test_a_holder_whose_client_is_gone_removes_nothing(self):
        held = self.cache.holder(self.node, 'compiled')
        held.client = lambda: None
        self.assertEqual(held(), 0)


class TestDependingOnANodeItself(unittest.TestCase):
    """`depend` with no field is a dependency on the node still being there."""

    def test_a_node_that_goes_away_takes_the_entry_with_it(self):
        held = cache.Cache().holder(Watched(), 'compiled')
        watched = Watched()
        held.depend(watched)
        self.assertEqual(len(held.nodeDependencies), 1)

    def test_the_client_going_away_empties_the_cache_for_it(self):
        store = cache.Cache()
        going = Watched()
        store.holder(going, 'compiled')
        client_id = id(going)
        del going
        gc.collect()
        self.assertNotIn(client_id, store)


class TestTheProcessWideCache(unittest.TestCase):
    """`cache.CACHE` is the one for data that depends on the node alone."""

    def test_its_reader_is_the_module_level_name(self):
        self.assertEqual(cache.getData.__self__, cache.CACHE)

    def test_something_kept_in_it_reads_back_through_that_name(self):
        held = Watched()
        cache.CACHE.holder(held, 'compiled')
        try:
            self.assertEqual(cache.getData(held), 'compiled')
        finally:
            cache.CACHE.pop(id(held), None)


if __name__ == '__main__':
    unittest.main()
