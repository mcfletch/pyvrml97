"""A Transform node's matrix, composed from what the node declares.

VRML97's Transform names five things -- a translation, a centre, a rotation, a
scale and the orientation the scale is applied in -- and the matrix that puts
its children in the world is those composed in a fixed order. Its inverse
takes a point back. `tests/test_transformmatrix.py` covers each of the three
primitives; this covers the composition, the inverse and the pair.

Every case here asserts against a point put through the matrix, because that
is what the matrix is for and because it holds whatever order the composition
is written in to being the right one.
"""

import unittest

from vrml.arrays import allclose, array, dot, pi
from vrml.vrml97 import transformmatrix


def moved(matrix, point):
    """`point` through `matrix`, as a 3-vector."""
    row = array([point[0], point[1], point[2], 1.0], 'd')
    return dot(row, matrix)[:3]


class TestTheForwardMatrix(unittest.TestCase):
    def test_nothing_declared_is_no_matrix_at_all(self):
        """None rather than the identity: a Transform that moves nothing has
        nothing for a renderer to multiply by, and saying so lets the caller
        skip the multiplication rather than do a null one per frame."""
        self.assertIsNone(transformmatrix.transformMatrix())

    def test_a_translation_moves_it(self):
        matrix = transformmatrix.transformMatrix(translation=(1, 0, 0))
        self.assertTrue(allclose(moved(matrix, (0, 0, 0)), (1, 0, 0), 0, 1e-6))

    def test_a_scale_multiplies_it(self):
        matrix = transformmatrix.transformMatrix(scale=(2, 2, 2))
        self.assertTrue(allclose(moved(matrix, (1, 1, 1)), (2, 2, 2), 0, 1e-6))

    def test_a_rotation_turns_it(self):
        """A half turn about Y takes +X to -X."""
        matrix = transformmatrix.transformMatrix(rotation=(0, 1, 0, pi))
        self.assertTrue(allclose(moved(matrix, (1, 0, 0)), (-1, 0, 0), 0, 1e-6))

    def test_a_centre_is_where_the_rotation_happens(self):
        """Turning about (1,0,0) leaves that point where it is."""
        matrix = transformmatrix.transformMatrix(
            center=(1, 0, 0), rotation=(0, 1, 0, pi))
        self.assertTrue(allclose(moved(matrix, (1, 0, 0)), (1, 0, 0), 0, 1e-6))

    def test_the_scale_orientation_turns_the_scale(self):
        """A scale along X, applied a quarter turn round, stretches Z."""
        matrix = transformmatrix.transformMatrix(
            scale=(2, 1, 1), scaleOrientation=(0, 1, 0, pi / 2.0))
        stretched = moved(matrix, (0, 0, 1))
        self.assertAlmostEqual(abs(stretched[2]), 2.0, places=5)

    def test_a_parent_matrix_is_applied_as_well(self):
        parent = transformmatrix.transformMatrix(translation=(10, 0, 0))
        matrix = transformmatrix.transformMatrix(
            translation=(1, 0, 0), parentMatrix=parent)
        self.assertTrue(allclose(moved(matrix, (0, 0, 0)), (11, 0, 0), 0, 1e-6))


class TestTheInverse(unittest.TestCase):
    """`itransformMatrix` takes a point in the node's space back out."""

    def declared(self):
        return dict(translation=(1, 2, 3), center=(0.5, 0, 0),
                    rotation=(0, 1, 0, pi / 3.0), scale=(2, 1, 0.5),
                    scaleOrientation=(1, 0, 0, pi / 4.0))

    def test_it_undoes_the_forward_matrix(self):
        forward = transformmatrix.transformMatrix(**self.declared())
        backward = transformmatrix.itransformMatrix(**self.declared())
        there = moved(forward, (1, 1, 1))
        back = moved(backward, there)
        self.assertTrue(allclose(back, (1, 1, 1), 0, 1e-6), back)

    def test_nothing_declared_is_no_matrix_at_all(self):
        self.assertIsNone(transformmatrix.itransformMatrix())


class TestAskingForBoth(unittest.TestCase):
    """`transformMatrices` answers the pair, which is what a scenegraph node
    keeps: one to draw its children with and one to pick through."""

    def test_the_pair_is_the_two_matrices(self):
        declared = dict(translation=(1, 2, 3), rotation=(0, 1, 0, pi / 3.0),
                        scale=(2, 1, 0.5))
        forward, backward = transformmatrix.transformMatrices(**declared)
        self.assertTrue(allclose(
            forward, transformmatrix.transformMatrix(**declared), 0, 1e-6))
        self.assertTrue(allclose(
            backward, transformmatrix.itransformMatrix(**declared), 0, 1e-6))

    def test_they_undo_each_other(self):
        forward, backward = transformmatrix.transformMatrices(
            translation=(4, 5, 6), scale=(2, 2, 2))
        back = moved(backward, moved(forward, (1, 1, 1)))
        self.assertTrue(allclose(back, (1, 1, 1), 0, 1e-6), back)


class TestWhereTheCentreOfRotationIs(unittest.TestCase):
    """`center` answers the node's centre of rotation in its parent's space,
    which is what a manipulator puts its handle on."""

    def test_with_nothing_declared_it_is_the_origin(self):
        found = transformmatrix.center()
        self.assertTrue(allclose(found[:3], (0, 0, 0), 0, 1e-6), found)

    def test_a_translation_moves_it(self):
        found = transformmatrix.center(translation=(1, 2, 3))
        self.assertTrue(allclose(found[:3], (1, 2, 3), 0, 1e-6), found)

    def test_the_centre_moves_it_as_well(self):
        found = transformmatrix.center(
            translation=(1, 0, 0), center=(0, 2, 0))
        self.assertTrue(allclose(found[:3], (1, 2, 0), 0, 1e-6), found)

    def test_a_parent_matrix_is_applied_to_it(self):
        parent = transformmatrix.transformMatrix(translation=(10, 0, 0))
        found = transformmatrix.center(
            translation=(1, 0, 0), parentMatrix=parent)
        self.assertTrue(allclose(found[:3], (11, 0, 0), 0, 1e-6), found)


class TestLocalMatrices(unittest.TestCase):
    """The node's own matrices, without a parent's."""

    def test_they_undo_each_other(self):
        forward, backward = transformmatrix.localMatrices(
            translation=(1, 2, 3), scale=(2, 2, 2))
        back = moved(backward, moved(forward, (1, 1, 1)))
        self.assertTrue(allclose(back, (1, 1, 1), 0, 1e-6), back)


class TestTheProjections(unittest.TestCase):
    """A perspective and an orthographic matrix, which a viewpoint builds."""

    def test_a_perspective_matrix_is_four_by_four(self):
        matrix = transformmatrix.perspectiveMatrix(
            pi / 3.0, 1.0, 0.1, 100.0)
        self.assertEqual(array(matrix).shape, (4, 4))

    def test_it_puts_the_near_plane_where_the_viewer_can_see_it(self):
        matrix = transformmatrix.perspectiveMatrix(
            pi / 3.0, 1.0, 1.0, 100.0)
        row = array([0.0, 0.0, -1.0, 1.0], 'd')
        clipped = dot(row, matrix)
        self.assertAlmostEqual(clipped[2] / clipped[3], -1.0, places=5)

    def test_an_orthographic_matrix_is_four_by_four(self):
        matrix = transformmatrix.orthoMatrix(-1, 1, -1, 1, 0.1, 100.0)
        self.assertEqual(array(matrix).shape, (4, 4))

    def test_it_maps_the_named_box_onto_the_clip_cube(self):
        matrix = transformmatrix.orthoMatrix(-2, 2, -2, 2, 1.0, 3.0)
        row = array([2.0, 2.0, -1.0, 1.0], 'd')
        clipped = dot(row, matrix)
        self.assertAlmostEqual(clipped[0], 1.0, places=5)
        self.assertAlmostEqual(clipped[1], 1.0, places=5)


class TestComposingMatrices(unittest.TestCase):
    def test_nothing_to_compose_is_no_matrix(self):
        """Documented: all of them None answers None, which is what lets a
        caller skip a multiplication rather than do a null one."""
        self.assertIsNone(transformmatrix.compressMatrices())
        self.assertIsNone(transformmatrix.compressMatrices(None, None))

    def test_one_matrix_composes_to_itself(self):
        moving = transformmatrix.transMatrix((1, 2, 3))[0]
        self.assertTrue(allclose(
            transformmatrix.compressMatrices(moving), moving, 0, 1e-6))

    def test_a_none_among_them_is_skipped(self):
        moving = transformmatrix.transMatrix((1, 2, 3))[0]
        self.assertTrue(allclose(
            transformmatrix.compressMatrices(None, moving, None),
            moving, 0, 1e-6))


if __name__ == '__main__':
    unittest.main()
