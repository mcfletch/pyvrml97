"""Field values as the X3D XML encoding writes them (ISO/IEC 19776-1).

An attribute value is text: numbers separated by whitespace or commas,
booleans as `true`/`false`, an MFString as double-quoted strings. `decode`
reads one into the value a field of that type holds, and `encode` writes a
field's value back as text `decode` reads to the same value.
"""

import math
import unittest

import numpy as np

from vrml import field
from vrml import fieldtypes  # noqa: F401 registers the types newField looks up
from vrml.x3d import codecs


def held(type_name, text):
    """The value a field of `type_name` holds after reading `text`."""
    declared = field.newField('value', type_name)
    return declared.coerce(codecs.decode(type_name, text))


class TestNumbers(unittest.TestCase):
    def test_a_float_is_read(self):
        self.assertEqual(codecs.decode('SFFloat', ' 1.5 '), 1.5)

    def test_an_integer_may_be_written_in_hex(self):
        self.assertEqual(codecs.decode('SFInt32', '0x1F'), 31)

    def test_an_integer_may_carry_an_exponent(self):
        self.assertEqual(codecs.decode('SFInt32', '1e3'), 1000)

    def test_a_double_keeps_its_digits(self):
        self.assertEqual(codecs.decode('SFDouble', '6378137.0000001'),
                         6378137.0000001)

    def test_commas_are_whitespace(self):
        self.assertEqual(held('MFFloat', '1,2, 3 ,4').tolist(), [1, 2, 3, 4])

    def test_a_vector_list_is_read_into_rows(self):
        value = held('MFVec3f', '0 0 0, 1 1 1')
        self.assertEqual(value.shape, (2, 3))
        self.assertEqual(value.dtype, np.float32)

    def test_a_double_vector_list_is_float64(self):
        self.assertEqual(held('MFVec3d', '1 2 3').dtype, np.float64)

    def test_an_empty_list_is_empty(self):
        self.assertEqual(len(held('MFInt32', '')), 0)

    def test_a_word_where_a_number_belongs_is_refused(self):
        with self.assertRaises(ValueError):
            codecs.decode('SFFloat', 'one')

    def test_a_vector_of_the_wrong_length_is_refused_by_the_field(self):
        with self.assertRaises(ValueError):
            held('SFVec3f', '1 2')

    def test_an_unknown_type_is_refused(self):
        with self.assertRaises(KeyError):
            codecs.decode('SFNoSuchThing', '1')


class TestBooleans(unittest.TestCase):
    def test_the_xml_words_are_read(self):
        self.assertIs(codecs.decode('SFBool', 'true'), True)
        self.assertIs(codecs.decode('SFBool', 'false'), False)

    def test_the_vrml_spelling_is_read_too(self):
        self.assertIs(codecs.decode('SFBool', 'TRUE'), True)

    def test_anything_else_is_refused(self):
        with self.assertRaises(ValueError):
            codecs.decode('SFBool', 'yes')

    def test_a_list_of_them(self):
        self.assertEqual(held('MFBool', 'true false, true').tolist(),
                         [True, False, True])


class TestStrings(unittest.TestCase):
    def test_a_single_string_is_the_attribute_text(self):
        self.assertEqual(codecs.decode('SFString', ' a "quoted" word '),
                         ' a "quoted" word ')

    def test_a_list_is_written_quoted(self):
        self.assertEqual(codecs.decode('MFString', '"EXAMINE" "ANY"'),
                         ['EXAMINE', 'ANY'])

    def test_quotes_and_backslashes_inside_are_escaped(self):
        self.assertEqual(codecs.decode('MFString', r'"say \"hi\"" "a\\b"'),
                         ['say "hi"', 'a\\b'])

    def test_commas_may_separate_them(self):
        self.assertEqual(codecs.decode('MFString', '"a", "b"'), ['a', 'b'])

    def test_an_unquoted_value_is_one_string(self):
        self.assertEqual(codecs.decode('MFString', 'images/brick.png'),
                         ['images/brick.png'])

    def test_an_unclosed_quote_is_refused(self):
        with self.assertRaises(ValueError):
            codecs.decode('MFString', '"a" "b')

    def test_an_empty_list(self):
        self.assertEqual(codecs.decode('MFString', ''), [])


class TestImages(unittest.TestCase):
    def test_pixels_may_be_hex(self):
        self.assertEqual(held('SFImage', '1 1 3 0xFF8800').tolist(),
                         [1, 1, 3, 0xFF8800])

    def test_a_list_of_images(self):
        images = held('MFImage', '1 1 1 0x00 1 1 1 0xFF')
        self.assertEqual([image.tolist() for image in images],
                         [[1, 1, 1, 0], [1, 1, 1, 255]])


class TestNodes(unittest.TestCase):
    def test_null_is_the_only_node_text(self):
        self.assertIsNone(codecs.decode('SFNode', 'NULL'))

    def test_other_node_text_is_refused(self):
        with self.assertRaises(ValueError):
            codecs.decode('SFNode', 'Box')


class TestWriting(unittest.TestCase):
    """`encode` writes what `decode` reads back to the same value."""

    CASES = (
        ('SFBool', True), ('SFBool', False),
        ('SFInt32', -7), ('SFFloat', 0.1), ('SFDouble', 6378137.0000001),
        ('SFTime', -1.0), ('SFString', 'a "b" c'),
        ('SFVec3f', [0.1, 0.2, 0.3]), ('SFRotation', [0, 1, 0, 3.14159]),
        ('SFColor', [1, 0.5, 0]), ('SFColorRGBA', [1, 0.5, 0, 0.25]),
        ('SFMatrix3f', np.identity(3)), ('SFVec3d', [1e-12, 2, 3]),
        ('MFFloat', [1.5, 2.5]), ('MFInt32', [0, -1, 2]),
        ('MFString', ['EXAMINE', 'say "hi"', 'a\\b', '']),
        ('MFVec2f', [[0, 1], [2, 3]]), ('MFBool', [True, False]),
        ('MFColorRGBA', [[1, 0, 0, 1]]), ('MFDouble', [1.0000000001]),
        ('SFImage', [2, 1, 1, 0, 255]),
        ('MFImage', [[1, 1, 1, 0], [1, 1, 1, 255]]),
    )

    def test_each_value_reads_back_equal(self):
        for type_name, value in self.CASES:
            declared = field.newField('value', type_name)
            original = declared.coerce(value)
            text = codecs.encode(type_name, original)
            again = declared.coerce(codecs.decode(type_name, text))
            with self.subTest(type_name=type_name, text=text):
                if type_name == 'MFImage':
                    self.assertEqual([i.tolist() for i in again],
                                     [i.tolist() for i in original])
                else:
                    np.testing.assert_array_equal(again, original)

    def test_booleans_are_written_in_lower_case(self):
        self.assertEqual(codecs.encode('MFBool', [True, False]), 'true false')

    def test_a_float32_is_written_in_its_shortest_form(self):
        declared = field.newField('value', 'SFVec3f')
        self.assertEqual(codecs.encode('SFVec3f', declared.coerce([0.1, 1, -2.5])),
                         '0.1 1 -2.5')

    def test_a_small_number_is_written_without_an_exponent(self):
        # The schema's patterns for colours and other unit ranges allow an
        # exponent only on a mantissa in [0, 1].
        declared = field.newField('value', 'SFColor')
        self.assertEqual(codecs.encode('SFColor', declared.coerce([7.89723e-05, 0, 0])),
                         '0.0000789723 0 0')

    def test_a_large_number_is_written_with_an_exponent(self):
        self.assertEqual(codecs.encode('SFDouble', 1e20), '1e+20')

    def test_a_vector_list_separates_its_rows_with_commas(self):
        declared = field.newField('value', 'MFVec2f')
        self.assertEqual(codecs.encode('MFVec2f', declared.coerce([[0, 1], [2, 3]])),
                         '0 1, 2 3')

    def test_a_non_finite_number_is_refused(self):
        with self.assertRaises(ValueError):
            codecs.encode('SFFloat', math.nan)

    def test_null_is_written_null(self):
        self.assertEqual(codecs.encode('SFNode', None), 'NULL')


if __name__ == '__main__':
    unittest.main()
