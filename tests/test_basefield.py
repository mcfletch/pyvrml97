"""The field primitives, and the two implementations of them.

`vrml.field.BaseField` is a Python class, and where the accelerator is
installed it is a compiled one instead.  Everything a node does with a field
goes through this handful of calls, so the two have to answer them the same
way: the same value, the same notification, the same error.  A divergence here
is invisible until it reaches whichever half of the user base has the other
build.

`vrml.field.PyBaseField` always names the Python class, so both are reachable
whichever one is installed.  The cases live in `TheContract` and each
implementation gets a class of its own, so a failure names the build it is in.

`tests/test_field.py` covers the `Field` layer above these -- the exposure
flag, copying, the VRML97 forms; this is the storage underneath it.
"""

import unittest

from pydispatch import dispatcher

from vrml import field


class Client:
    """Something to hold a value, as a node does."""


class Recorder:
    """What the notifications a field sends look like from the far end."""

    def __init__(self):
        self.heard = []

    def connect(self, sender):
        dispatcher.connect(self.hear, sender=sender, weak=False)
        return self

    def hear(self, signal, sender, **named):
        self.heard.append((signal[0], named.get('value')))

    def disconnect(self, sender):
        dispatcher.disconnect(self.hear, sender=sender, weak=False)


class TheContract:
    """What both implementations of the primitives have to do.

    `implementation` is the class under test; the concrete cases below bind
    it.
    """

    implementation = field.PyBaseField

    def a_field(self, name='size', default=1.0):
        return self.implementation(name, default)

    def a_holder(self, held):
        """A class with `held` as one of its attributes, so that the
        descriptor protocol is what reaches it."""
        return type('Holder', (object,), {held.name: held})

    def heard_while(self, act, held=None):
        """The notifications a client received while `act` ran on it."""
        if held is None:
            held = self.a_field()
        client = Client()
        listener = Recorder().connect(client)
        try:
            act(held, client)
        finally:
            listener.disconnect(client)
        return listener.heard

    ### Reading a value
    def test_a_client_with_nothing_set_reads_the_default(self):
        self.assertEqual(self.a_field().fget(Client()), 1.0)

    def test_what_was_set_reads_back(self):
        held, client = self.a_field(), Client()
        held.fset(client, 2.0)
        self.assertEqual(held.fget(client), 2.0)

    def test_setting_answers_the_value_that_was_stored(self):
        self.assertEqual(self.a_field().fset(Client(), 2.0), 2.0)

    def test_reading_the_field_off_the_class_answers_the_field(self):
        """Which is how `protofunctions` gets at the field object itself."""
        held = self.a_field()
        self.assertIs(self.a_holder(held).size, held)

    def test_the_owning_class_may_be_named_as_well(self):
        """`fget` is the descriptor's own `__get__`, which is handed one."""
        self.assertEqual(self.a_field().fget(Client(), Client), 1.0)

    ### A default that is built rather than shared
    def test_a_callable_default_is_called_for_the_value(self):
        self.assertEqual(self.a_field('names', list).fget(Client()), [])

    def test_two_clients_do_not_share_a_built_default(self):
        held = self.a_field('names', list)
        self.assertIsNot(held.fget(Client()), held.fget(Client()))

    def test_a_plain_default_is_the_value_itself(self):
        self.assertEqual(self.a_field().getDefault(), 1.0)

    def test_asking_for_the_default_for_a_client_stores_it(self):
        """So that the next read is a dictionary lookup rather than a build."""
        held, client = self.a_field('names', list), Client()
        held.getDefault(client)
        self.assertIn('names', client.__dict__)

    def test_storing_it_that_way_says_nothing(self):
        """Reading a value nobody set is not a change to hear about."""
        self.assertEqual(self.heard_while(lambda held, client:
                                          held.fget(client)), [])

    def test_a_callable_default_is_marked_as_one(self):
        self.assertTrue(self.a_field('names', list).call_default)

    def test_a_plain_default_is_not(self):
        self.assertFalse(self.a_field().call_default)

    def test_the_name_and_the_default_read_back(self):
        held = self.a_field()
        self.assertEqual(held.name, 'size')
        self.assertEqual(held.defaultobj, 1.0)

    ### Deleting
    def test_deleting_brings_the_default_back(self):
        held, client = self.a_field(), Client()
        held.fset(client, 2.0)
        held.fdel(client)
        self.assertEqual(held.fget(client), 1.0)

    def test_deleting_answers_what_was_there(self):
        held, client = self.a_field(), Client()
        held.fset(client, 2.0)
        self.assertEqual(held.fdel(client), 2.0)

    def test_deleting_what_was_never_set_says_which_field(self):
        with self.assertRaises(AttributeError) as caught:
            self.a_field().fdel(Client())
        self.assertIn('size', str(caught.exception))

    def test_the_descriptor_protocol_deletes_it_too(self):
        held = self.a_field()
        client = self.a_holder(held)()
        client.size = 2.0
        del client.size
        self.assertEqual(client.size, 1.0)

    ### Notifying
    def test_setting_is_announced_with_the_new_value(self):
        heard = self.heard_while(lambda held, client: held.fset(client, 2.0))
        self.assertEqual(heard, [('set', 2.0)])

    def test_deleting_is_announced(self):
        def act(held, client):
            held.fset(client, 2.0, False)
            held.fdel(client)

        self.assertEqual(self.heard_while(act), [('del', None)])

    def test_a_caller_may_ask_for_silence(self):
        heard = self.heard_while(
            lambda held, client: held.fset(client, 2.0, False))
        self.assertEqual(heard, [])

    def test_deleting_may_be_silent_as_well(self):
        def act(held, client):
            held.fset(client, 2.0, False)
            held.fdel(client, False)

        self.assertEqual(self.heard_while(act), [])

    def test_assignment_through_the_descriptor_is_announced(self):
        held = self.a_field()
        client = self.a_holder(held)()
        listener = Recorder().connect(client)
        try:
            client.size = 2.0
        finally:
            listener.disconnect(client)
        self.assertEqual(listener.heard, [('set', 2.0)])

    def test_deletion_through_the_descriptor_is_announced(self):
        held = self.a_field()
        client = self.a_holder(held)()
        held.fset(client, 2.0, False)
        listener = Recorder().connect(client)
        try:
            del client.size
        finally:
            listener.disconnect(client)
        self.assertEqual(listener.heard, [('del', None)])

    ### A prototype, which holds its values on the class
    def prototype(self):
        """A field on a base class and a subclass to hold values on, which is
        the shape `protofunctions` works with.

        A class's `__dict__` is a read-only proxy, so this case cannot store
        the way a node's does -- the value shadows the field in the subclass
        instead.
        """
        held = self.a_field()
        return held, type('Prototype', (self.a_holder(held),), {})

    def test_a_value_set_on_a_prototype_reads_back(self):
        held, prototype = self.prototype()
        held.fset(prototype, 2.0)
        self.assertEqual(prototype.size, 2.0)

    def test_it_is_the_subclass_that_holds_it(self):
        held, prototype = self.prototype()
        held.fset(prototype, 2.0)
        self.assertIn('size', prototype.__dict__)

    def test_deleting_it_uncovers_the_field_again(self):
        held, prototype = self.prototype()
        held.fset(prototype, 2.0)
        self.assertEqual(held.fdel(prototype), 2.0)
        self.assertIs(prototype.size, held)

    def test_deleting_one_a_prototype_never_set_says_which_field(self):
        held, prototype = self.prototype()
        with self.assertRaises(AttributeError) as caught:
            held.fdel(prototype)
        self.assertIn('size', str(caught.exception))

    ### What it refuses
    def refusing(self, error):
        """A field whose type will take nothing, to see what the refusal
        says."""

        class Refusing(self.implementation):
            def coerce(self, value):
                raise error('no')

        return Refusing('size', 1.0)

    def test_a_value_error_says_what_the_type_said(self):
        """The field describes itself -- `Field.__str__` writes the VRML97
        declaration -- and carries the type's own reason along."""
        with self.assertRaises(ValueError) as caught:
            self.refusing(ValueError).fset(Client(), object())
        self.assertIn('could not accept value', str(caught.exception))
        self.assertIn('(no)', str(caught.exception))

    def test_a_field_that_refuses_a_value_names_itself(self):
        class Refusing(field.Field):
            defaultDefault = 1.0

            def coerce(self, value):
                raise ValueError('no')

        with self.assertRaises(ValueError) as caught:
            Refusing('size').fset(Client(), object())
        self.assertIn('size', str(caught.exception))

    def test_a_type_error_becomes_a_value_error_naming_the_type(self):
        with self.assertRaises(ValueError) as caught:
            self.refusing(TypeError).fset(Client(), 2.0)
        self.assertIn('float', str(caught.exception))

    def test_nothing_is_stored_when_it_refuses(self):
        held, client = self.refusing(ValueError), Client()
        with self.assertRaises(ValueError):
            held.fset(client, 2.0)
        self.assertNotIn('size', client.__dict__)

    ### Coercion and checking
    def test_coerce_answers_what_it_was_given(self):
        given = object()
        self.assertIs(self.a_field().coerce(given), given)

    def test_check_answers_what_it_was_given(self):
        given = object()
        self.assertIs(self.a_field().check(given), given)

    def test_a_subclass_coercion_is_used_when_a_value_is_stored(self):
        class Doubling(self.implementation):
            def coerce(self, value):
                return value * 2

        held, client = Doubling('size', 1.0), Client()
        held.fset(client, 2.0)
        self.assertEqual(held.fget(client), 4.0)


class TestThePythonImplementation(TheContract, unittest.TestCase):
    implementation = field.PyBaseField


@unittest.skipIf(field.BaseField is field.PyBaseField,
                 'the accelerator is not installed')
class TestTheAcceleratedImplementation(TheContract, unittest.TestCase):
    implementation = field.BaseField


if __name__ == '__main__':
    unittest.main()
