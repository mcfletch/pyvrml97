"""Copying a node, and what "a copy" has to mean.

A copy is what a program gets when it duplicates part of a scene, and it is
also how a PROTO is instantiated: the prototype's body is copied once per
instance. So a copy has to be a copy all the way down -- change one and the
other stays as it was -- and at the same time a node reached twice in the
original has to be one node in the copy, because that is what DEF/USE and a
prototype's IS wiring mean. `Copier` is what holds both of those at once.

`tests/test_scenegraph.py` covers copying a whole graph;
`tests/test_routes_and_protofunctions.py` covers copying a ROUTE.
"""

import unittest

from vrml import copier as copiermodule
from vrml import node, protofunctions
from vrml.vrml97 import basenodes
from vrml.vrml97.parser import buildParser
from vrml.vrml97.scenegraph import SceneGraph

PARSER = buildParser()


def read(text):
    """The scene a VRML97 source builds."""
    return PARSER.parse(text)[1][1]


class TestCopyingOneNode(unittest.TestCase):
    def test_the_copy_is_another_node(self):
        original = basenodes.Transform()
        self.assertIsNot(original.copy(), original)

    def test_it_is_of_the_same_type(self):
        self.assertIsInstance(basenodes.Sphere().copy(), basenodes.Sphere)

    def test_a_value_that_was_set_comes_with_it(self):
        original = basenodes.Transform(translation=(1, 2, 3))
        self.assertEqual(list(original.copy().translation), [1.0, 2.0, 3.0])

    def test_a_value_that_was_not_set_is_still_the_default(self):
        self.assertEqual(list(basenodes.Transform().copy().scale),
                         [1.0, 1.0, 1.0])

    def test_the_def_name_comes_with_it(self):
        original = basenodes.Transform(DEF='Shared')
        self.assertEqual(protofunctions.defName(original.copy()), 'Shared')

    def test_a_copier_is_made_when_none_is_given(self):
        self.assertIsNotNone(basenodes.Transform().copy())


class TestCopyingGoesAllTheWayDown(unittest.TestCase):
    """A copy that shared its children would not be a copy: writing to one
    would be seen through the other."""

    def scene(self):
        child = basenodes.Shape(geometry=basenodes.Sphere(radius=1.0))
        return child, basenodes.Transform(children=[child])

    def test_a_child_is_copied_rather_than_shared(self):
        child, parent = self.scene()
        self.assertIsNot(parent.copy().children[0], child)

    def test_writing_to_the_copy_leaves_the_original_alone(self):
        child, parent = self.scene()
        parent.copy().children[0].geometry.radius = 5.0
        self.assertAlmostEqual(child.geometry.radius, 1.0, places=5)

    def test_a_grandchild_is_copied_too(self):
        child, parent = self.scene()
        self.assertIsNot(parent.copy().children[0].geometry, child.geometry)

    def test_a_single_node_field_is_copied(self):
        geometry = basenodes.Sphere(radius=1.0)
        shape = basenodes.Shape(geometry=geometry)
        self.assertIsNot(shape.copy().geometry, geometry)

    def test_a_null_field_stays_null(self):
        """NULL is the one node there is only ever one of."""
        self.assertIs(basenodes.Shape().copy().geometry, node.NULL)


class TestANodeReachedTwice(unittest.TestCase):
    """DEF and USE put one node in two places, and the copy has to keep it
    one node."""

    def scene(self):
        shared = basenodes.Transform(DEF='Shared')
        return shared, basenodes.Group(children=[shared, shared])

    def test_it_is_one_node_in_the_copy_as_well(self):
        shared, group = self.scene()
        copied = group.copy()
        self.assertIs(copied.children[0], copied.children[1])

    def test_and_it_is_not_the_original(self):
        shared, group = self.scene()
        self.assertIsNot(group.copy().children[0], shared)

    def test_a_named_node_and_the_graphs_name_for_it_are_the_same_copy(self):
        shared = basenodes.Transform()
        scene = SceneGraph(children=[shared])
        scene.regDefName('Shared', shared)
        copied = scene.copy()
        self.assertIs(copied.getDEF('Shared'), copied.children[0])

    def test_one_copier_across_two_copies_keeps_them_together(self):
        shared = basenodes.Transform()
        copier = copiermodule.Copier()
        first = basenodes.Group(children=[shared]).copy(copier)
        second = basenodes.Group(children=[shared]).copy(copier)
        self.assertIs(first.children[0], second.children[0])


class TestWhatANodeDoesNotOwn(unittest.TestCase):
    """The scene root a node points back at is not part of it, so a copy
    points at the same scene rather than at a copy of the whole file."""

    def test_the_scene_root_is_not_copied(self):
        scene = SceneGraph(children=[basenodes.Transform()])
        held = scene.children[0]
        self.assertIs(protofunctions.root(held.copy()),
                      protofunctions.root(held))


class TestInstantiatingAPrototype(unittest.TestCase):
    """Each instance of a PROTO gets its own body, built by copying the
    prototype's."""

    SOURCE = ('#VRML V2.0 utf8\n'
              'PROTO Wheel [ exposedField SFFloat radius 1.0 ]\n'
              '{ Shape { geometry Sphere { radius IS radius } } }\n'
              'Wheel { radius 2.0 }\n'
              'Wheel { radius 5.0 }\n')

    def bodies(self):
        first, second = read(self.SOURCE).children
        return first.scenegraph, second.scenegraph

    def test_two_instances_have_two_bodies(self):
        first, second = self.bodies()
        self.assertIsNot(first, second)

    def test_they_do_not_share_the_nodes_in_them(self):
        first, second = self.bodies()
        self.assertIsNot(first.children[0], second.children[0])

    def test_each_keeps_the_value_it_was_given(self):
        first, second = self.bodies()
        self.assertAlmostEqual(first.children[0].geometry.radius, 2.0,
                               places=5)
        self.assertAlmostEqual(second.children[0].geometry.radius, 5.0,
                               places=5)

    def test_setting_one_afterwards_leaves_the_other_alone(self):
        scene = read(self.SOURCE)
        scene.children[0].radius = 9.0
        self.assertAlmostEqual(
            scene.children[1].scenegraph.children[0].geometry.radius, 5.0,
            places=5)


if __name__ == '__main__':
    unittest.main()
