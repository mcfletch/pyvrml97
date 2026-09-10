"""Reading each kind of value out of a VRML97 file.

The grammar hands the processor a parse tree and the source text, and the
processor turns each production into the value a field will hold. Every field
type has a shape in the file -- a number, a bracketed run of them, a quoted
string with escapes in it, a nested vector -- and this is each of those read
back as what it says.

`tests/test_parseprocessor.py` covers the file-level constructs the processor
builds; this covers the values inside them.
"""

import unittest

from vrml.vrml97.parser import buildParser

PARSER = buildParser()


def read(text):
    """The scene a VRML97 source builds, insisting the whole of it was read."""
    success, results, consumed = PARSER.parse(text)
    if not success or consumed != len(text):
        raise AssertionError('the grammar stopped at %s of %s:\n%s'
                             % (consumed, len(text), text))
    return results[1]


def node_from(field_text, node_type='WorldInfo'):
    """The one node in a file declaring `field_text`."""
    return read('#VRML V2.0 utf8\n%s { %s }\n' % (node_type, field_text)).children[0]


class TestNumbers(unittest.TestCase):
    def test_a_float(self):
        self.assertAlmostEqual(
            node_from('radius 2.5', 'Sphere').radius, 2.5, places=5)

    def test_a_negative_float(self):
        self.assertAlmostEqual(
            node_from('radius -2.5', 'Sphere').radius, -2.5, places=5)

    def test_exponential_notation(self):
        self.assertAlmostEqual(
            node_from('radius 2.5e2', 'Sphere').radius, 250.0, places=3)

    def test_an_integer_field(self):
        self.assertEqual(
            node_from('xDimension 4', 'ElevationGrid').xDimension, 4)

    def test_a_hexadecimal_integer(self):
        """VRML97 writes an SFImage's pixels this way."""
        got = node_from('xDimension 0x10', 'ElevationGrid').xDimension
        self.assertEqual(got, 16)

    def test_a_boolean(self):
        self.assertFalse(node_from('collide FALSE', 'Collision').collide)
        self.assertTrue(node_from('collide TRUE', 'Collision').collide)


class TestVectors(unittest.TestCase):
    def test_a_three_vector(self):
        got = node_from('translation 1 2 3', 'Transform').translation
        self.assertEqual(list(got), [1.0, 2.0, 3.0])

    def test_a_two_vector(self):
        got = node_from('scale 1 2', 'TextureTransform').scale
        self.assertEqual(list(got), [1.0, 2.0])

    def test_a_rotation(self):
        got = node_from('rotation 0 1 0 1.5', 'Transform').rotation
        self.assertEqual(list(got), [0.0, 1.0, 0.0, 1.5])

    def test_a_colour(self):
        got = node_from('diffuseColor 1 0 0', 'Material').diffuseColor
        self.assertEqual(list(got), [1.0, 0.0, 0.0])


class TestListsOfNumbers(unittest.TestCase):
    def test_a_list_of_floats(self):
        got = node_from('height [ 1, 2, 3 ]', 'ElevationGrid').height
        self.assertEqual(list(got), [1.0, 2.0, 3.0])

    def test_an_empty_list(self):
        self.assertEqual(len(node_from('height [ ]', 'ElevationGrid').height),
                         0)

    def test_a_list_of_integers(self):
        got = node_from('coordIndex [ 0, 1, 2, -1 ]',
                        'IndexedFaceSet').coordIndex
        self.assertEqual(list(got), [0, 1, 2, -1])

    def test_a_list_of_hexadecimal_integers(self):
        got = node_from('coordIndex [ 0x1, 0x10 ]',
                        'IndexedFaceSet').coordIndex
        self.assertEqual(list(got), [1, 16])

    def test_a_list_of_vectors(self):
        got = node_from('point [ 1 2 3, 4 5 6 ]', 'Coordinate').point
        self.assertEqual(got.shape, (2, 3))
        self.assertEqual(list(got[1]), [4.0, 5.0, 6.0])

    def test_a_list_of_colours(self):
        got = node_from('color [ 1 0 0, 0 1 0 ]', 'Color').color
        self.assertEqual(got.shape, (2, 3))


class TestNestedVectors(unittest.TestCase):
    """A field that takes an array of any shape is written as brackets
    inside brackets, which is what a shader's uniform value looks like."""

    def scene(self, value):
        return read('#VRML V2.0 utf8\n'
                    'PROTO Held [ field SFArray value %s ] { }\n'
                    'Held { }\n' % (value,))

    def test_a_flat_run(self):
        got = self.scene('[ 1, 2, 3 ]').children[0].value
        self.assertEqual(list(got), [1.0, 2.0, 3.0])

    def test_rows_inside_it(self):
        got = self.scene('[ [1, 2], [3, 4] ]').children[0].value
        self.assertEqual(got.shape, (2, 2))
        self.assertEqual(list(got[1]), [3.0, 4.0])

    def test_nothing_at_all(self):
        self.assertEqual(len(self.scene('[ ]').children[0].value), 0)


class TestStrings(unittest.TestCase):
    def test_a_plain_string(self):
        self.assertEqual(node_from('title "a world"').title, 'a world')

    def test_an_escaped_quote(self):
        self.assertEqual(node_from(r'title "say \"no\""').title, 'say "no"')

    def test_an_escaped_backslash(self):
        self.assertEqual(node_from(r'title "a\\b"').title, 'a\\b')

    def test_a_lone_backslash(self):
        self.assertEqual(node_from(r'title "a\b"').title, 'a\\b')

    def test_an_empty_string(self):
        self.assertEqual(node_from('title ""').title, '')

    def test_a_list_of_strings(self):
        got = node_from('info [ "one", "two" ]').info
        self.assertEqual(list(got), ['one', 'two'])

    def test_escapes_inside_a_list(self):
        got = node_from(r'info [ "say \"no\"", "a\\b" ]').info
        self.assertEqual(list(got), ['say "no"', 'a\\b'])

    def test_an_empty_list_of_strings(self):
        self.assertEqual(len(node_from('info [ ]').info), 0)


class TestCommentsAndWhitespace(unittest.TestCase):
    def test_a_comment_is_not_part_of_a_value(self):
        scene = read('#VRML V2.0 utf8\n'
                     'Sphere {  # how big\n'
                     '  radius 2.0\n'
                     '}\n')
        self.assertAlmostEqual(scene.children[0].radius, 2.0, places=5)

    def test_a_file_may_end_with_a_comment(self):
        scene = read('#VRML V2.0 utf8\nSphere { }\n# the end\n')
        self.assertEqual(len(scene.children), 1)

    def test_a_file_may_be_a_header_alone(self):
        self.assertEqual(len(read('#VRML V2.0 utf8\n').children), 0)


if __name__ == '__main__':
    unittest.main()
