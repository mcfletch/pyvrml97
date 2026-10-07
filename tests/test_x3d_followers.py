"""X3D's followers: chasers and dampers moving a value toward a destination.

A chaser reaches each destination `duration` seconds after it is set, along
a smooth step; a damper approaches it through `order` first-order filters of
time constant `tau`. Each is moved by `advance(now)`, which answers whether
it is still moving; `isActive` says the same to routes.
"""

import math
import unittest

import numpy as np

from vrml.x3d import followers, runtime


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class FollowerCase(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.saved = followers.clock
        followers.clock = self.clock

    def tearDown(self):
        followers.clock = self.saved

    def at(self, made, seconds):
        self.clock.now = 100.0 + seconds
        return made.advance(self.clock.now)


class TestChasers(FollowerCase):
    def test_it_is_halfway_at_half_its_duration(self):
        made = followers.ScalarChaser(duration=2.0)
        made.set_destination = 10.0
        self.assertTrue(self.at(made, 1.0))
        self.assertAlmostEqual(made.value_changed, 5.0)
        self.assertIs(made.isActive, True)

    def test_it_arrives_after_its_duration_and_stops(self):
        made = followers.ScalarChaser(duration=2.0)
        made.set_destination = 10.0
        self.assertFalse(self.at(made, 2.5))
        self.assertAlmostEqual(made.value_changed, 10.0)
        self.assertIs(made.isActive, False)

    def test_a_new_destination_carries_on_from_where_it_is(self):
        made = followers.ScalarChaser(duration=2.0)
        made.set_destination = 10.0
        self.at(made, 1.0)
        before = made.value_changed
        made.set_destination = 0.0
        self.at(made, 1.0)
        self.assertAlmostEqual(made.value_changed, before)
        self.at(made, 3.0)
        self.assertAlmostEqual(made.value_changed, 0.0)

    def test_set_value_jumps_and_stops(self):
        made = followers.PositionChaser()
        made.set_destination = (1, 2, 3)
        made.set_value = (4, 5, 6)
        self.assertTrue(np.allclose(made.value_changed, (4, 5, 6)))
        self.assertFalse(self.at(made, 0.1))

    def test_an_orientation_turns_halfway(self):
        made = followers.OrientationChaser(duration=1.0, initialValue=(0, 1, 0, 0))
        made.set_destination = (0, 1, 0, 1.0)
        self.at(made, 0.5)
        self.assertAlmostEqual(float(made.value_changed[3]), 0.5, places=4)

    def test_it_starts_toward_its_initial_destination(self):
        made = followers.ScalarChaser(duration=1.0, initialValue=0.0, initialDestination=4.0)
        self.at(made, 0.0)
        self.assertTrue(made.moving())
        self.at(made, 1.0)
        self.assertAlmostEqual(made.value_changed, 4.0)


class TestDampers(FollowerCase):
    def test_a_first_order_damper_is_one_time_constant_short(self):
        made = followers.ScalarDamper(order=1, tau=0.5)
        made.set_destination = 1.0
        self.at(made, 0.0)
        self.at(made, 0.5)
        self.assertAlmostEqual(made.value_changed, 1.0 - math.exp(-1.0), places=4)

    def test_it_comes_to_rest_within_its_tolerance(self):
        made = followers.ScalarDamper(order=3, tau=0.2, tolerance=0.001)
        made.set_destination = 1.0
        self.at(made, 0.0)
        steps = 0
        while self.at(made, 0.02 * (steps + 1)) and steps < 1000:
            steps += 1
        self.assertLess(steps, 1000)
        self.assertAlmostEqual(made.value_changed, 1.0, places=2)
        self.assertIs(made.isActive, False)

    def test_order_zero_jumps(self):
        made = followers.PositionDamper(order=0)
        made.set_destination = (1, 1, 1)
        self.assertFalse(self.at(made, 0.0))
        self.assertTrue(np.allclose(made.value_changed, (1, 1, 1)))

    def test_a_coordinate_damper_moves_every_point(self):
        made = followers.CoordinateDamper(order=1, tau=1.0, initialValue=[(0, 0, 0), (1, 1, 1)],
                                          initialDestination=[(0, 0, 0), (1, 1, 1)])
        made.set_destination = [(2, 2, 2), (3, 3, 3)]
        self.at(made, 0.0)
        self.at(made, 1.0)
        found = np.asarray(made.value_changed)
        self.assertEqual(found.shape, (2, 3))
        self.assertTrue(np.all(found > (0, 0, 0)))

    def test_an_orientation_damper_turns_toward_its_destination(self):
        made = followers.OrientationDamper(order=1, tau=1.0)
        made.set_destination = (0, 0, 1, 1.0)
        self.at(made, 0.0)
        self.at(made, 1.0)
        self.assertAlmostEqual(float(made.value_changed[3]), 1.0 - math.exp(-1.0), places=3)


class TestTheFamily(unittest.TestCase):
    def test_every_follower_is_in_the_runtime(self):
        names = [name for name in runtime.PROTOTYPES if 'Chaser' in name or 'Damper' in name]
        self.assertEqual(len(names), 14)


if __name__ == '__main__':
    unittest.main()
