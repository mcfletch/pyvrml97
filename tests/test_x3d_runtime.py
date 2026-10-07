"""X3D's event utilities, sequencers and KeySensor: what each sends for what it receives.

`vrml.x3d.runtime` gives each its behaviour on top of the X3D declaration. An
inputOnly event set on a node calls its handler; the outputs it sets are
forwarded along routes as any field change is.
"""

import unittest

from vrml import x3d
from vrml.x3d import nodes, runtime


def outputs(node, name):
    """The value of an output event, or None where it has not been sent"""
    return node.__dict__.get(name)


class TestBooleanFilter(unittest.TestCase):
    def test_true_is_sent_as_true_and_negated(self):
        made = runtime.BooleanFilter()
        made.set_boolean = True
        self.assertIs(outputs(made, 'inputTrue'), True)
        self.assertIs(outputs(made, 'inputNegate'), False)
        self.assertIsNone(outputs(made, 'inputFalse'))

    def test_false_is_sent_as_false_and_negated(self):
        made = runtime.BooleanFilter()
        made.set_boolean = False
        self.assertIs(outputs(made, 'inputFalse'), False)
        self.assertIs(outputs(made, 'inputNegate'), True)
        self.assertIsNone(outputs(made, 'inputTrue'))


class TestBooleanToggle(unittest.TestCase):
    def test_true_flips_it_and_false_does_not(self):
        made = runtime.BooleanToggle()
        made.set_boolean = True
        self.assertTrue(made.toggle)
        made.set_boolean = False
        self.assertTrue(made.toggle)
        made.set_boolean = True
        self.assertFalse(made.toggle)


class TestTriggers(unittest.TestCase):
    def test_a_boolean_trigger_sends_true_for_a_time(self):
        made = runtime.BooleanTrigger()
        made.set_triggerTime = 12.5
        self.assertIs(outputs(made, 'triggerTrue'), True)

    def test_an_integer_trigger_sends_its_key_for_true(self):
        made = runtime.IntegerTrigger(integerKey=7)
        made.set_boolean = False
        self.assertIsNone(outputs(made, 'triggerValue'))
        made.set_boolean = True
        self.assertEqual(outputs(made, 'triggerValue'), 7)

    def test_a_time_trigger_sends_the_time_now(self):
        saved = runtime.clock
        runtime.clock = lambda: 1234.5
        try:
            made = runtime.TimeTrigger()
            made.set_boolean = False
            self.assertEqual(outputs(made, 'triggerTime'), 1234.5)
        finally:
            runtime.clock = saved


class TestSequencers(unittest.TestCase):
    def sequencer(self):
        return runtime.IntegerSequencer(key=[0.0, 0.5, 1.0], keyValue=[10, 20, 30])

    def test_a_fraction_chooses_the_value_of_the_last_key_reached(self):
        made = self.sequencer()
        for fraction, expected in ((0.0, 10), (0.49, 10), (0.5, 20), (0.99, 20), (1.0, 30)):
            made.set_fraction = fraction
            self.assertEqual(outputs(made, 'value_changed'), expected, fraction)

    def test_before_the_first_key_is_the_first_value(self):
        made = runtime.IntegerSequencer(key=[0.2, 0.6], keyValue=[1, 2])
        made.set_fraction = 0.1
        self.assertEqual(outputs(made, 'value_changed'), 1)

    def test_a_value_is_sent_only_when_it_changes(self):
        made = self.sequencer()
        sent = []
        made.set_fraction = 0.1
        sent.append(outputs(made, 'value_changed'))
        made.__dict__.pop('value_changed')
        made.set_fraction = 0.2
        self.assertIsNone(outputs(made, 'value_changed'))
        self.assertEqual(sent, [10])

    def test_next_and_previous_step_and_wrap(self):
        made = self.sequencer()
        made.set_fraction = 0.9
        made.next = True
        self.assertEqual(outputs(made, 'value_changed'), 30)
        made.next = True
        self.assertEqual(outputs(made, 'value_changed'), 10)
        made.previous = True
        self.assertEqual(outputs(made, 'value_changed'), 30)
        made.next = False
        self.assertEqual(outputs(made, 'value_changed'), 30)

    def test_a_boolean_sequencer(self):
        made = runtime.BooleanSequencer(key=[0.0, 0.5], keyValue=[True, False])
        made.set_fraction = 0.75
        self.assertIs(outputs(made, 'value_changed'), False)

    def test_no_keys_sends_nothing(self):
        made = runtime.IntegerSequencer()
        made.set_fraction = 0.5
        made.next = True
        self.assertIsNone(outputs(made, 'value_changed'))


class TestKeySensor(unittest.TestCase):
    def test_a_character_is_a_key_press_and_release(self):
        made = runtime.KeySensor()
        made.keyDown('a')
        self.assertEqual(outputs(made, 'keyPress'), 'a')
        self.assertIs(outputs(made, 'isActive'), True)
        made.keyUp('a')
        self.assertEqual(outputs(made, 'keyRelease'), 'a')
        self.assertIs(outputs(made, 'isActive'), False)

    def test_an_action_key_is_its_number(self):
        made = runtime.KeySensor()
        made.keyDown('UP')
        self.assertEqual(outputs(made, 'actionKeyPress'), runtime.ACTION_KEYS['UP'])
        made.keyUp('F3')
        self.assertEqual(outputs(made, 'actionKeyRelease'), 3)

    def test_a_modifier_is_true_while_held(self):
        made = runtime.KeySensor()
        made.keyDown('SHIFT')
        self.assertIs(outputs(made, 'shiftKey'), True)
        made.keyUp('SHIFT')
        self.assertIs(outputs(made, 'shiftKey'), False)

    def test_it_stays_active_while_any_key_is_held(self):
        made = runtime.KeySensor()
        made.keyDown('a')
        made.keyDown('b')
        made.keyUp('a')
        self.assertIs(outputs(made, 'isActive'), True)
        made.keyUp('b')
        self.assertIs(outputs(made, 'isActive'), False)

    def test_a_disabled_sensor_sends_nothing(self):
        made = runtime.KeySensor(enabled=False)
        made.keyDown('a')
        self.assertIsNone(outputs(made, 'keyPress'))


class TestStringSensor(unittest.TestCase):
    def test_characters_are_entered_and_return_ends_the_text(self):
        made = runtime.StringSensor()
        for character in 'hi!':
            made.typed(character)
        self.assertEqual(outputs(made, 'enteredText'), 'hi!')
        self.assertIs(outputs(made, 'isActive'), True)
        made.typed('\n')
        self.assertEqual(outputs(made, 'finalText'), 'hi!')
        self.assertEqual(outputs(made, 'enteredText'), '')
        self.assertIs(outputs(made, 'isActive'), False)

    def test_backspace_deletes_where_deletion_is_allowed(self):
        made = runtime.StringSensor()
        for character in 'ab\b':
            made.typed(character)
        self.assertEqual(outputs(made, 'enteredText'), 'a')
        kept = runtime.StringSensor(deletionAllowed=False)
        for character in 'ab\b':
            kept.typed(character)
        self.assertEqual(outputs(kept, 'enteredText'), 'ab')

    def test_return_with_nothing_entered_sends_nothing(self):
        made = runtime.StringSensor()
        made.typed('\n')
        self.assertIsNone(outputs(made, 'finalText'))

    def test_a_disabled_sensor_takes_nothing(self):
        made = runtime.StringSensor(enabled=False)
        made.typed('a')
        self.assertIsNone(outputs(made, 'enteredText'))


class TestFromADocument(unittest.TestCase):
    def test_routes_carry_the_outputs(self):
        scene = x3d.loads(b'''<X3D version="4.0"><Scene>
          <BooleanToggle DEF="T"/>
          <BooleanFilter DEF="F"/>
          <ROUTE fromNode="T" fromField="toggle" toNode="F" toField="set_boolean"/>
        </Scene></X3D>''', prototypes=runtime.PROTOTYPES)
        toggle, flip = scene.getDEF('T'), scene.getDEF('F')
        self.assertIsInstance(toggle, runtime.BooleanToggle)
        toggle.set_boolean = True
        self.assertIs(outputs(flip, 'inputTrue'), True)

    def test_a_document_read_with_no_prototypes_has_the_behaviours(self):
        scene = x3d.loads(b'<X3D version="4.0"><Scene><BooleanToggle DEF="T"/></Scene></X3D>')
        self.assertIsInstance(scene.getDEF('T'), runtime.BooleanToggle)

    def test_every_class_implements_its_declaration(self):
        for name, cls in runtime.PROTOTYPES.items():
            self.assertTrue(issubclass(cls, nodes.CONCRETE_NODES[name]), name)


if __name__ == '__main__':
    unittest.main()
