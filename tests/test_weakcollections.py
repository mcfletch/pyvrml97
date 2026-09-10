"""The weak sequences node paths are built from.

A scenegraph holds a path to a node as a sequence of the nodes along it, and it
must not be the thing that keeps them alive: a path left over from a previous
frame would otherwise pin a whole subtree. So the path is a sequence of weak
references that answers with strong ones.

``WeakList`` skips an item whose referent has gone; ``WeakTuple`` raises
``ReferenceError``, because its membership is fixed and there is no sensible
shorter tuple to answer with.
"""

import copy
import gc
import unittest

from vrml.protonamespace import ProtoNamespace
from vrml.weaklist import WeakList
from vrml.weaktuple import WeakTuple


class Thing(object):
    """Something weak-referenceable with an order, so sorting has meaning."""

    def __init__(self, number):
        self.number = number

    def __repr__(self):
        return 'Thing(%s)' % (self.number,)

    def __lt__(self, other):
        return self.number < other.number


class TestWeakList(unittest.TestCase):
    def setUp(self):
        self.items = [Thing(3), Thing(1), Thing(2)]
        self.weak = WeakList(self.items)

    def test_it_answers_with_the_objects_themselves(self):
        self.assertEqual(list(self.weak), self.items)

    def test_get_answers_strong_references(self):
        self.assertEqual(self.weak.get(), self.items)

    def test_membership_is_by_the_referent(self):
        self.assertIn(self.items[0], self.weak)
        self.assertNotIn(Thing(99), self.weak)

    def test_it_counts_referents(self):
        self.assertEqual(self.weak.count(self.items[0]), 1)

    def test_it_finds_the_index_of_a_referent(self):
        self.assertEqual(self.weak.index(self.items[1]), 1)

    def test_it_sorts_the_referents_and_keeps_them_weak(self):
        self.weak.sort()
        self.assertEqual([thing.number for thing in self.weak], [1, 2, 3])

    def test_it_sorts_by_a_key(self):
        self.weak.sort(key=lambda thing: -thing.number)
        self.assertEqual([thing.number for thing in self.weak], [3, 2, 1])

    def test_it_removes_a_referent(self):
        self.weak.remove(self.items[1])
        self.assertEqual([thing.number for thing in self.weak], [3, 2])

    def test_a_slice_answers_strong_references(self):
        self.assertEqual(self.weak[:2], self.items[:2])

    def test_a_collected_item_drops_out(self):
        """Skipping it is the whole difference from WeakTuple."""
        held = [Thing(1), Thing(2)]
        weak = WeakList(held + [Thing(3)])
        gc.collect()
        self.assertEqual(weak.get(), held)


class TestWeakTuple(unittest.TestCase):
    def setUp(self):
        self.items = [Thing(3), Thing(1), Thing(2)]
        self.weak = WeakTuple(self.items)

    def test_it_can_be_built(self):
        self.assertEqual(len(self.weak), 3)

    def test_it_answers_with_the_objects_themselves(self):
        self.assertEqual(list(self.weak), self.items)

    def test_indexing_answers_a_strong_reference(self):
        self.assertIs(self.weak[0], self.items[0])

    def test_a_slice_answers_strong_references(self):
        self.assertEqual(self.weak[1:], self.items[1:])

    def test_membership_is_by_the_referent(self):
        self.assertIn(self.items[2], self.weak)
        self.assertNotIn(Thing(99), self.weak)

    def test_it_counts_referents(self):
        self.assertEqual(self.weak.count(self.items[2]), 1)

    def test_it_finds_the_index_of_a_referent(self):
        self.assertEqual(self.weak.index(self.items[1]), 1)

    def test_valid_says_whether_every_referent_is_still_there(self):
        self.assertTrue(self.weak.valid())

    def test_a_collected_item_makes_it_invalid_rather_than_shorter(self):
        weak = WeakTuple([Thing(1)])
        gc.collect()
        self.assertFalse(weak.valid())

    def test_reaching_a_collected_item_raises_reference_error(self):
        """The documented failure, and the reason `valid` exists."""
        weak = WeakTuple([Thing(1)])
        gc.collect()
        with self.assertRaises(ReferenceError):
            list(weak)


class TestProtoNamespaceCopies(unittest.TestCase):
    """`copy.copy` on one, which is how a scene graph copies its prototypes."""

    def test_it_copies_to_its_own_class(self):
        original = ProtoNamespace({'Wheel': object, 'Axle': object})
        duplicate = copy.copy(original)
        self.assertIsInstance(duplicate, ProtoNamespace)
        self.assertEqual(dict(duplicate), dict(original))
        self.assertIsNot(duplicate, original)

    def test_the_copy_is_independent(self):
        original = ProtoNamespace({'Wheel': object})
        duplicate = copy.copy(original)
        duplicate['Axle'] = object
        self.assertNotIn('Axle', original)


if __name__ == '__main__':
    unittest.main()
