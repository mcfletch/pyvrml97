"""Comparing two scenes: the first place their graphs differ."""

import unittest

from vrml.x3d import nodes as x3d
from vrml.x3d.compare import first_difference
from vrml.x3d.scene import X3DScene


def scene(*children, **fields):
    return X3DScene(children=list(children), **fields)


class TestFirstDifference(unittest.TestCase):
    def test_equal_graphs_have_none(self):
        self.assertIsNone(first_difference(
            scene(x3d.Transform(translation=(1, 2, 3), children=[x3d.Shape(geometry=x3d.Box())])),
            scene(x3d.Transform(translation=(1, 2, 3), children=[x3d.Shape(geometry=x3d.Box())])),
        ))

    def test_a_value_differs(self):
        found = first_difference(scene(x3d.Sphere(radius=1)), scene(x3d.Sphere(radius=2)))
        self.assertIn('children[0].radius', found)

    def test_a_node_type_differs(self):
        found = first_difference(scene(x3d.Sphere()), scene(x3d.Box()))
        self.assertIn('Sphere', found)
        self.assertIn('Box', found)

    def test_lists_of_different_lengths(self):
        found = first_difference(scene(x3d.Group(), x3d.Group()), scene(x3d.Group()))
        self.assertIn('children', found)

    def test_values_within_float32_precision_are_equal(self):
        self.assertIsNone(first_difference(
            scene(x3d.Transform(translation=(0.1, 0.2, 0.3))),
            scene(x3d.Transform(translation=(0.1000000001, 0.2, 0.3)))))

    def test_shared_nodes_must_be_shared_in_both(self):
        shape = x3d.Shape()
        shared = scene(x3d.Group(children=[shape, shape]))
        separate = scene(x3d.Group(children=[x3d.Shape(), x3d.Shape()]))
        self.assertIn('shared', first_difference(shared, separate))
        self.assertIsNone(first_difference(shared, scene(x3d.Group(children=[shape, shape]))))

    def test_the_header_is_compared(self):
        found = first_difference(scene(profile='Full'), scene(profile='Core'))
        self.assertIn('profile', found)

    def test_a_dag_is_compared_once_per_node(self):
        leaf = x3d.Shape()
        deep = leaf
        for _ in range(30):
            deep = x3d.Group(children=[deep, deep])
        self.assertIsNone(first_difference(scene(deep), scene(deep)))


if __name__ == '__main__':
    unittest.main()
