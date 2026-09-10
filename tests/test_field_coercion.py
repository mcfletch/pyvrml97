"""Reading a field's value from whatever a caller wrote.

Every field type takes its value from a file, from a program, or from another
node's field -- so each `coerce` has to read text, a number, a sequence, and an
array of the wrong element type, and to refuse what is none of those by saying
which field it was and what it was given.

`tests/test_fieldtypes.py` covers the array types' string forms; this covers
the rest of each type's ways in, and the refusals.
"""

import unittest

import numpy as np

from vrml import fieldtypes


class TestAnIntegerList(unittest.TestCase):
    def field(self):
        return fieldtypes.MFInt32(name='indices')

    def test_text(self):
        self.assertEqual(list(self.field().coerce('1 2 3')), [1, 2, 3])

    def test_text_with_commas(self):
        self.assertEqual(list(self.field().coerce('1, 2, 3')), [1, 2, 3])

    def test_one_number_becomes_a_list_of_one(self):
        self.assertEqual(list(self.field().coerce(4)), [4])

    def test_a_sequence(self):
        self.assertEqual(list(self.field().coerce([1, 2, 3])), [1, 2, 3])

    def test_an_array_of_another_element_type_is_converted(self):
        given = np.array([1.0, 2.0, 3.0], 'd')
        got = self.field().coerce(given)
        self.assertEqual(list(got), [1, 2, 3])

    def test_a_two_dimensional_array_is_flattened(self):
        given = np.array([[1, 2], [3, 4]], 'i')
        self.assertEqual(list(self.field().coerce(given)), [1, 2, 3, 4])

    def test_nothing_is_an_empty_array(self):
        self.assertEqual(len(self.field().coerce(None)), 0)

    def test_what_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(object())
        self.assertIn('MFInt32', str(caught.exception))


class TestAFloatList(unittest.TestCase):
    def field(self):
        return fieldtypes.MFFloat(name='heights')

    def test_text(self):
        self.assertEqual(list(self.field().coerce('1 2.5 3')), [1.0, 2.5, 3.0])

    def test_one_number_becomes_a_list_of_one(self):
        self.assertEqual(list(self.field().coerce(2.5)), [2.5])

    def test_a_nested_sequence_is_flattened(self):
        self.assertEqual(list(self.field().coerce([[1, 2], [3, 4]])),
                         [1.0, 2.0, 3.0, 4.0])

    def test_an_array_of_another_element_type_is_converted(self):
        got = self.field().coerce(np.array([1, 2, 3], 'i'))
        self.assertEqual(list(got), [1.0, 2.0, 3.0])

    def test_nothing_is_an_empty_array(self):
        self.assertEqual(len(self.field().coerce(None)), 0)

    def test_what_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(object())
        self.assertIn('MFFloat', str(caught.exception))


class TestAVector(unittest.TestCase):
    """A vector field has a shape, and a value has to fit it."""

    def field(self):
        return fieldtypes.SFVec3f(name='translation')

    def test_text(self):
        self.assertEqual(list(self.field().coerce('1 2 3')), [1.0, 2.0, 3.0])

    def test_a_sequence(self):
        self.assertEqual(list(self.field().coerce([1, 2, 3])), [1.0, 2.0, 3.0])

    def test_an_array_of_another_element_type_is_converted(self):
        got = self.field().coerce(np.array([1, 2, 3], 'i'))
        self.assertEqual(list(got), [1.0, 2.0, 3.0])

    def test_the_wrong_length_says_both_shapes(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce([1.0, 2.0])
        self.assertIn('shape', str(caught.exception))

    def test_what_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(object())
        self.assertIn('SFVec3f', str(caught.exception))

    def test_its_default_is_the_zero_vector(self):
        self.assertEqual(list(self.field().defaultDefault()), [0.0, 0.0, 0.0])


class TestAVectorList(unittest.TestCase):
    """`MFVec3f` is rows of three, and reshapes whatever it is given."""

    def field(self):
        return fieldtypes.MFVec3f(name='point')

    def test_a_flat_sequence_is_taken_in_rows(self):
        got = self.field().coerce([1, 2, 3, 4, 5, 6])
        self.assertEqual(got.shape, (2, 3))

    def test_rows_are_kept_as_rows(self):
        got = self.field().coerce([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(got.shape, (2, 3))

    def test_an_array_of_another_element_type_is_converted(self):
        got = self.field().coerce(np.array([[1, 2, 3]], 'i'))
        self.assertEqual(got.shape, (1, 3))
        self.assertEqual(list(got[0]), [1.0, 2.0, 3.0])

    def test_what_it_cannot_read_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(object())
        self.assertIn('MFVec3f', str(caught.exception))


class TestAColour(unittest.TestCase):
    def test_it_reads_three_numbers(self):
        field = fieldtypes.SFColor(name='diffuseColor')
        self.assertEqual(list(field.coerce([1, 0, 0])), [1.0, 0.0, 0.0])

    def test_a_list_of_them_is_rows_of_three(self):
        field = fieldtypes.MFColor(name='color')
        self.assertEqual(field.coerce([1, 0, 0, 0, 1, 0]).shape, (2, 3))


class TestARotation(unittest.TestCase):
    def test_it_reads_four_numbers(self):
        field = fieldtypes.SFRotation(name='rotation')
        self.assertEqual(list(field.coerce([0, 1, 0, 1.5])),
                         [0.0, 1.0, 0.0, 1.5])

    def test_its_default_turns_nothing(self):
        field = fieldtypes.SFRotation(name='rotation')
        self.assertEqual(len(field.defaultDefault()), 4)


class TestAMatrix(unittest.TestCase):
    def test_it_reads_sixteen_numbers_as_four_rows(self):
        """A flat list of the right length, which is how a file writes one."""
        field = fieldtypes.SFMatrix4f(name='matrix')
        got = field.coerce(list(range(16)))
        self.assertEqual(got.shape, (4, 4))
        self.assertEqual(list(got[0]), [0.0, 1.0, 2.0, 3.0])

    def test_it_reads_four_rows_of_four(self):
        field = fieldtypes.SFMatrix4f(name='matrix')
        got = field.coerce([[0, 1, 2, 3]] * 4)
        self.assertEqual(got.shape, (4, 4))

    def test_it_reads_an_array_of_another_element_type(self):
        field = fieldtypes.SFMatrix4f(name='matrix')
        got = field.coerce(np.arange(16, dtype='i').reshape(4, 4))
        self.assertEqual(got.shape, (4, 4))

    def test_its_default_is_the_identity(self):
        field = fieldtypes.SFMatrix4f(name='matrix')
        got = field.defaultDefault()
        self.assertEqual(got.shape, (4, 4))


if __name__ == '__main__':
    unittest.main()
