"""X3D's interpolation arithmetic, and the interpolator nodes that use it.

Linear interpolation between keys, the Hermite spline of the spline
interpolators, EaseInEaseOut's fraction curve and the squad of
SquadOrientationInterpolator (ISO/IEC 19775-1, 19.2).
"""

import math
import unittest

import numpy as np

from vrml.x3d import interpolation as ip
from vrml.x3d import runtime


def sent(node):
    return node.__dict__.get('value_changed')


class TestSegments(unittest.TestCase):
    def test_a_fraction_between_keys(self):
        self.assertEqual(ip.segment([0.0, 0.5, 1.0], 0.75), (1, 0.5))

    def test_before_the_first_and_after_the_last_key_hold_the_ends(self):
        self.assertEqual(ip.segment([0.2, 0.6], 0.0), (0, 0.0))
        self.assertEqual(ip.segment([0.2, 0.6], 1.0), (0, 1.0))

    def test_one_key_is_its_value(self):
        self.assertEqual(ip.segment([0.5], 0.9), (0, 0.0))


class TestLinear(unittest.TestCase):
    def test_a_value_per_key(self):
        found = ip.linear([0, 1], np.array([(0, 0), (2, 4)], 'f'), 0.25)
        self.assertTrue(np.allclose(found, (0.5, 1.0)))

    def test_several_values_per_key(self):
        values = np.array([(0, 0), (1, 1), (2, 2), (3, 3)], 'f')
        found = ip.linear([0, 1], values, 0.5, per_key=2)
        self.assertTrue(np.allclose(found, [(1, 1), (2, 2)]))


class TestSpline(unittest.TestCase):
    KEYS = (0.0, 0.3, 0.7, 1.0)
    VALUES = np.array([0.0, 2.0, -1.0, 4.0])

    def test_it_passes_through_every_key(self):
        for key, value in zip(self.KEYS, self.VALUES):
            self.assertAlmostEqual(float(ip.spline(self.KEYS, self.VALUES, key)), value, places=5)

    def test_an_open_curve_starts_and_ends_still(self):
        near = float(ip.spline(self.KEYS, self.VALUES, 0.001))
        self.assertAlmostEqual(near, 0.0, places=3)

    def test_given_velocities_set_the_tangents(self):
        slow = ip.spline([0, 1], np.array([0.0, 1.0]), 0.25, velocities=[0.0, 0.0])
        fast = ip.spline([0, 1], np.array([0.0, 1.0]), 0.25, velocities=[4.0, 4.0])
        self.assertGreater(float(fast), float(slow))

    def test_a_closed_curve_is_smooth_through_its_join(self):
        keys = [0.0, 0.25, 0.5, 0.75, 1.0]
        values = np.array([(1, 0), (0, 1), (-1, 0), (0, -1), (1, 0)], 'f')
        before = ip.spline(keys, values, 0.999, closed=True)
        after = ip.spline(keys, values, 0.001, closed=True)
        self.assertTrue(np.allclose(before[0], after[0], atol=1e-2))
        self.assertGreater(after[1] - before[1], 0.0)

    def test_normalised_velocities_have_the_curves_length(self):
        found = ip.tangents(np.array([[0.0], [1.0], [3.0]]), normalize=True)
        self.assertTrue(np.allclose(np.linalg.norm(found[1]), 3.0))


class TestEase(unittest.TestCase):
    def test_no_easing_leaves_the_fraction(self):
        self.assertAlmostEqual(ip.ease([0, 1], [(0, 0), (0, 0)], 0.3), 0.3)

    def test_easing_out_starts_slowly(self):
        self.assertLess(ip.ease([0, 1], [(0, 0.5), (0, 0)], 0.1), 0.1)

    def test_easing_in_ends_slowly(self):
        self.assertGreater(ip.ease([0, 1], [(0, 0), (0.5, 0)], 0.9), 0.9)

    def test_the_ends_are_kept(self):
        for fraction in (0.0, 1.0):
            self.assertAlmostEqual(ip.ease([0, 1], [(0.3, 0.3), (0.3, 0.3)], fraction), fraction)


class TestSquad(unittest.TestCase):
    ROTATIONS = np.array([(0, 0, 1, 0), (0, 0, 1, 1.0), (0, 0, 1, 2.0), (0, 0, 1, 3.0)], 'f')

    def test_it_passes_through_every_key(self):
        keys = [0.0, 0.3, 0.6, 1.0]
        for key, rotation in zip(keys, self.ROTATIONS):
            found = ip.squad(keys, self.ROTATIONS, key)
            self.assertAlmostEqual(abs(found[3]), rotation[3], places=4)

    def test_rotations_about_one_axis_turn_about_it(self):
        found = ip.squad([0.0, 1.0], self.ROTATIONS[:2], 0.5)
        self.assertTrue(np.allclose(found[:3], (0, 0, 1), atol=1e-5))
        self.assertAlmostEqual(found[3], 0.5, places=4)

    def test_a_quaternion_round_trip(self):
        rotation = (1 / math.sqrt(3),) * 3 + (1.2,)
        back = ip.rotation_of(ip.quaternion_of(rotation))
        self.assertTrue(np.allclose(back, rotation, atol=1e-6))


class TestTheNodes(unittest.TestCase):
    def test_a_2d_position_interpolator(self):
        made = runtime.PositionInterpolator2D(key=[0, 1], keyValue=[(0, 0), (2, 2)])
        made.set_fraction = 0.5
        self.assertTrue(np.allclose(sent(made), (1, 1)))

    def test_a_2d_coordinate_interpolator(self):
        made = runtime.CoordinateInterpolator2D(key=[0, 1], keyValue=[(0, 0), (1, 1), (2, 2), (3, 3)])
        made.set_fraction = 1.0
        self.assertTrue(np.allclose(sent(made), [(2, 2), (3, 3)]))

    def test_a_spline_position_interpolator(self):
        made = runtime.SplinePositionInterpolator(key=[0, 1], keyValue=[(0, 0, 0), (1, 2, 3)])
        made.set_fraction = 1.0
        self.assertTrue(np.allclose(sent(made), (1, 2, 3)))

    def test_a_spline_scalar_interpolator(self):
        made = runtime.SplineScalarInterpolator(key=[0, 1], keyValue=[1.0, 3.0])
        made.set_fraction = 0.5
        self.assertAlmostEqual(float(sent(made)), 2.0)

    def test_an_ease_in_ease_out(self):
        made = runtime.EaseInEaseOut(key=[0, 1], easeInEaseOut=[(0, 0), (0, 0)])
        made.set_fraction = 0.4
        self.assertAlmostEqual(made.__dict__['modifiedFraction_changed'], 0.4)

    def test_a_squad_orientation_interpolator(self):
        made = runtime.SquadOrientationInterpolator(
            key=[0, 1], keyValue=[(0, 1, 0, 0), (0, 1, 0, 1)])
        made.set_fraction = 0.5
        self.assertAlmostEqual(float(sent(made)[3]), 0.5, places=4)

    def test_no_keys_sends_nothing(self):
        made = runtime.SplineScalarInterpolator()
        made.set_fraction = 0.5
        self.assertIsNone(sent(made))


if __name__ == '__main__':
    unittest.main()
