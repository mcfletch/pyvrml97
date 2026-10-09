"""X3D's LoadSensor (ISO/IEC 19775-1, 9.4.3), and the load state it watches.

A node that reads a url records whether it is loading, has loaded or has
failed (`loadsensor.set_load_state`). A LoadSensor's `observe` reads its
children's states: `isActive` while any is loading, `progress` as they load,
and when all have loaded `isLoaded TRUE` and `loadTime`; a failure, or
`timeOut` passing, sends `isLoaded FALSE`.
"""

import unittest

from vrml.x3d import loadsensor, nodes, runtime
from vrml.x3d.loadsensor import FAILED, LOADED, LOADING, LoadSensor


def sent(node, name):
    return node.__dict__.get(name)


def watched(*states):
    found = [nodes.ImageTexture() for _ in states]
    for node, state in zip(found, states):
        loadsensor.set_load_state(node, state)
    return found


class TestLoadState(unittest.TestCase):
    def test_a_node_that_reads_nothing_has_no_state(self):
        self.assertIsNone(loadsensor.load_state(nodes.ImageTexture()))

    def test_a_state_once_set_is_read_back(self):
        node, = watched(LOADING)
        self.assertEqual(loadsensor.load_state(node), LOADING)


class TestLoading(unittest.TestCase):
    def test_loading_children_activate_and_report_progress(self):
        children = watched(LOADING, LOADED)
        sensor = LoadSensor(children=children)
        self.assertTrue(sensor.observe(now=1.0))
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertAlmostEqual(sent(sensor, 'progress'), 0.5)

    def test_all_loaded_sends_isloaded_and_loadtime(self):
        children = watched(LOADING, LOADED)
        sensor = LoadSensor(children=children)
        sensor.observe(now=1.0)
        loadsensor.set_load_state(children[0], LOADED)
        sensor.observe(now=2.0)
        self.assertIs(sent(sensor, 'isLoaded'), True)
        self.assertEqual(sent(sensor, 'loadTime'), 2.0)
        self.assertAlmostEqual(sent(sensor, 'progress'), 1.0)
        self.assertIs(sent(sensor, 'isActive'), False)
        self.assertFalse(sensor.observe(now=3.0))

    def test_children_loaded_before_it_looked_are_loaded(self):
        sensor = LoadSensor(children=watched(LOADED))
        sensor.observe(now=5.0)
        self.assertIs(sent(sensor, 'isLoaded'), True)
        self.assertEqual(sent(sensor, 'loadTime'), 5.0)

    def test_a_failure_sends_isloaded_false(self):
        children = watched(LOADING, LOADING)
        sensor = LoadSensor(children=children)
        sensor.observe(now=1.0)
        loadsensor.set_load_state(children[1], FAILED)
        sensor.observe(now=2.0)
        self.assertIs(sent(sensor, 'isLoaded'), False)
        self.assertIs(sent(sensor, 'isActive'), False)
        self.assertIsNone(sent(sensor, 'loadTime'))

    def test_timing_out_sends_isloaded_false(self):
        sensor = LoadSensor(children=watched(LOADING), timeOut=3.0)
        sensor.observe(now=1.0)
        sensor.observe(now=3.5)
        self.assertIsNone(sent(sensor, 'isLoaded'))
        sensor.observe(now=4.5)
        self.assertIs(sent(sensor, 'isLoaded'), False)

    def test_loading_again_starts_again(self):
        children = watched(LOADED)
        sensor = LoadSensor(children=children)
        sensor.observe(now=1.0)
        loadsensor.set_load_state(children[0], LOADING)
        sensor.observe(now=2.0)
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertAlmostEqual(sent(sensor, 'progress'), 0.0)

    def test_children_without_a_state_are_not_waited_for(self):
        sensor = LoadSensor(children=[nodes.ImageTexture()] + watched(LOADED))
        sensor.observe(now=1.0)
        self.assertIs(sent(sensor, 'isLoaded'), True)

    def test_a_disabled_sensor_sends_nothing(self):
        self.assertFalse(LoadSensor(children=watched(LOADED), enabled=False).observe(now=1.0))

    def test_no_children_send_not_loaded_once(self):
        sensor = LoadSensor()
        self.assertTrue(sensor.observe(now=1.0))
        self.assertIs(sent(sensor, 'isLoaded'), False)
        self.assertIs(sent(sensor, 'isActive'), False)
        self.assertEqual(sent(sensor, 'progress'), 0.0)
        self.assertIsNone(sent(sensor, 'loadTime'))
        self.assertFalse(sensor.observe(now=2.0))

    def test_new_children_are_watched_afresh(self):
        sensor = LoadSensor()
        sensor.observe(now=1.0)
        sensor.children = watched(LOADED)
        self.assertTrue(sensor.observe(now=2.0))
        self.assertIs(sent(sensor, 'isLoaded'), True)
        sensor.children = []
        self.assertTrue(sensor.observe(now=3.0))
        self.assertIs(sent(sensor, 'isLoaded'), False)

    def test_a_failure_sends_the_part_loaded(self):
        children = watched(LOADED, LOADING, LOADING, LOADING)
        sensor = LoadSensor(children=children)
        sensor.observe(now=1.0)
        loadsensor.set_load_state(children[1], FAILED)
        loadsensor.set_load_state(children[2], LOADED)
        sensor.observe(now=2.0)
        self.assertAlmostEqual(sent(sensor, 'progress'), 0.5)


class TestLoadStateMethod(unittest.TestCase):
    def test_a_node_may_answer_its_own_state(self):
        class Answering(nodes.ImageTexture):
            def loadState(self):
                return FAILED
        self.assertEqual(loadsensor.load_state(Answering()), FAILED)


class TestRegistered(unittest.TestCase):
    def test_it_is_in_the_runtime(self):
        self.assertIs(runtime.PROTOTYPES['LoadSensor'], LoadSensor)


if __name__ == '__main__':
    unittest.main()
