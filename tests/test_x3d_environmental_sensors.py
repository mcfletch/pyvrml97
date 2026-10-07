"""X3D's environmental sensors (ISO/IEC 19775-1, 22).

A ProximitySensor watches the viewer, a TransformSensor its target object,
within a box of `size` about `center`; a VisibilitySensor whether its box is
in view. Each is told what it watches by `observe`, in its own coordinates,
by whoever draws the scene: entering sends `isActive TRUE` and `enterTime`,
leaving `isActive FALSE` and `exitTime`, and moving while inside sends
`position_changed` and `orientation_changed`.
"""

import math
import unittest

import numpy as np

from vrml.x3d import runtime, sensors


def sent(node, name):
    return node.__dict__.get(name)


class TestProximity(unittest.TestCase):
    def setUp(self):
        self.sensor = sensors.ProximitySensor(center=(0, 0, 0), size=(10, 10, 10))

    def test_entering_activates_and_sends_the_pose(self):
        self.sensor.observe((1, 2, 3), (0, 1, 0, 0.5), now=4.0)
        self.assertIs(sent(self.sensor, 'isActive'), True)
        self.assertEqual(sent(self.sensor, 'enterTime'), 4.0)
        self.assertTrue(np.allclose(sent(self.sensor, 'position_changed'), (1, 2, 3)))
        self.assertTrue(np.allclose(sent(self.sensor, 'orientation_changed'), (0, 1, 0, 0.5)))

    def test_outside_sends_nothing(self):
        self.sensor.observe((6, 0, 0), (0, 0, 1, 0), now=1.0)
        self.assertIsNone(sent(self.sensor, 'isActive'))
        self.assertIsNone(sent(self.sensor, 'position_changed'))

    def test_leaving_deactivates(self):
        self.sensor.observe((0, 0, 0), (0, 0, 1, 0), now=1.0)
        self.sensor.observe((0, 0, 20), (0, 0, 1, 0), now=2.0)
        self.assertIs(sent(self.sensor, 'isActive'), False)
        self.assertEqual(sent(self.sensor, 'exitTime'), 2.0)

    def test_standing_still_sends_no_position(self):
        self.sensor.observe((1, 1, 1), (0, 0, 1, 0), now=1.0)
        self.sensor.__dict__.pop('position_changed')
        self.sensor.observe((1, 1, 1), (0, 0, 1, 0), now=2.0)
        self.assertIsNone(sent(self.sensor, 'position_changed'))

    def test_a_sensor_of_no_size_senses_nothing(self):
        sensor = sensors.ProximitySensor(size=(0, 0, 0))
        sensor.observe((0, 0, 0), (0, 0, 1, 0), now=1.0)
        self.assertIsNone(sent(sensor, 'isActive'))

    def test_disabling_an_active_sensor_deactivates_it(self):
        self.sensor.observe((0, 0, 0), (0, 0, 1, 0), now=1.0)
        self.sensor.enabled = False
        self.sensor.observe((0, 0, 0), (0, 0, 1, 0), now=2.0)
        self.assertIs(sent(self.sensor, 'isActive'), False)

    def test_the_box_is_about_its_centre(self):
        sensor = sensors.ProximitySensor(center=(100, 0, 0), size=(2, 2, 2))
        sensor.observe((100.9, 0, 0), (0, 0, 1, 0), now=1.0)
        self.assertIs(sent(sensor, 'isActive'), True)

    def test_its_time_is_its_scenes(self):
        from vrml.x3d import timing  # noqa: PLC0415 kept with its use
        saved = timing.clock
        timing.clock = lambda: 9.5
        try:
            self.sensor.observe((0, 0, 0), (0, 0, 1, 0))
        finally:
            timing.clock = saved
        self.assertEqual(sent(self.sensor, 'enterTime'), 9.5)


class TestTransform(unittest.TestCase):
    def test_the_target_inside_activates(self):
        sensor = sensors.TransformSensor(size=(4, 4, 4))
        sensor.observe((1, 0, 0), (1, 0, 0, math.pi / 2), now=3.0)
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertEqual(sent(sensor, 'enterTime'), 3.0)
        self.assertTrue(np.allclose(sent(sensor, 'position_changed'), (1, 0, 0)))


class TestVisibility(unittest.TestCase):
    def test_coming_into_view_and_going_out(self):
        sensor = sensors.VisibilitySensor(size=(1, 1, 1))
        sensor.observe(True, now=1.0)
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertEqual(sent(sensor, 'enterTime'), 1.0)
        sensor.observe(False, now=2.0)
        self.assertIs(sent(sensor, 'isActive'), False)
        self.assertEqual(sent(sensor, 'exitTime'), 2.0)

    def test_a_box_of_no_size_is_never_seen(self):
        sensor = sensors.VisibilitySensor(size=(1, 0, 1))
        sensor.observe(True, now=1.0)
        self.assertIsNone(sent(sensor, 'isActive'))


class TestRegistered(unittest.TestCase):
    def test_each_is_in_the_runtime(self):
        for name in ('ProximitySensor', 'TransformSensor', 'VisibilitySensor'):
            self.assertIs(runtime.PROTOTYPES[name], getattr(sensors, name))


if __name__ == '__main__':
    unittest.main()
