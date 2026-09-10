"""Writing a field value back out as VRML97.

Every field type answers `vrmlstr`, and what it writes has to read back as the
same value -- which is what `tests/test_tostring.py` drives whole files
through. What is here is each type on its own, and the shapes the file format
has for one: a float written without its leading or trailing zero, a long list
broken across lines against a lineariser's indent, a string with a quote in it.
"""

import unittest

from vrml import fieldtypes
from vrml.vrml97 import linearise


class Indented:
    """A lineariser at a chosen depth, which is all `vrmlstr` reads of one."""

    def __init__(self, **overrides):
        self.linvalues = dict(linearise.defaults)
        self.linvalues.update(overrides)


class TestAFloat(unittest.TestCase):
    """VRML97 writes a float as briefly as it can be read back."""

    def wrote(self, value):
        return fieldtypes.SFFloat_vrmlstr(value)

    def test_zero_is_a_single_digit(self):
        self.assertEqual(self.wrote(0.0), '0')

    def test_a_leading_zero_is_dropped(self):
        self.assertEqual(self.wrote(0.5), '.5')

    def test_a_negative_keeps_its_sign_and_drops_the_zero(self):
        self.assertEqual(self.wrote(-0.5), '-.5')

    def test_a_trailing_zero_is_dropped(self):
        self.assertEqual(self.wrote(2.0), '2')

    def test_anything_else_is_written_as_it_reads(self):
        self.assertEqual(self.wrote(1.25), '1.25')


class TestAString(unittest.TestCase):
    def test_it_is_quoted(self):
        self.assertEqual(fieldtypes.SFString_vrmlstr('plain'), '"plain"')

    def test_a_quote_inside_is_escaped(self):
        self.assertEqual(fieldtypes.SFString_vrmlstr('say "no"'),
                         '"say \\"no\\""')

    def test_a_backslash_is_escaped(self):
        self.assertEqual(fieldtypes.SFString_vrmlstr('a\\b'), '"a\\\\b"')


class TestAListOfStrings(unittest.TestCase):
    """`MFString` writes one string, a bracketed row, or a broken-up block."""

    def wrote(self, value, lineariser=None):
        return fieldtypes.MFString_vrmlstr(value, lineariser)

    def test_nothing_is_an_empty_pair_of_brackets(self):
        self.assertEqual(self.wrote([]), '[ ]')

    def test_one_string_stands_on_its_own(self):
        self.assertEqual(self.wrote(['one']), '"one"')

    def test_a_few_are_bracketed_on_one_line(self):
        written = self.wrote(['one', 'two'])
        self.assertTrue(written.startswith('[ '), written)
        self.assertIn('"one"', written)
        self.assertIn('"two"', written)

    def test_a_long_set_is_broken_across_lines(self):
        """Over sixty characters of text, which is where one line stops
        being readable."""
        written = self.wrote(['word ' * 8] * 3)
        self.assertIn('\n', written)
        self.assertTrue(written.startswith('['), written[:20])

    def test_one_long_string_is_not_bracketed(self):
        """A single value needs no brackets however long it is."""
        written = self.wrote(['word ' * 20])
        self.assertFalse(written.startswith('['), written[:20])

    def test_a_lineariser_decides_the_indent(self):
        written = self.wrote(['word ' * 8] * 3, Indented(curindent='    '))
        self.assertIn('\n    ', written)


class TestAnInteger(unittest.TestCase):
    def field(self):
        return fieldtypes.SFInt32(name='count')

    def test_it_is_written_as_digits(self):
        self.assertEqual(self.field().vrmlstr(42), '42')

    def test_a_negative_keeps_its_sign(self):
        self.assertEqual(self.field().vrmlstr(-42), '-42')

    def test_a_number_too_long_to_convert_is_written_with_a_note(self):
        """VRML97's int32 has a range and Python's has none, so a value past
        it is written as it stands and said to be out of range rather than
        silently truncated."""

        class TooLong:
            def __int__(self):
                raise OverflowError('past int32')

            def __str__(self):
                return '99999999999999999999L'

        written = self.field().vrmlstr(TooLong())
        self.assertTrue(written.startswith('99999999999999999999'), written)
        self.assertIn('Overly long', written)
        self.assertNotIn('L', written.split('#')[0])


class TestAnUnsignedInteger(unittest.TestCase):
    def field(self):
        return fieldtypes.SFUInt32(name='count')

    def test_it_reads_a_number(self):
        self.assertEqual(self.field().coerce('42'), 42)

    def test_it_says_which_field_refused_a_value(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce('not a number')
        self.assertIn('SFUInt32', str(caught.exception))

    def test_it_checks_for_an_integer(self):
        self.assertTrue(self.field().check(1))
        self.assertFalse(self.field().check(1.5))

    def test_it_is_written_as_digits(self):
        self.assertEqual(self.field().vrmlstr(42), '42')


class TestABool(unittest.TestCase):
    """VRML97 spells these TRUE and FALSE, and a file may give either."""

    def field(self):
        return fieldtypes.SFBool(name='on')

    def test_the_word_true(self):
        self.assertEqual(self.field().coerce('TRUE'), 1)

    def test_the_word_false(self):
        self.assertEqual(self.field().coerce('FALSE'), 0)

    def test_either_case(self):
        self.assertEqual(self.field().coerce('true'), 1)
        self.assertEqual(self.field().coerce('false'), 0)

    def test_a_number_written_as_text(self):
        self.assertEqual(self.field().coerce('1'), 1)
        self.assertEqual(self.field().coerce('0'), 0)

    def test_anything_with_a_truth_value(self):
        self.assertEqual(self.field().coerce([1]), 1)
        self.assertEqual(self.field().coerce([]), 0)


class TestASetOfNumbers(unittest.TestCase):
    """`MFSimple` writes a run of numbers, wrapping where a line grows long."""

    def wrote(self, value, lineariser=None):
        return fieldtypes.MFSimple_vrmlstr(value, lineariser)

    def test_a_few_are_written_on_one_line(self):
        written = self.wrote([1, 2, 3])
        self.assertNotIn('\n', written.strip())
        for number in ('1', '2', '3'):
            self.assertIn(number, written)

    def test_many_are_broken_up(self):
        written = self.wrote(list(range(200)))
        self.assertIn('\n', written)

    def test_nothing_is_written_as_nothing(self):
        self.assertIn('[', self.wrote([]))


if __name__ == '__main__':
    unittest.main()
