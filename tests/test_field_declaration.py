"""Declaring a field, and what the declaration is good for.

A field binds a name, a type, an exposure and a default, and the rest of the
library reads that declaration back: the parser looks a type up by its VRML97
name, the lineariser writes the declaration into a PROTO, a copier makes a new
prototype's fields from an old one's, and the cache watches a field for
changes.

`tests/test_basefield.py` covers the storage underneath these;
`tests/test_field_assignment.py` covers what assignment does to a node;
`tests/test_field_coercion.py` covers what each type will read.
"""

import contextlib
import io
import unittest
import weakref

from pydispatch import dispatcher

from vrml import field, fieldtypes, node


class Client:
    """Something to hold a value, as a node does."""


class Held:
    """Something a weak field can point at, since a weak reference needs a
    class that allows one."""


class Printed:
    """What was written to stdout inside the block."""

    def __enter__(self):
        self._buffer = io.StringIO()
        self._redirect = contextlib.redirect_stdout(self._buffer)
        self._redirect.__enter__()
        return self

    def __exit__(self, *exception):
        self._redirect.__exit__(*exception)
        self.text = self._buffer.getvalue()
        return False


class Buffered:
    """As much of a lineariser as a field's writing methods read."""

    def __init__(self):
        self.buffer = io.StringIO()
        self.linvalues = {'curindent': '', 'indent': '\t', 'numsep': ',',
                          'mffieldsep': '\n', 'subelspacer': ', ',
                          'courtesyspace': ' ', 'full_element_separator': '\n'}


class TestLookingATypeUpByName(unittest.TestCase):
    """The parser has a type's VRML97 name and needs the class."""

    def test_a_field_type_is_registered_under_its_vrml_name(self):
        self.assertIs(field.baseFieldTypes['SFFloat'], fieldtypes.SFFloat)

    def test_an_event_type_is_registered_separately(self):
        self.assertIs(field.baseEventTypes['SFFloat'], fieldtypes.SFFloatEvt)

    def test_a_field_may_be_declared_by_that_name(self):
        declared = field.newField('size', 'SFFloat', 1, 2.0)
        self.assertIsInstance(declared, fieldtypes.SFFloat)
        self.assertEqual(declared.name, 'size')
        self.assertEqual(declared.getDefault(), 2.0)

    def test_a_field_may_be_declared_by_its_class_instead(self):
        declared = field.newField('size', fieldtypes.SFFloat, 1, 2.0)
        self.assertIsInstance(declared, fieldtypes.SFFloat)

    def test_an_event_may_be_declared_by_name(self):
        declared = field.newEvent('changed', 'SFFloat')
        self.assertIsInstance(declared, fieldtypes.SFFloatEvt)

    def test_an_event_may_be_declared_by_its_class(self):
        declared = field.newEvent('changed', fieldtypes.SFFloatEvt, 0)
        self.assertEqual(declared.direction, 0)

    def test_the_type_name_is_the_declared_one(self):
        self.assertEqual(fieldtypes.SFFloat('size').typeName(), 'SFFloat')

    def test_a_class_without_one_is_named_for_itself(self):
        class Unnamed(field.Field):
            pass

        self.assertEqual(field.typeName(Unnamed), 'Unnamed')


class TestRegisteringAType(unittest.TestCase):
    """`register` files a class under its type name, and says so when a name
    is taken over."""

    def setUp(self):
        self.fields = dict(field.baseFieldTypes)
        self.events = dict(field.baseEventTypes)

    def tearDown(self):
        field.baseFieldTypes.clear()
        field.baseFieldTypes.update(self.fields)
        field.baseEventTypes.clear()
        field.baseEventTypes.update(self.events)

    def test_a_field_class_goes_in_with_the_fields(self):
        class SFThing(field.Field):
            fieldType = 'SFThing'

        field.register(SFThing)
        self.assertIs(field.baseFieldTypes['SFThing'], SFThing)
        self.assertNotIn('SFThing', field.baseEventTypes)

    def test_an_event_class_goes_in_with_the_events(self):
        class SFThingEvt(field.Event):
            fieldType = 'SFThing'

        field.register(SFThingEvt)
        self.assertIs(field.baseEventTypes['SFThing'], SFThingEvt)
        self.assertNotIn('SFThing', field.baseFieldTypes)

    def test_taking_a_name_over_is_reported(self):
        """Two classes under one name is how a typo in a new field type
        stays hidden, so it is said out loud."""

        class SFThing(field.Field):
            fieldType = 'SFThing'

        class Replacement(field.Field):
            fieldType = 'SFThing'

        field.register(SFThing)
        with Printed() as said:
            field.register(Replacement)
        self.assertIn('SFThing', said.text)
        self.assertIs(field.baseFieldTypes['SFThing'], Replacement)


class TestWhatTheDeclarationSays(unittest.TestCase):
    def test_an_exposed_field_says_so(self):
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        self.assertTrue(str(declared).startswith('exposedField'))

    def test_a_plain_field_says_field(self):
        declared = fieldtypes.SFFloat('size', 0, 1.0)
        self.assertTrue(str(declared).startswith('field'))

    def test_it_names_the_type_and_the_field(self):
        self.assertEqual(str(fieldtypes.SFFloat('size', 1, 1.0)),
                         'exposedField SFFloat size 1.0')

    def test_a_built_default_is_written_as_an_empty_list(self):
        """`list` as the default means each node gets its own, and what a
        reader wants to see is the value it stands for."""
        self.assertIn('[]', str(fieldtypes.MFFloat('heights', 1, list)))

    def test_a_long_default_is_cut_short(self):
        declared = fieldtypes.SFString('title', 1, 'a' * 100)
        self.assertLess(len(str(declared)), 60)

    def test_the_declaration_is_the_documentation(self):
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        self.assertEqual(declared.__doc__, str(declared))


class TestOrderingFields(unittest.TestCase):
    """The lineariser sorts a node's fields, so that two writings of one
    scene are the same text."""

    def test_they_order_by_type_then_name(self):
        first = fieldtypes.SFFloat('size')
        second = fieldtypes.SFFloat('title')
        self.assertLess(first, second)

    def test_the_type_name_is_looked_at_first(self):
        self.assertLess(fieldtypes.MFFloat('zzz'), fieldtypes.SFFloat('aaa'))

    def test_something_that_is_not_a_field_does_not_order_before_one(self):
        self.assertFalse(fieldtypes.SFFloat('size') < 'a string')


class TestSayingWhetherAValueWasSet(unittest.TestCase):
    """`fhas` is what the copier and the lineariser ask before writing a
    value out: a field left at its default is not written."""

    def test_a_client_that_set_one_has_it(self):
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        client = Client()
        declared.fset(client, 2.0)
        self.assertTrue(declared.fhas(client))

    def test_a_client_that_did_not_has_not(self):
        self.assertFalse(fieldtypes.SFFloat('size', 1, 1.0).fhas(Client()))

    def test_a_prototype_that_set_one_has_it(self):
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        prototype = type('Prototype', (object,), {'size': declared})
        declared.fset(prototype, 2.0)
        self.assertTrue(declared.fhas(prototype))

    def test_a_prototype_that_only_declares_it_has_not(self):
        """Declaring a field is not setting a value for it: reading the name
        off the class answers the field itself."""
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        prototype = type('Prototype', (object,), {'size': declared})
        self.assertFalse(declared.fhas(prototype))
        self.assertFalse(declared.fhas(type('Sub', (prototype,), {})))

    def test_a_prototype_without_the_field_at_all_has_not(self):
        self.assertFalse(fieldtypes.SFFloat('size', 1, 1.0)
                         .fhas(type('Bare', (object,), {})))


class TestCopying(unittest.TestCase):
    """A copier duplicates a prototype by copying each field declaration, and
    a node by copying each value that was set."""

    def test_copying_for_a_prototype_makes_a_new_declaration(self):
        declared = fieldtypes.SFFloat('size', 0, 2.0)
        copied = declared.copy(type('Prototype', (object,), {}))
        self.assertIsNot(copied, declared)
        self.assertEqual(copied.name, 'size')
        self.assertEqual(copied.exposure, 0)
        self.assertEqual(copied.getDefault(), 2.0)

    def test_copying_for_a_node_that_set_a_value_answers_the_value(self):
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        client = Client()
        declared.fset(client, 2.0)
        self.assertEqual(declared.copy(client), 2.0)

    def test_copying_for_a_node_that_did_not_answers_nothing(self):
        """`_NULL`, which is the copier's sign to leave the field alone."""
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        self.assertIs(declared.copy(Client()), field._NULL)

    def test_the_base_copies_a_value_as_it_stands(self):
        given = object()
        self.assertIs(fieldtypes.SFFloat('size').copyValue(given), given)


class TestWritingTheDeclarationOut(unittest.TestCase):
    """`fieldVrmlstr` writes what a PROTO declares, which is the type, the
    name and the default."""

    def wrote(self, declared):
        lineariser = Buffered()
        declared.fieldVrmlstr(lineariser)
        return lineariser.buffer.getvalue()

    def test_an_exposed_field_says_so(self):
        written = self.wrote(fieldtypes.SFFloat('size', 1, 1.0))
        self.assertTrue(written.startswith('exposedField SFFloat size'))

    def test_a_plain_field_says_field(self):
        written = self.wrote(fieldtypes.SFFloat('size', 0, 1.0))
        self.assertTrue(written.startswith('field SFFloat size'))

    def test_the_default_is_written_in_its_vrml_form(self):
        self.assertTrue(self.wrote(fieldtypes.SFFloat('size', 1, 0.5))
                        .endswith('.5'))

    def test_a_type_with_nothing_to_write_writes_the_declaration_alone(self):
        """`Field.vrmlstr` answers an empty string, so a type that has not
        said how to write a value still declares itself."""

        class Silent(field.Field):
            fieldType = 'Silent'
            defaultDefault = None

        self.assertEqual(self.wrote(Silent('thing', 1)),
                         'exposedField Silent thing ')

    def test_an_event_writes_its_direction(self):
        lineariser = Buffered()
        written = fieldtypes.SFFloatEvt('changed', 1).eventVrmlstr(lineariser)
        self.assertEqual(written, 'eventOut SFFloat changed')
        self.assertEqual(lineariser.buffer.getvalue(), written)

    def test_an_event_in_says_so(self):
        lineariser = Buffered()
        self.assertEqual(fieldtypes.SFFloatEvt('set_size', 0)
                         .eventVrmlstr(lineariser), 'eventIn SFFloat set_size')


class TestWatchingAField(unittest.TestCase):
    """`watch` is how the render cache hears that a value changed."""

    def heard(self, connect):
        told = []
        declared = fieldtypes.SFFloat('size', 1, 1.0)
        client = Client()

        def receiver(signal, sender, **named):
            told.append(signal[0])

        connect(declared, client, receiver)
        try:
            declared.fset(client, 2.0)
        finally:
            dispatcher.disconnect(receiver, sender=client)
        return told

    def test_a_field_change_reaches_the_receiver(self):
        self.assertEqual(
            self.heard(lambda declared, client, receiver:
                       declared.watch(client, receiver)), ['set'])

    def test_an_event_may_be_watched_the_same_way(self):
        told = []
        declared = fieldtypes.SFFloatEvt('changed', 1)
        client = Client()

        def receiver(signal, sender, **named):
            told.append(signal[0])

        declared.watch(client, receiver)
        try:
            declared.__set__(client, 2.0)
        finally:
            dispatcher.disconnect(receiver, sender=client)
        self.assertEqual(told, ['set'])


class TestAnEventPort(unittest.TestCase):
    """An event keeps the last value sent through it, and hands it to the
    node's handler on the way past."""

    class Handling:
        def __init__(self):
            self.seen = []

        def on_changed(self, value):
            self.seen.append(value)

    def test_the_value_reads_back(self):
        declared = fieldtypes.SFFloatEvt('changed', 1)
        client = Client()
        declared.__set__(client, 2.0)
        self.assertEqual(declared.__get__(client), 2.0)

    def test_a_value_that_was_never_sent_is_not_there(self):
        declared = fieldtypes.SFFloatEvt('changed', 1)
        with self.assertRaises(AttributeError) as caught:
            declared.__get__(Client())
        self.assertIn('changed', str(caught.exception))

    def test_reading_it_off_the_class_answers_the_event(self):
        declared = fieldtypes.SFFloatEvt('changed', 1)
        self.assertIs(declared.__get__(None), declared)

    def test_the_nodes_handler_is_called_with_the_value(self):
        declared = fieldtypes.SFFloatEvt('changed', 1)
        client = self.Handling()
        declared.__set__(client, 2.0)
        self.assertEqual(client.seen, [2.0])

    def test_a_node_with_no_handler_still_keeps_the_value(self):
        declared = fieldtypes.SFFloatEvt('changed', 1)
        client = Client()
        declared.__set__(client, 2.0)
        self.assertEqual(client.__dict__['changed'], 2.0)

    def test_it_may_be_sent_silently(self):
        told = []
        declared = fieldtypes.SFFloatEvt('changed', 1)
        client = Client()

        def receiver(signal, sender, **named):
            told.append(signal[0])

        declared.watch(client, receiver)
        try:
            declared.__set__(client, 2.0, notify=0)
        finally:
            dispatcher.disconnect(receiver, sender=client)
        self.assertEqual(told, [])

    def test_it_describes_itself_by_direction(self):
        self.assertEqual(str(fieldtypes.SFFloatEvt('changed', 1)),
                         'eventOut SFFloat changed')
        self.assertEqual(str(fieldtypes.SFFloatEvt('set_size', 0)),
                         'eventIn SFFloat set_size')

    def test_it_knows_its_type_name(self):
        self.assertEqual(fieldtypes.SFFloatEvt('changed', 1).typeName(),
                         'SFFloat')

    def test_cloning_keeps_the_name_and_direction(self):
        declared = fieldtypes.SFFloatEvt('changed', 0)
        copied = declared.clone()
        self.assertIsNot(copied, declared)
        self.assertEqual(copied.name, 'changed')
        self.assertEqual(copied.direction, 0)

    def test_cloning_may_rename_it(self):
        copied = fieldtypes.SFFloatEvt('changed', 0).clone('renamed', 1)
        self.assertEqual(copied.name, 'renamed')
        self.assertEqual(copied.direction, 1)


class TestAWeakField(unittest.TestCase):
    """A weak field stores a reference, so that what it points at is free to
    go away -- which is how a node holds its scene root without keeping the
    whole scene alive."""

    def declared(self):
        return node.WeakSFNode('scenegraph', 1, None)

    def test_what_was_set_reads_back_as_the_object(self):
        declared, client, held = self.declared(), Client(), Held()
        declared.fset(client, held)
        self.assertIs(declared.fget(client), held)

    def test_setting_answers_the_object_rather_than_the_reference(self):
        declared, held = self.declared(), Held()
        self.assertIs(declared.fset(Client(), held), held)

    def test_a_reference_may_be_given_instead_of_the_object(self):
        declared, client, held = self.declared(), Client(), Held()
        declared.fset(client, weakref.ref(held))
        self.assertIs(declared.fget(client), held)

    def test_what_it_holds_is_free_to_go_away(self):
        declared, client = self.declared(), Client()
        held = Held()
        declared.fset(client, held)
        del held
        self.assertIsNone(declared.fget(client))

    def test_the_entry_is_dropped_once_it_has_gone(self):
        """So that the client is not left holding a dead reference."""
        declared, client = self.declared(), Client()
        held = Held()
        declared.fset(client, held)
        del held
        declared.fget(client)
        self.assertNotIn('scenegraph', client.__dict__)

    def test_setting_nothing_clears_it(self):
        declared, client = self.declared(), Client()
        declared.fset(client, Held())
        self.assertIsNone(declared.fset(client, None))
        self.assertNotIn('scenegraph', client.__dict__)

    def test_setting_nothing_when_there_was_nothing_is_harmless(self):
        declared = self.declared()
        self.assertIsNone(declared.fset(Client(), None))

    def test_reading_one_that_was_never_set_answers_the_default(self):
        """An SFNode's default is the NULL node, which is what a weak one
        answers as well until something is put in it."""
        self.assertIs(self.declared().fget(Client()), node.NULL)

    def test_a_prototype_may_hold_one_too(self):
        declared = self.declared()
        prototype = type('Prototype', (object,), {'scenegraph': declared})
        held = Held()
        declared.fset(prototype, held)
        self.assertIs(declared.fget(prototype), held)


if __name__ == '__main__':
    unittest.main()
