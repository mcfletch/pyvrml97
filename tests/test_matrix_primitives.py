"""The five matrix primitives, and the two implementations of them.

A rotation, a scale, a translation and the two projections are each built in
Python and, where the accelerator is installed, in C instead. Both answer the
same calls, so both have to answer them the same way -- a matrix that differed
between builds would move a scene by a different amount on one machine than on
another.

Each primitive answers a pair, the matrix and its inverse, and answers
`(None, None)` where there is nothing to do: no rotation, a scale of one, a
translation of zero. That is what lets a renderer skip a multiplication rather
than do a null one per frame, so it is part of the contract as much as the
numbers are.

`tests/test_transform_composition.py` covers what `transformmatrix` composes
from these.
"""

import unittest

from vrml.arrays import allclose, array, dot, pi
from vrml.vrml97 import _transformmatrix

try:
    from vrml.vrml97 import _transformmatrix_accel
except ImportError:                                 # pragma: no cover
    _transformmatrix_accel = None


def moved(matrix, point):
    """`point` through `matrix`, as a 3-vector."""
    row = array([point[0], point[1], point[2], 1.0], 'd')
    return dot(row, matrix)[:3]


class TheContract:
    """What both implementations of the primitives have to do.

    `implementation` is the module under test; the concrete cases below bind
    it.
    """

    implementation = _transformmatrix

    ### Rotation
    def test_a_half_turn_about_y_takes_x_to_minus_x(self):
        forward, backward = self.implementation.rotMatrix((0, 1, 0, pi))
        self.assertTrue(allclose(moved(forward, (1, 0, 0)), (-1, 0, 0),
                                 0, 1e-6))

    def test_the_inverse_turns_it_back(self):
        forward, backward = self.implementation.rotMatrix((0, 1, 0, pi / 3.0))
        there = moved(forward, (1, 2, 3))
        self.assertTrue(allclose(moved(backward, there), (1, 2, 3), 0, 1e-6))

    def test_an_unnormalised_axis_turns_the_same_amount(self):
        """A file may give any vector; the length of it is not the angle."""
        forward, backward = self.implementation.rotMatrix((0, 2, 0, pi))
        self.assertTrue(allclose(moved(forward, (1, 0, 0)), (-1, 0, 0),
                                 0, 1e-6))

    def test_no_rotation_at_all_is_no_matrix(self):
        self.assertEqual(self.implementation.rotMatrix((0, 1, 0, 0)),
                         (None, None))

    def test_a_whole_turn_is_no_matrix_either(self):
        self.assertEqual(
            self.implementation.rotMatrix((0, 1, 0, 2.0 * pi)), (None, None))

    def test_nothing_given_is_no_matrix(self):
        self.assertEqual(self.implementation.rotMatrix(), (None, None))

    ### Scale
    def test_a_scale_multiplies_a_point(self):
        forward, backward = self.implementation.scaleMatrix((2, 3, 4))
        self.assertTrue(allclose(moved(forward, (1, 1, 1)), (2, 3, 4),
                                 0, 1e-6))

    def test_its_inverse_divides_again(self):
        forward, backward = self.implementation.scaleMatrix((2, 3, 4))
        self.assertTrue(allclose(moved(backward, (2, 3, 4)), (1, 1, 1),
                                 0, 1e-6))

    def test_a_scale_of_one_is_no_matrix(self):
        self.assertEqual(self.implementation.scaleMatrix((1.0, 1.0, 1.0)),
                         (None, None))

    def test_nothing_given_is_no_scale(self):
        self.assertEqual(self.implementation.scaleMatrix(), (None, None))

    def test_a_scale_of_zero_still_answers_an_inverse(self):
        """Undoing it is not possible, and answering no matrix at all would
        make the caller skip a multiplication it must not skip."""
        forward, backward = self.implementation.scaleMatrix((0.0, 1.0, 1.0))
        self.assertIsNotNone(forward)
        self.assertIsNotNone(backward)

    ### Translation
    def test_a_translation_moves_a_point(self):
        forward, backward = self.implementation.transMatrix((1, 2, 3))
        self.assertTrue(allclose(moved(forward, (0, 0, 0)), (1, 2, 3),
                                 0, 1e-6))

    def test_its_inverse_moves_it_back(self):
        forward, backward = self.implementation.transMatrix((1, 2, 3))
        self.assertTrue(allclose(moved(backward, (1, 2, 3)), (0, 0, 0),
                                 0, 1e-6))

    def test_no_translation_is_no_matrix(self):
        self.assertEqual(self.implementation.transMatrix((0.0, 0.0, 0.0)),
                         (None, None))

    def test_nothing_given_is_no_translation(self):
        self.assertEqual(self.implementation.transMatrix(), (None, None))

    def test_a_longer_vector_is_read_for_its_first_three(self):
        forward, backward = self.implementation.transMatrix((1, 2, 3, 1))
        self.assertTrue(allclose(moved(forward, (0, 0, 0)), (1, 2, 3),
                                 0, 1e-6))

    ### The projections
    def test_a_perspective_matrix_puts_the_near_plane_on_the_clip_plane(self):
        matrix = self.implementation.perspectiveMatrix(
            pi / 3.0, 1.0, 1.0, 100.0)
        clipped = dot(array([0.0, 0.0, -1.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(clipped[2] / clipped[3], -1.0, places=5)

    def test_it_puts_the_far_plane_on_the_other_one(self):
        matrix = self.implementation.perspectiveMatrix(
            pi / 3.0, 1.0, 1.0, 100.0)
        clipped = dot(array([0.0, 0.0, -100.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(clipped[2] / clipped[3], 1.0, places=4)

    def test_the_aspect_ratio_widens_it(self):
        square = self.implementation.perspectiveMatrix(
            pi / 3.0, 1.0, 1.0, 100.0)
        wide = self.implementation.perspectiveMatrix(
            pi / 3.0, 2.0, 1.0, 100.0)
        self.assertLess(abs(wide[0][0]), abs(square[0][0]))

    def test_a_perspective_inverse_undoes_it(self):
        matrix = self.implementation.perspectiveMatrix(
            pi / 3.0, 1.0, 1.0, 100.0)
        inverse = self.implementation.perspectiveMatrix(
            pi / 3.0, 1.0, 1.0, 100.0, inverse=True)
        point = array([0.5, 0.25, -10.0, 1.0], 'd')
        clipped = dot(point, matrix)
        back = dot(clipped, inverse)
        self.assertTrue(allclose(back[:3] / back[3], point[:3] / point[3],
                                 0, 1e-4), back)

    def test_an_orthographic_matrix_maps_the_box_onto_the_clip_cube(self):
        matrix = self.implementation.orthoMatrix(-2, 2, -2, 2, 1.0, 3.0)
        clipped = dot(array([2.0, 2.0, -1.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(clipped[0], 1.0, places=5)
        self.assertAlmostEqual(clipped[1], 1.0, places=5)

    def test_its_near_plane_lands_on_the_clip_plane(self):
        matrix = self.implementation.orthoMatrix(-2, 2, -2, 2, 1.0, 3.0)
        clipped = dot(array([0.0, 0.0, -1.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(clipped[2], -1.0, places=5)

    def test_its_far_plane_lands_on_the_other_one(self):
        matrix = self.implementation.orthoMatrix(-2, 2, -2, 2, 1.0, 3.0)
        clipped = dot(array([0.0, 0.0, -3.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(clipped[2], 1.0, places=5)

    def test_an_off_centre_box_is_moved_onto_the_cube(self):
        """The offset goes in the last row, as every other matrix here puts
        it: a point through this is `dot(point, matrix)`."""
        matrix = self.implementation.orthoMatrix(0, 4, -2, 2, 1.0, 3.0)
        left = dot(array([0.0, 0.0, -1.0, 1.0], 'd'), matrix)
        right = dot(array([4.0, 0.0, -1.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(left[0], -1.0, places=5)
        self.assertAlmostEqual(right[0], 1.0, places=5)

    def test_it_leaves_the_homogenous_coordinate_alone(self):
        """An orthographic projection does not divide, so w comes out as it
        went in."""
        matrix = self.implementation.orthoMatrix(0, 4, -2, 2, 1.0, 3.0)
        clipped = dot(array([1.0, 1.0, -2.0, 1.0], 'd'), matrix)
        self.assertAlmostEqual(clipped[3], 1.0, places=5)


class TestThePythonImplementation(TheContract, unittest.TestCase):
    implementation = _transformmatrix


@unittest.skipIf(_transformmatrix_accel is None,
                 'the accelerator is not installed')
class TestTheAcceleratedImplementation(TheContract, unittest.TestCase):
    implementation = _transformmatrix_accel


@unittest.skipIf(_transformmatrix_accel is None,
                 'the accelerator is not installed')
class TestTheTwoAgree(unittest.TestCase):
    """The numbers themselves, so that a scene is in the same place
    whichever build is installed."""

    def both(self, name, *arguments):
        return (getattr(_transformmatrix, name)(*arguments),
                getattr(_transformmatrix_accel, name)(*arguments))

    def assertPairsAgree(self, name, *arguments):
        first, second = self.both(name, *arguments)
        for mine, theirs in zip(first, second):
            self.assertTrue(allclose(mine, theirs, 0, 1e-5),
                            '%s%r:\n%s\n%s' % (name, arguments, mine, theirs))

    def test_a_rotation(self):
        self.assertPairsAgree('rotMatrix', (0.3, 0.5, 0.8, pi / 3.0))

    def test_a_scale(self):
        self.assertPairsAgree('scaleMatrix', (2.0, 3.0, 0.5))

    def test_a_translation(self):
        self.assertPairsAgree('transMatrix', (1.0, 2.0, 3.0))

    def test_a_perspective_matrix(self):
        self.assertTrue(allclose(
            _transformmatrix.perspectiveMatrix(pi / 3.0, 1.5, 0.1, 100.0),
            _transformmatrix_accel.perspectiveMatrix(pi / 3.0, 1.5, 0.1,
                                                     100.0),
            0, 1e-5))

    def test_an_orthographic_matrix(self):
        self.assertTrue(allclose(
            _transformmatrix.orthoMatrix(-1, 2, -3, 4, 0.1, 100.0),
            _transformmatrix_accel.orthoMatrix(-1, 2, -3, 4, 0.1, 100.0),
            0, 1e-5))


if __name__ == '__main__':
    unittest.main()
