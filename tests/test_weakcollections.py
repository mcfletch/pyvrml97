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
import weakref

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


class TestComparingAWeakList(unittest.TestCase):
    """A weak list compares as the list of referents it stands for."""

    def setUp(self):
        self.items = [Thing(1), Thing(2)]
        self.weak = WeakList(self.items)

    def test_it_equals_the_list_of_its_referents(self):
        self.assertTrue(self.weak == self.items)

    def test_it_differs_from_another_list(self):
        self.assertTrue(self.weak != [Thing(9)])

    def test_it_orders_against_a_plain_list(self):
        shorter = self.items[:1]
        self.assertTrue(self.weak > shorter)
        self.assertTrue(self.weak >= shorter)
        self.assertTrue(shorter < self.weak)
        self.assertTrue(shorter <= self.weak)

    def test_it_orders_below_a_longer_list(self):
        longer = self.items + [Thing(3)]
        self.assertTrue(self.weak < longer)
        self.assertTrue(self.weak <= longer)
        self.assertFalse(self.weak < self.items)
        self.assertTrue(self.weak <= self.items)

    def test_its_representation_names_the_class_and_the_referents(self):
        shown = repr(self.weak)
        self.assertIn('WeakList', shown)
        self.assertIn('Thing(1)', shown)


class TestBuildingAWeakList(unittest.TestCase):
    """Each way of putting an item in wraps it, and each way of taking one out
    resolves it."""

    def setUp(self):
        self.held = [Thing(1), Thing(2), Thing(3)]
        self.weak = WeakList(self.held[:1])

    def test_append_stores_a_reference_and_answers_the_object(self):
        self.weak.append(self.held[1])
        self.assertEqual(list(self.weak), self.held[:2])

    def test_insert_puts_it_where_it_was_asked_for(self):
        self.weak.insert(0, self.held[1])
        self.assertEqual(list(self.weak), [self.held[1], self.held[0]])

    def test_setting_one_item_replaces_it(self):
        self.weak[0] = self.held[2]
        self.assertEqual(list(self.weak), [self.held[2]])

    def test_pop_takes_the_object_out(self):
        self.assertIs(self.weak.pop(), self.held[0])
        self.assertEqual(list(self.weak), [])

    def test_index_searches_between_a_start_and_a_stop(self):
        weak = WeakList(self.held)
        self.assertEqual(weak.index(self.held[2], 1, 3), 2)

    def test_extend_stores_a_reference_to_each(self):
        self.weak.extend(self.held[1:])
        self.assertEqual(list(self.weak), self.held)

    def test_what_extend_added_is_held_weakly_too(self):
        weak = WeakList()
        going = Thing(9)
        weak.extend([going])
        del going
        gc.collect()
        self.assertEqual(len(weak), 0)

    def test_a_referent_taken_out_twice_over_is_not_reported(self):
        """The callback that removes a dead reference can run after the list
        has already dropped it, and it has nobody to raise to."""
        weak = WeakList()
        going = Thing(9)
        weak.append(going)
        reference = list.__getitem__(weak, 0)
        callback = reference.__callback__
        del going
        gc.collect()
        self.assertIsNone(callback(reference))

    def test_wrapping_a_reference_stores_what_it_points_at(self):
        """A caller may hand over a reference rather than the object."""
        weak = WeakList([weakref.ref(self.held[0])])
        self.assertEqual(list(weak), [self.held[0]])


class TestComparingAWeakTuple(unittest.TestCase):
    def setUp(self):
        self.items = [Thing(1), Thing(2)]
        self.weak = WeakTuple(self.items)

    def test_it_equals_the_list_of_its_referents(self):
        self.assertTrue(self.weak == self.items)

    def test_it_differs_from_another_list(self):
        self.assertTrue(self.weak != [Thing(9)])

    def test_it_orders_against_a_plain_list(self):
        shorter = self.items[:1]
        self.assertTrue(self.weak > shorter)
        self.assertTrue(self.weak >= shorter)
        self.assertTrue(shorter < list(self.weak))
        self.assertTrue(self.weak <= self.items)

    def test_adding_answers_a_plain_tuple(self):
        """The membership of a WeakTuple is fixed, so a sum is not one."""
        third = Thing(3)
        self.assertEqual(self.weak + (third,), tuple(self.items) + (third,))

    def test_its_representation_names_the_class(self):
        self.assertIn('WeakTuple', repr(self.weak))

    def test_looking_for_something_it_does_not_hold_raises(self):
        with self.assertRaises(ValueError):
            self.weak.index(Thing(9))

    def test_wrapping_a_reference_stores_what_it_points_at(self):
        held = Thing(1)
        self.assertEqual(list(WeakTuple([weakref.ref(held)])), [held])
