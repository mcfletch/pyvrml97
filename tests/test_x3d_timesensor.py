"""X3D's TimeSensor (ISO/IEC 19775-1, 8.4.1), advanced by whoever keeps time.

`advance(now)` sends what the sensor sends at `now`: `isActive` as it starts
and stops, `cycleTime` at the start of each cycle, `fraction_changed`, `time`
and `elapsedTime` while it runs, and `isPaused` as it pauses and resumes. It
answers whether it sent anything.
"""

import unittest

from vrml.x3d import runtime
from vrml.x3d.timesensor import TimeSensor


def sent(node, name):
    return node.__dict__.get(name)


class TestStarting(unittest.TestCase):
    def test_a_looping_sensor_from_time_zero_runs(self):
        sensor = TimeSensor(cycleInterval=2.0, loop=True)
        self.assertTrue(sensor.advance(5.0))
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertAlmostEqual(sent(sensor, 'fraction_changed'), 0.5)
        self.assertEqual(sent(sensor, 'time'), 5.0)

    def test_a_single_cycle_long_past_does_not_run(self):
        sensor = TimeSensor(cycleInterval=2.0, loop=False)
        self.assertFalse(sensor.advance(100.0))
        self.assertIsNone(sent(sensor, 'isActive'))

    def test_a_later_start_waits_for_it(self):
        sensor = TimeSensor(cycleInterval=2.0, startTime=10.0)
        self.assertFalse(sensor.advance(9.0))
        sensor.advance(10.5)
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertEqual(sent(sensor, 'cycleTime'), 10.5)
        self.assertAlmostEqual(sent(sensor, 'fraction_changed'), 0.25)

    def test_a_single_cycle_ends_at_one(self):
        sensor = TimeSensor(cycleInterval=2.0, startTime=10.0)
        sensor.advance(11.0)
        sensor.advance(13.0)
        self.assertEqual(sent(sensor, 'fraction_changed'), 1.0)
        self.assertIs(sent(sensor, 'isActive'), False)
        sensor.__dict__.pop('fraction_changed')
        self.assertFalse(sensor.advance(14.0))
        self.assertIsNone(sent(sensor, 'fraction_changed'))

    def test_each_new_cycle_sends_cycletime(self):
        sensor = TimeSensor(cycleInterval=2.0, loop=True, startTime=10.0)
        sensor.advance(10.5)
        sensor.advance(11.0)
        self.assertEqual(sent(sensor, 'cycleTime'), 10.5)
        sensor.advance(12.5)
        self.assertEqual(sent(sensor, 'cycleTime'), 12.5)

    def test_elapsed_time_counts_from_the_start(self):
        sensor = TimeSensor(cycleInterval=2.0, loop=True, startTime=10.0)
        sensor.advance(10.0)
        sensor.advance(13.0)
        self.assertAlmostEqual(sent(sensor, 'elapsedTime'), 3.0)


class TestStopping(unittest.TestCase):
    def test_stoptime_after_the_start_stops_it(self):
        sensor = TimeSensor(cycleInterval=4.0, loop=True, startTime=10.0, stopTime=12.0)
        sensor.advance(11.0)
        sensor.advance(12.5)
        self.assertIs(sent(sensor, 'isActive'), False)
        self.assertFalse(sensor.advance(13.0))

    def test_stoptime_before_the_start_is_ignored(self):
        sensor = TimeSensor(cycleInterval=4.0, loop=True, startTime=10.0, stopTime=5.0)
        sensor.advance(11.0)
        self.assertIs(sent(sensor, 'isActive'), True)

    def test_disabling_stops_it(self):
        sensor = TimeSensor(cycleInterval=2.0, loop=True)
        sensor.advance(1.0)
        sensor.enabled = False
        sensor.advance(1.5)
        self.assertIs(sent(sensor, 'isActive'), False)

    def test_a_cycle_of_no_length_does_not_run(self):
        sensor = TimeSensor(cycleInterval=0.0, loop=True)
        self.assertFalse(sensor.advance(1.0))

    def test_starting_again_after_a_stop(self):
        sensor = TimeSensor(cycleInterval=2.0, startTime=10.0)
        sensor.advance(10.5)
        sensor.advance(12.5)
        sensor.startTime = 20.0
        sensor.advance(20.5)
        self.assertIs(sent(sensor, 'isActive'), True)
        self.assertAlmostEqual(sent(sensor, 'fraction_changed'), 0.25)


class TestPausing(unittest.TestCase):
    def test_pausing_holds_the_fraction_and_resuming_carries_on(self):
        sensor = TimeSensor(cycleInterval=4.0, loop=True, startTime=10.0)
        sensor.advance(11.0)
        sensor.pauseTime = 11.0
        sensor.advance(12.0)
        self.assertIs(sent(sensor, 'isPaused'), True)
        sensor.__dict__.pop('fraction_changed')
        sensor.advance(13.0)
        self.assertIsNone(sent(sensor, 'fraction_changed'))
        sensor.resumeTime = 14.0
        sensor.advance(15.0)
        self.assertIs(sent(sensor, 'isPaused'), False)
        # A second running before the pause at 11, a second after the resume at 14.
        self.assertAlmostEqual(sent(sensor, 'fraction_changed'), 0.5)
        self.assertAlmostEqual(sent(sensor, 'elapsedTime'), 2.0)


class TestRegistered(unittest.TestCase):
    def test_it_is_in_the_runtime(self):
        self.assertIs(runtime.PROTOTYPES['TimeSensor'], TimeSensor)


if __name__ == '__main__':
    unittest.main()
