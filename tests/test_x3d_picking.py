"""X3D's pick sensors (ISO/IEC 19775-1, 38).

Whoever draws the scene works out what each sensor's `pickingGeometry`
touches among its `pickTarget` nodes and hands the sensor a `Pick` for each
shape touched; the sensor keeps those its `sortOrder` asks for and sends
`isActive`, `pickedGeometry` and, for line and point sensors, the points.
"""

import unittest

import numpy as np

from vrml.x3d import picking, runtime


def sent(node, name):
    return node.__dict__.get(name)


class Shape:
    """Stands for a picked shape: the sensor sends the object it is given"""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Shape(%s)' % self.name


NEAR, MIDDLE, FAR = Shape('near'), Shape('middle'), Shape('far')


def picks():
    return [picking.Pick(MIDDLE, 5.0), picking.Pick(FAR, 9.0), picking.Pick(NEAR, 1.0)]


class TestMatching(unittest.TestCase):
    def test_all_on_either_side_matches(self):
        self.assertTrue(picking.matches(['ALL'], ['TERRAIN'], 'MATCH_ANY'))
        self.assertTrue(picking.matches(['DOOR'], ['ALL'], 'MATCH_ONLY_ONE'))

    def test_none_on_either_side_never_matches(self):
        self.assertFalse(picking.matches(['NONE'], ['ALL'], 'MATCH_ANY'))
        self.assertFalse(picking.matches(['ALL'], ['NONE'], 'MATCH_ANY'))

    def test_match_any_wants_one_label_in_common(self):
        self.assertTrue(picking.matches(['DOOR', 'WALL'], ['WALL'], 'MATCH_ANY'))
        self.assertFalse(picking.matches(['DOOR'], ['WALL'], 'MATCH_ANY'))

    def test_match_every_wants_each_of_the_sensors_labels(self):
        self.assertTrue(picking.matches(['DOOR', 'WOOD'], ['WOOD', 'DOOR', 'OLD'], 'MATCH_EVERY'))
        self.assertFalse(picking.matches(['DOOR', 'WOOD'], ['DOOR'], 'MATCH_EVERY'))

    def test_match_only_one_wants_exactly_one_in_common(self):
        self.assertTrue(picking.matches(['DOOR', 'WOOD'], ['DOOR'], 'MATCH_ONLY_ONE'))
        self.assertFalse(picking.matches(['DOOR', 'WOOD'], ['DOOR', 'WOOD'], 'MATCH_ONLY_ONE'))

    def test_a_sensor_accepts_by_its_own_fields(self):
        sensor = picking.VolumePickSensor(objectType=['DOOR'], matchCriterion='MATCH_ANY')
        self.assertTrue(sensor.accepts(['DOOR']))
        self.assertFalse(sensor.accepts(['WALL']))


class TestSortOrder(unittest.TestCase):
    def chosen(self, order):
        sensor = picking.VolumePickSensor(sortOrder=order)
        sensor.observe(picks())
        return list(sent(sensor, 'pickedGeometry'))

    def test_closest_is_the_nearest_alone(self):
        self.assertEqual(self.chosen('CLOSEST'), [NEAR])

    def test_any_is_the_first_found(self):
        self.assertEqual(self.chosen('ANY'), [MIDDLE])

    def test_all_is_every_one_in_the_order_found(self):
        self.assertEqual(self.chosen('ALL'), [MIDDLE, FAR, NEAR])

    def test_all_sorted_is_every_one_nearest_first(self):
        self.assertEqual(self.chosen('ALL_SORTED'), [NEAR, MIDDLE, FAR])

    def test_an_unknown_order_is_closest(self):
        self.assertEqual(self.chosen('BY_COLOUR'), [NEAR])


class TestEvents(unittest.TestCase):
    def test_a_pick_activates_and_nothing_picked_deactivates(self):
        sensor = picking.PrimitivePickSensor()
        sensor.observe(picks())
        self.assertIs(sent(sensor, 'isActive'), True)
        sensor.observe([])
        self.assertIs(sent(sensor, 'isActive'), False)
        self.assertEqual(list(sent(sensor, 'pickedGeometry')), [])

    def test_nothing_picked_from_the_start_sends_nothing(self):
        sensor = picking.PrimitivePickSensor()
        sensor.observe([])
        self.assertIsNone(sent(sensor, 'isActive'))
        self.assertIsNone(sent(sensor, 'pickedGeometry'))

    def test_the_same_picks_again_send_no_geometry(self):
        sensor = picking.VolumePickSensor(sortOrder='ALL')
        sensor.observe(picks())
        sensor.__dict__.pop('pickedGeometry')
        sensor.observe(picks())
        self.assertIsNone(sent(sensor, 'pickedGeometry'))

    def test_a_disabled_sensor_picks_nothing(self):
        sensor = picking.VolumePickSensor()
        sensor.observe(picks())
        sensor.enabled = False
        sensor.observe(picks())
        self.assertIs(sent(sensor, 'isActive'), False)

    def test_a_sensor_of_object_type_none_picks_nothing(self):
        sensor = picking.VolumePickSensor(objectType=['NONE'])
        self.assertFalse(sensor.senses())
        sensor.observe(picks())
        self.assertIsNone(sent(sensor, 'isActive'))

    def test_the_line_sensor_sends_the_chosen_picks_points(self):
        sensor = picking.LinePickSensor(sortOrder='ALL_SORTED')
        sensor.observe([
            picking.Pick(FAR, 4.0, points=[(0, 0, -4)], normals=[(0, 0, 1)],
                         texCoords=[(0.5, 0.5, 0)]),
            picking.Pick(NEAR, 2.0, points=[(0, 0, -2), (0, 0, -3)],
                         normals=[(0, 0, 1), (0, 0, -1)],
                         texCoords=[(0, 0, 0), (1, 0, 0)]),
        ])
        self.assertTrue(np.allclose(sent(sensor, 'pickedPoint'),
                                    [(0, 0, -2), (0, 0, -3), (0, 0, -4)]))
        self.assertTrue(np.allclose(sent(sensor, 'pickedNormal'),
                                    [(0, 0, 1), (0, 0, -1), (0, 0, 1)]))
        self.assertTrue(np.allclose(sent(sensor, 'pickedTextureCoordinate'),
                                    [(0, 0, 0), (1, 0, 0), (0.5, 0.5, 0)]))

    def test_the_line_sensor_sends_points_of_the_closest_alone(self):
        sensor = picking.LinePickSensor()
        sensor.observe([picking.Pick(FAR, 4.0, points=[(0, 0, -4)]),
                        picking.Pick(NEAR, 2.0, points=[(0, 0, -2)])])
        self.assertTrue(np.allclose(sent(sensor, 'pickedPoint'), [(0, 0, -2)]))

    def test_the_point_sensor_sends_the_points_inside(self):
        sensor = picking.PointPickSensor()
        sensor.observe([picking.Pick(NEAR, 1.0, points=[(1, 2, 3)])])
        self.assertTrue(np.allclose(sent(sensor, 'pickedPoint'), [(1, 2, 3)]))
        self.assertFalse(hasattr(picking.PointPickSensor, 'pickedNormal'))

    def test_unchanged_points_are_not_sent_again(self):
        sensor = picking.PointPickSensor()
        sensor.observe([picking.Pick(NEAR, 1.0, points=[(1, 2, 3)])])
        sensor.__dict__.pop('pickedPoint')
        sensor.observe([picking.Pick(NEAR, 1.0, points=[(1, 2, 3)])])
        self.assertIsNone(sent(sensor, 'pickedPoint'))

    def test_the_runtime_builds_the_pick_sensors(self):
        for name in ('LinePickSensor', 'PointPickSensor', 'PrimitivePickSensor',
                     'VolumePickSensor'):
            self.assertIs(runtime.PROTOTYPES[name], picking.PICK_SENSORS[name])


if __name__ == '__main__':
    unittest.main()
