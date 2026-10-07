"""X3D's pointing-device sensors (ISO/IEC 19775-1, 20).

Whoever has the pointer tells a sensor, in the sensor's own coordinates,
where the pointer's ray is and what it hits: `pointerOver` as it moves,
`pointerPress` when the primary button goes down over the sensor's geometry,
`pointerDrag` as it moves while held and `pointerRelease` when it comes up.
"""

import math
import unittest

import numpy as np

from vrml.x3d import pointing, runtime


def sent(node, name):
    return node.__dict__.get(name)


def down(origin, toward):
    """A ray from `origin` toward `toward`"""
    origin = np.asarray(origin, float)
    return pointing.Ray(origin, np.asarray(toward, float) - origin)


class TestTouch(unittest.TestCase):
    def setUp(self):
        self.sensor = pointing.TouchSensor()
        self.hit = pointing.Hit((1, 2, 0), (0, 0, 1), (0.5, 0.5))

    def test_over_sends_isover_and_the_hit(self):
        self.sensor.pointerOver(self.hit)
        self.assertIs(sent(self.sensor, 'isOver'), True)
        self.assertTrue(np.allclose(sent(self.sensor, 'hitPoint_changed'), (1, 2, 0)))
        self.assertTrue(np.allclose(sent(self.sensor, 'hitNormal_changed'), (0, 0, 1)))
        self.assertTrue(np.allclose(sent(self.sensor, 'hitTexCoord_changed'), (0.5, 0.5)))
        self.sensor.pointerOver(None)
        self.assertIs(sent(self.sensor, 'isOver'), False)

    def test_a_click_over_it_sends_touchtime(self):
        self.sensor.pointerOver(self.hit)
        self.sensor.pointerPress(self.hit, down((1, 2, 5), (1, 2, 0)))
        self.assertIs(sent(self.sensor, 'isActive'), True)
        self.sensor.pointerRelease(True, now=4.0)
        self.assertIs(sent(self.sensor, 'isActive'), False)
        self.assertEqual(sent(self.sensor, 'touchTime'), 4.0)

    def test_released_elsewhere_sends_no_touchtime(self):
        self.sensor.pointerPress(self.hit, down((1, 2, 5), (1, 2, 0)))
        self.sensor.pointerRelease(False, now=4.0)
        self.assertIsNone(sent(self.sensor, 'touchTime'))

    def test_a_disabled_sensor_sends_nothing(self):
        self.sensor.enabled = False
        self.sensor.pointerOver(self.hit)
        self.sensor.pointerPress(self.hit, down((1, 2, 5), (1, 2, 0)))
        self.assertIsNone(sent(self.sensor, 'isOver'))
        self.assertIsNone(sent(self.sensor, 'isActive'))


class TestPlane(unittest.TestCase):
    def press(self, sensor, point=(0, 0, 0)):
        sensor.pointerPress(pointing.Hit(point), down((point[0], point[1], 10), point))

    def test_dragging_translates_in_the_plane(self):
        sensor = pointing.PlaneSensor()
        self.press(sensor, (1, 1, 2))
        sensor.pointerDrag(None, down((4, 3, 10), (4, 3, 2)))
        self.assertTrue(np.allclose(sent(sensor, 'translation_changed'), (3, 2, 0)))
        self.assertTrue(np.allclose(sent(sensor, 'trackPoint_changed'), (4, 3, 2)))

    def test_the_plane_is_through_the_first_hit(self):
        sensor = pointing.PlaneSensor()
        self.press(sensor, (0, 0, 2))
        sensor.pointerDrag(None, down((0, 0, 10), (1, 0, 6)))
        # The ray meets z=2 at x=2.
        self.assertTrue(np.allclose(sent(sensor, 'trackPoint_changed'), (2, 0, 2)))

    def test_the_translation_is_clamped(self):
        sensor = pointing.PlaneSensor(minPosition=(-1, 0), maxPosition=(1, 0))
        self.press(sensor)
        sensor.pointerDrag(None, down((5, 5, 10), (5, 5, 0)))
        self.assertTrue(np.allclose(sent(sensor, 'translation_changed'), (1, 0, 0)))

    def test_a_minimum_past_the_maximum_leaves_that_axis_free(self):
        sensor = pointing.PlaneSensor(minPosition=(1, 0), maxPosition=(-1, 0))
        self.press(sensor)
        sensor.pointerDrag(None, down((5, 5, 10), (5, 5, 0)))
        self.assertTrue(np.allclose(sent(sensor, 'translation_changed'), (5, 0, 0)))

    def test_auto_offset_carries_on_from_the_last_drag(self):
        sensor = pointing.PlaneSensor()
        self.press(sensor)
        sensor.pointerDrag(None, down((2, 0, 10), (2, 0, 0)))
        sensor.pointerRelease(True, now=2.0)
        self.assertTrue(np.allclose(sensor.offset, (2, 0, 0)))
        self.press(sensor)
        sensor.pointerDrag(None, down((1, 0, 10), (1, 0, 0)))
        self.assertTrue(np.allclose(sent(sensor, 'translation_changed'), (3, 0, 0)))

    def test_axis_rotation_turns_the_plane(self):
        sensor = pointing.PlaneSensor(axisRotation=(0, 1, 0, math.pi / 2))
        self.press(sensor)
        # The plane is now x=0: a ray along -x from x=10 meets it.
        sensor.pointerDrag(None, down((10, 1, 3), (0, 1, 3)))
        self.assertTrue(np.allclose(sent(sensor, 'translation_changed'), (0, 1, 3), atol=1e-6))


class TestCylinder(unittest.TestCase):
    def test_dragging_round_the_cylinder_turns_about_y(self):
        sensor = pointing.CylinderSensor()
        start = (0, 0, 1)
        sensor.pointerPress(pointing.Hit(start), down((0, 0, 10), start))
        quarter = (1, 0, 0)
        sensor.pointerDrag(None, down((10, 0, 0), quarter))
        rotation = sent(sensor, 'rotation_changed')
        self.assertTrue(np.allclose(rotation[:3], (0, 1, 0)))
        self.assertAlmostEqual(rotation[3], math.pi / 2, places=5)

    def test_looking_down_the_axis_turns_a_disk(self):
        sensor = pointing.CylinderSensor()
        start = (1, 0, 0)
        sensor.pointerPress(pointing.Hit(start), down((1, 10, 0), start))
        sensor.pointerDrag(None, down((0, 10, -1), (0, 0, -1)))
        self.assertAlmostEqual(sent(sensor, 'rotation_changed')[3], math.pi / 2, places=5)

    def test_the_angle_is_clamped(self):
        sensor = pointing.CylinderSensor(minAngle=0.0, maxAngle=0.5)
        sensor.pointerPress(pointing.Hit((0, 0, 1)), down((0, 0, 10), (0, 0, 1)))
        sensor.pointerDrag(None, down((10, 0, 0), (1, 0, 0)))
        self.assertAlmostEqual(sent(sensor, 'rotation_changed')[3], 0.5, places=5)


    def test_a_drag_across_the_half_turn_carries_on(self):
        def at(degrees):
            theta = math.radians(degrees)
            point = (math.cos(theta), 0.0, -math.sin(theta))
            return point, down(tuple(10 * value for value in point), point)
        sensor = pointing.CylinderSensor(minAngle=0.0, maxAngle=1.5)
        point, ray = at(170)
        sensor.pointerPress(pointing.Hit(point), ray)
        for degrees in (180, 190):
            sensor.pointerDrag(None, at(degrees)[1])
        self.assertAlmostEqual(sent(sensor, 'rotation_changed')[3], math.radians(20), places=5)


class TestSphere(unittest.TestCase):
    def test_dragging_over_the_sphere_turns_it(self):
        sensor = pointing.SphereSensor()
        sensor.pointerPress(pointing.Hit((0, 0, 1)), down((0, 0, 10), (0, 0, 1)))
        sensor.pointerDrag(None, down((0, 10, 0), (0, 1, 0)))
        rotation = sent(sensor, 'rotation_changed')
        self.assertTrue(np.allclose(rotation[:3], (-1, 0, 0), atol=1e-6))
        self.assertAlmostEqual(rotation[3], math.pi / 2, places=5)
        self.assertTrue(np.allclose(sent(sensor, 'trackPoint_changed'), (0, 1, 0)))

    def test_a_ray_that_misses_takes_the_nearest_point(self):
        sensor = pointing.SphereSensor()
        sensor.pointerPress(pointing.Hit((0, 0, 1)), down((0, 0, 10), (0, 0, 1)))
        sensor.pointerDrag(None, down((5, 0, 10), (5, 0, 0)))
        self.assertTrue(np.allclose(sent(sensor, 'trackPoint_changed'), (1, 0, 0)))


class TestRegistered(unittest.TestCase):
    def test_each_is_in_the_runtime(self):
        for name in ('TouchSensor', 'PlaneSensor', 'CylinderSensor', 'SphereSensor'):
            self.assertIs(runtime.PROTOTYPES[name], getattr(pointing, name))


if __name__ == '__main__':
    unittest.main()
