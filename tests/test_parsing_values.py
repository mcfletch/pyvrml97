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
        got = node_from(r'info [ "say \"no\"", "a\\b", "c\d" ]').info
        self.assertEqual(list(got), ['say "no"', 'a\\b', 'c\\d'])

    def test_an_empty_list_of_strings(self):
        self.assertEqual(len(node_from('info [ ]').info), 0)


class TestReadingBytes(unittest.TestCase):
    """A file is read from disk as bytes, and a VRML97 string field holds
    text, so the source may be either."""

    SOURCE = b'#VRML V2.0 utf8\nWorldInfo { title "a world" }\n'

    def test_a_bytes_source_is_read(self):
        self.assertEqual(read(self.SOURCE).children[0].title, 'a world')

    def test_text_outside_ascii_comes_back(self):
        source = '#VRML V2.0 utf8\nWorldInfo { title "café" }\n'
        self.assertEqual(read(source.encode('utf-8')).children[0].title,
                         'café')


class TestListsWithNothingInThem(unittest.TestCase):
    """Each list type has to read an empty pair of brackets, which is what
    a generated file writes for a field it has nothing for."""

    def test_a_list_of_integers(self):
        self.assertEqual(
            len(node_from('coordIndex [ ]', 'IndexedFaceSet').coordIndex), 0)

    def test_a_list_of_vectors(self):
        self.assertEqual(len(node_from('point [ ]', 'Coordinate').point), 0)

    def test_an_image(self):
        self.assertEqual(len(node_from('image [ ]', 'PixelTexture').image), 0)


class TestAFieldTypeAPrototypeDeclares(unittest.TestCase):
    """A PROTO may declare a field of any registered type, including ones
    no built-in node has."""

    def held(self, declaration, value):
        return read('#VRML V2.0 utf8\n'
                    'PROTO Held [ field %s value %s ] { }\n'
                    'Held { }\n' % (declaration, value)).children[0].value

    def test_an_unsigned_integer(self):
        self.assertEqual(self.held('SFUInt32', '42'), 42)

    def test_an_unsigned_integer_list(self):
        self.assertEqual(list(self.held('MFUInt32', '[ 1, 2, 3 ]')), [1, 2, 3])

    def test_a_time(self):
        self.assertAlmostEqual(self.held('SFTime', '2.5'), 2.5, places=5)

    def test_a_four_vector(self):
        self.assertEqual(list(self.held('SFVec4f', '1 2 3 4')),
                         [1.0, 2.0, 3.0, 4.0])

    def test_a_double_precision_vector(self):
        self.assertEqual(list(self.held('SFVec3d', '1 2 3')), [1.0, 2.0, 3.0])

    def test_a_list_of_four_vectors(self):
        self.assertEqual(self.held('MFVec4f', '[ 1 2 3 4, 5 6 7 8 ]').shape,
                         (2, 4))

    def test_a_list_of_double_precision_vectors(self):
        self.assertEqual(self.held('MFVec3d', '[ 1 2 3, 4 5 6 ]').shape,
                         (2, 3))

    def test_a_matrix(self):
        got = self.held('SFMatrix4f', '[ [1,0,0,0], [0,1,0,0], '
                                      '[0,0,1,0], [0,0,0,1] ]')
        self.assertEqual(got.shape, (4, 4))
        self.assertEqual(list(got[0]), [1.0, 0.0, 0.0, 0.0])

    def test_a_smaller_matrix(self):
        self.assertEqual(
            self.held('SFMatrix3f', '[ [1,0,0], [0,1,0], [0,0,1] ]').shape,
            (3, 3))

    def test_a_list_of_matrices(self):
        got = self.held('MFMatrix4f',
                        '[ [1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1],\n'
                        '  [2,0,0,0], [0,2,0,0], [0,0,2,0], [0,0,0,1] ]')
        self.assertEqual(got.shape, (2, 4, 4))

    def test_an_array_of_any_shape(self):
        self.assertEqual(self.held('SFArray32', '[ 1, 2, 3 ]').shape, (3,))

    def test_every_registered_type_can_be_declared(self):
        """A file may name any field type the library has, so each has to
        have a way of being read."""
        from vrml import field as fieldmodule
        from vrml.vrml97 import parseprocessor

        #: Node-valued types have their own path through the processor.
        by_hand = {'SFNode', 'MFNode', 'WeakSFNode', 'RootScenegraphNode'}
        missing = sorted(
            name for name in fieldmodule.baseFieldTypes
            if name not in by_hand
            and not hasattr(parseprocessor.ParseProcessor, name))
        self.assertEqual(missing, [])


class TestNamingAFieldTheNodeDoesNotHave(unittest.TestCase):
    """A file can name anything; what the node declares is what it has."""

    def test_it_says_which_field_and_which_node(self):
        with self.assertRaises(AttributeError) as caught:
            read('#VRML V2.0 utf8\nSphere { nosuchfield 1 }\n')
        self.assertIn('nosuchfield', str(caught.exception))
        self.assertIn('Sphere', str(caught.exception))


class TestAScriptInsideAPrototype(unittest.TestCase):
    """A Script declares its own interface, and inside a PROTO each part of
    it may be wired to the prototype's with IS."""

    SOURCE = ('#VRML V2.0 utf8\n'
              'PROTO Thing [\n'
              '  eventIn SFFloat set_x\n'
              '  field SFFloat r 1.0\n'
              ']\n'
              '{\n'
              '  Script {\n'
              '    eventIn SFFloat set_x IS set_x\n'
              '    eventOut SFFloat x_changed\n'
              '    field SFFloat r IS r\n'
              '    field SFFloat scale 2.0\n'
              '    url "javascript:function set_x(v){}"\n'
              '  }\n'
              '}\n'
              'Thing { r 3.0 }\n')

    def instance(self):
        return read(self.SOURCE).children[0]

    def test_the_prototype_is_declared(self):
        self.assertIn('Thing', read(self.SOURCE).protoTypes)

    def test_the_script_is_the_body(self):
        self.assertEqual(len(self.instance().scenegraph.children), 1)

    def test_a_field_the_script_declared_for_itself_keeps_its_value(self):
        script = self.instance().scenegraph.children[0]
        self.assertAlmostEqual(script.scale, 2.0, places=5)

    def test_a_field_wired_with_is_takes_the_instances_value(self):
        script = self.instance().scenegraph.children[0]
        self.assertAlmostEqual(script.r, 3.0, places=5)

    def test_the_url_is_kept(self):
        self.assertIn('javascript:',
                      list(self.instance().scenegraph.children[0].url)[0])


class TestReadingASliceOfTheSource(unittest.TestCase):
    """`as_str` is what turns a slice of the parse buffer into the text a
    string field holds, whichever of bytes and text the source was read
    as."""

    def as_str(self, value):
        from vrml.vrml97.parseprocessor import as_str

        return as_str(value)

    def test_text_comes_back_as_it_is(self):
        self.assertEqual(self.as_str('a world'), 'a world')

    def test_bytes_are_decoded(self):
        self.assertEqual(self.as_str(b'caf\xc3\xa9'), 'café')

    def test_anything_else_is_written_as_text(self):
        self.assertEqual(self.as_str(42), '42')


class TestWiringInsideAScript(unittest.TestCase):
    """A Script's braces hold ROUTEs and PROTOs as well as its own
    declarations."""

    SOURCE = ('#VRML V2.0 utf8\n'
              'DEF Clock TimeSensor { }\n'
              'DEF Mover Transform { }\n'
              'Script {\n'
              '  url "js:x"\n'
              '  ROUTE Clock.fraction_changed TO Mover.set_translation\n'
              '}\n')

    def test_the_route_is_read(self):
        self.assertTrue(read(self.SOURCE).routes)

    def test_it_names_both_ends(self):
        wired = read(self.SOURCE).routes[0]
        self.assertEqual(wired.sourceField, 'fraction_changed')


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
