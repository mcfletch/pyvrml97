"""Naming a colour, the way a stylesheet does.

A VRML97 file writes a colour as three numbers, and an author writing one by
hand would rather say `crimson` or `#DC143C`.  `stringToColor` reads both.
"""

import unittest

from vrml import arrays, csscolors


class TestANamedColour(unittest.TestCase):
    def test_every_name_reads_back_as_its_colour(self):
        for name, value in csscolors.cssColors.items():
            self.assertEqual(csscolors.stringToColor(name), value, name)

    def test_the_name_is_read_whatever_its_case(self):
        self.assertEqual(csscolors.stringToColor('CRIMSON'),
                         csscolors.cssColors['crimson'])

    def test_black_is_the_origin(self):
        self.assertEqual(csscolors.stringToColor('black'), (0.0, 0.0, 0.0))


class TestAHexColour(unittest.TestCase):
    def test_every_named_colour_reads_back_through_its_hex_form(self):
        """The two spellings have to agree to a byte, which is all the hex
        form carries."""
        for name, value in csscolors.cssColors.items():
            written = '#%02x%02x%02x' % tuple(
                csscolors.toInt(channel) for channel in value)
            self.assertTrue(
                arrays.allclose(csscolors.stringToColor(written), value, 0.001),
                '%s: %r wrote %s and read back %r'
                % (name, value, written, csscolors.stringToColor(written)))

    def test_white_is_every_channel_full(self):
        self.assertEqual(csscolors.stringToColor('#ffffff'), (1.0, 1.0, 1.0))

    def test_the_channels_are_red_green_blue_in_that_order(self):
        self.assertEqual(csscolors.stringToColor('#ff0000'), (1.0, 0.0, 0.0))
        self.assertEqual(csscolors.stringToColor('#00ff00'), (0.0, 1.0, 0.0))
        self.assertEqual(csscolors.stringToColor('#0000ff'), (0.0, 0.0, 1.0))


class TestWhatItRefuses(unittest.TestCase):
    def test_a_name_nobody_has_says_so(self):
        with self.assertRaises(ValueError) as caught:
            csscolors.stringToColor('mauve-ish')
        self.assertIn('mauve-ish', str(caught.exception))

    def test_the_message_says_what_it_would_have_taken(self):
        with self.assertRaises(ValueError) as caught:
            csscolors.stringToColor('')
        self.assertIn('#FFFFFF', str(caught.exception))


class TestTheTwoConversions(unittest.TestCase):
    def test_a_byte_and_a_fraction_are_the_same_number(self):
        for byte in (0, 1, 127, 128, 254, 255):
            self.assertEqual(csscolors.toInt(csscolors.toFloat(byte)), byte)

    def test_a_shift_picks_the_channel_out_of_one_number(self):
        packed = 0x123456
        self.assertEqual(csscolors.toInt(csscolors.toFloat(packed, 16)), 0x12)
        self.assertEqual(csscolors.toInt(csscolors.toFloat(packed, 8)), 0x34)
        self.assertEqual(csscolors.toInt(csscolors.toFloat(packed, 0)), 0x56)


if __name__ == '__main__':
    unittest.main()
