"""The ways into and out of a field value that a file or a program reaches.

Each VRML97 field type reads its value from several shapes -- text from a
file, a number or a sequence from a program, an array of the wrong element
type from numpy -- and writes it back in the shape the file format wants. It
also answers two further questions the rest of the library asks: `check`, for
whether a value is already of the type, and `copyValue`, for what a copy of it
is.

`tests/test_field_coercion.py` covers the ordinary ways in;
`tests/test_vrmlstr.py` covers the ordinary ways out. What is here is the
edges of each: an empty value, a value of the wrong element type, a value too
big for one line, a colour named rather than numbered, and what each type
refuses.
"""

import unittest

import numpy as np

from vrml import fieldtypes


class Lineariser:
    """A lineariser at a chosen depth, which is all `vrmlstr` reads of one."""

    def __init__(self, **overrides):
        from vrml.vrml97 import linearise

        self.linvalues = dict(linearise.defaults)
        self.linvalues.update(overrides)


class TestAString(unittest.TestCase):
    def field(self):
        return fieldtypes.SFString(name='title')

    def test_text_is_taken_as_it_stands(self):
        self.assertEqual(self.field().coerce('a world'), 'a world')

    def test_bytes_are_read_as_utf_8(self):
        """A file is read as bytes, and a generated module may hold them."""
        self.assertEqual(self.field().coerce(b'caf\xc3\xa9'), 'café')

    def test_a_sequence_of_one_is_that_one(self):
        self.assertEqual(self.field().coerce(['only']), 'only')

    def test_nothing_is_the_empty_string(self):
        self.assertEqual(self.field().coerce([]), '')

    def test_several_are_joined(self):
        self.assertEqual(self.field().coerce(['a', 'b']), 'ab')

    def test_a_lazy_sequence_is_drawn_out_first(self):
        self.assertEqual(self.field().coerce(map(str, [1, 2])), '12')

    def test_anything_else_is_written_as_text(self):
        self.assertEqual(self.field().coerce(42), '42')

    def test_it_checks_for_text(self):
        self.assertTrue(self.field().check('a world'))
        self.assertFalse(self.field().check(42))


class TestAListOfStrings(unittest.TestCase):
    def field(self):
        return fieldtypes.MFString(name='info')

    def test_one_string_becomes_a_list_of_one(self):
        self.assertEqual(self.field().coerce('only'), ['only'])

    def test_a_sequence_is_taken_string_by_string(self):
        self.assertEqual(self.field().coerce(['a', 'b']), ['a', 'b'])

    def test_it_checks_for_a_list_of_strings(self):
        self.assertTrue(self.field().check(['a']))
        self.assertFalse(self.field().check(['a', 1]))
        self.assertFalse(self.field().check('a'))

    def test_a_copy_is_a_list_of_its_own(self):
        given = ['a', 'b']
        copied = self.field().copyValue(given)
        self.assertEqual(copied, given)
        self.assertIsNot(copied, given)

    def test_a_number_is_refused_the_way_the_other_lists_refuse_one(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(42)
        self.assertIn('MFString', str(caught.exception))


class TestABool(unittest.TestCase):
    def field(self):
        return fieldtypes.SFBool(name='on')

    def test_true_is_written_as_the_word(self):
        self.assertEqual(self.field().vrmlstr(1), 'TRUE')

    def test_false_is_written_as_the_word(self):
        self.assertEqual(self.field().vrmlstr(0), 'FALSE')

    def test_it_checks_for_one_of_the_two_values(self):
        self.assertTrue(self.field().check(1))
        self.assertTrue(self.field().check(0))
        self.assertFalse(self.field().check(2))


class TestAnInteger(unittest.TestCase):
    def field(self):
        return fieldtypes.SFInt32(name='count')

    def test_text_is_read_as_a_number(self):
        self.assertEqual(self.field().coerce('42'), 42)

    def test_what_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce('not a number')
        self.assertIn('SFInt32', str(caught.exception))

    def test_it_checks_for_an_integer(self):
        self.assertTrue(self.field().check(1))
        self.assertFalse(self.field().check(1.5))


class TestAFloat(unittest.TestCase):
    def field(self):
        return fieldtypes.SFFloat(name='size')

    def test_text_is_read_as_a_number(self):
        self.assertAlmostEqual(self.field().coerce('2.5'), 2.5, places=6)

    def test_what_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce('not a number')
        self.assertIn('SFFloat', str(caught.exception))

    def test_it_checks_for_a_float(self):
        self.assertTrue(self.field().check(1.5))
        self.assertFalse(self.field().check(1))


class TestCopyingAnArrayValue(unittest.TestCase):
    """A copy of an array field is an array of its own, so that writing to
    the copy does not reach the original."""

    def copied(self, declared, value):
        given = declared.coerce(value)
        copied = declared.copyValue(given)
        return given, copied

    def test_a_float_list(self):
        given, copied = self.copied(fieldtypes.MFFloat(name='h'), [1.0, 2.0])
        copied[0] = 9.0
        self.assertAlmostEqual(given[0], 1.0, places=6)

    def test_an_integer_list(self):
        given, copied = self.copied(fieldtypes.MFInt32(name='i'), [1, 2])
        copied[0] = 9
        self.assertEqual(given[0], 1)

    def test_a_vector_list(self):
        given, copied = self.copied(fieldtypes.MFVec3f(name='p'),
                                    [[1, 2, 3], [4, 5, 6]])
        copied[0][0] = 9.0
        self.assertAlmostEqual(given[0][0], 1.0, places=5)

    def test_a_colour(self):
        given, copied = self.copied(fieldtypes.SFColor(name='c'), [1, 0, 0])
        copied[0] = 0.0
        self.assertAlmostEqual(given[0], 1.0, places=5)

    def test_a_bare_array(self):
        given, copied = self.copied(fieldtypes.SFArray(name='a'), [1.0, 2.0])
        copied[0] = 9.0
        self.assertAlmostEqual(given[0], 1.0, places=6)


class TestAVectorFromAScalar(unittest.TestCase):
    """One number fills the whole vector, which is how a uniform scale or a
    grey colour is written."""

    def test_a_vector_takes_the_number_in_every_place(self):
        got = fieldtypes.SFVec3f(name='scale').coerce(2.0)
        self.assertEqual(list(got), [2.0, 2.0, 2.0])

    def test_an_integer_does_as_well(self):
        got = fieldtypes.SFVec3f(name='scale').coerce(2)
        self.assertEqual(list(got), [2.0, 2.0, 2.0])

    def test_a_value_of_the_wrong_shape_says_both_shapes(self):
        with self.assertRaises(ValueError) as caught:
            fieldtypes.SFVec3f(name='scale').coerce(np.zeros((2, 2), 'd'))
        self.assertIn('shape', str(caught.exception))

    def test_something_it_cannot_read_at_all_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            fieldtypes.SFVec3f(name='scale').coerce(object())
        self.assertIn('SFVec3f', str(caught.exception))


class TestAMatrixDefault(unittest.TestCase):
    """A matrix field left alone is the identity, so that a node that
    declares one transforms nothing."""

    def test_a_three_by_three(self):
        got = fieldtypes.SFMatrix3f(name='matrix').defaultDefault()
        self.assertEqual(got.shape, (3, 3))
        self.assertEqual(list(got[0]), [1.0, 0.0, 0.0])

    def test_a_four_by_four(self):
        got = fieldtypes.SFMatrix4f(name='matrix').defaultDefault()
        self.assertEqual(got.shape, (4, 4))
        self.assertEqual(list(got[3]), [0.0, 0.0, 0.0, 1.0])


class TestABareArray(unittest.TestCase):
    """`SFArray` holds whatever numpy array it is given, which is how a
    shader uniform or a vertex buffer is carried."""

    def field(self):
        return fieldtypes.SFArray(name='data')

    def test_text_is_read_as_numbers(self):
        got = self.field().coerce('[1, 2, 3]')
        self.assertEqual(list(got), [1.0, 2.0, 3.0])

    def test_one_number_becomes_an_array_of_one(self):
        self.assertEqual(list(self.field().coerce(2.0)), [2.0])

    def test_a_lazy_sequence_is_drawn_out(self):
        self.assertEqual(list(self.field().coerce(range(3))), [0.0, 1.0, 2.0])

    def test_an_array_of_another_element_type_is_converted(self):
        got = self.field().coerce(np.array([1, 2], 'i'))
        self.assertEqual(list(got), [1.0, 2.0])

    def test_something_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(object())
        self.assertIn('SFArray', str(caught.exception))

    def test_it_is_written_as_the_array_reads(self):
        self.assertIn('1.', self.field().vrmlstr(self.field().coerce([1.0])))

    def test_it_checks_for_an_array_of_the_right_kind(self):
        declared = self.field()
        self.assertFalse(declared.check([1.0, 2.0]))


class TestWritingAListOfVectors(unittest.TestCase):
    """`MFVec3f` writes rows, and breaks them across lines once there are
    more than a line will hold."""

    def field(self):
        return fieldtypes.MFVec3f(name='point')

    def test_nothing_is_an_empty_pair_of_brackets(self):
        self.assertEqual(self.field().vrmlstr(self.field().coerce([])), '[ ]')

    def test_a_few_are_written_on_one_line(self):
        written = self.field().vrmlstr(self.field().coerce([[1, 2, 3]]))
        self.assertNotIn('\n', written)

    def test_many_are_broken_across_lines(self):
        value = self.field().coerce([[float(n)] * 3 for n in range(200)])
        self.assertIn('\n', self.field().vrmlstr(value))

    def test_it_checks_for_rows_of_the_right_width(self):
        declared = self.field()
        self.assertTrue(declared.check(declared.coerce([[1, 2, 3]])))
        self.assertFalse(declared.check(np.array([1.0, 2.0, 3.0], 'f')))
        self.assertFalse(declared.check([[1, 2, 3]]))


class TestAColourByName(unittest.TestCase):
    """A colour may be written as a CSS name or a hex triple, which is what
    a generated scene or a hand-written one is likely to hold."""

    def test_a_name_is_read(self):
        got = fieldtypes.SFColor(name='diffuseColor').coerce('red')
        self.assertEqual(list(got), [1.0, 0.0, 0.0])

    def test_a_hex_triple_is_read(self):
        got = fieldtypes.SFColor(name='diffuseColor').coerce('#00ff00')
        self.assertEqual(list(got), [0.0, 1.0, 0.0])

    def test_a_value_outside_the_range_is_brought_into_it(self):
        got = fieldtypes.SFColor(name='diffuseColor').coerce([2.0, -1.0, 0.5])
        self.assertEqual(list(got), [1.0, 0.0, 0.5])


class TestAListOfColoursByName(unittest.TestCase):
    """`MFColor` takes the two mixed: numbers in threes, and a name standing
    for a colour of its own."""

    def field(self):
        return fieldtypes.MFColor(name='color')

    def test_numbers_alone(self):
        got = self.field().coerce([1, 0, 0, 0, 1, 0])
        self.assertEqual(got.shape, (2, 3))

    def test_a_name_among_them(self):
        got = self.field().coerce([0.2, 0.3, 0.4, 'red'])
        self.assertEqual(got.shape, (2, 3))
        self.assertEqual(list(got[1]), [1.0, 0.0, 0.0])

    def test_names_alone(self):
        got = self.field().coerce(['red', 'blue'])
        self.assertEqual(list(got[0]), [1.0, 0.0, 0.0])
        self.assertEqual(list(got[1]), [0.0, 0.0, 1.0])

    def test_a_name_partway_through_a_colour_says_so(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce([0.2, 0.3, 'red'])
        self.assertIn('before string value', str(caught.exception))

    def test_numbers_left_over_at_the_end_say_so(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce([0.2, 0.3, 0.4, 'red', 0.5])
        self.assertIn('end of MFColor', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
