"""The VRML200x grammar, which differs from VRML97 mostly in its header.

VRML97 opens with one comment line. This one opens with `#X3D <version> utf8`,
a mandatory `PROFILE`, and any number of `COMPONENT` and `META` statements --
which is what the file that follows is read against. The body is a near-copy of
the VRML97 grammar and the parser hands what it reads to the same
`ParseProcessor`, so the nodes come back as the same objects.
"""

import unittest

from vrml.vrml200x import parser
from vrml.vrml97.scenegraph import SceneGraph


HEADER = '#X3D 3.0 utf8\nPROFILE Immersive\n'

SCENE = HEADER + """Transform {
    translation 1 2 3
    children [
        Shape {
            geometry Box { size 2 2 2 }
        }
    ]
}
"""


class TestBuildingTheParser(unittest.TestCase):
    def test_the_grammar_compiles(self):
        self.assertIsNotNone(parser.buildParser())

    def test_it_builds_a_parse_processor(self):
        """The same one VRML97 uses: the two share their node vocabulary."""
        from vrml.vrml97 import parseprocessor
        built = parser.buildParser().buildProcessor()
        self.assertIsInstance(built, parseprocessor.ParseProcessor)

    def test_a_second_parser_is_a_separate_object(self):
        self.assertIsNot(parser.buildParser(), parser.buildParser())

    def test_a_grammar_can_be_passed_in(self):
        """The default is the module's own; a caller may hand over another."""
        from vrml.vrml200x.parser import grammar
        self.assertIsNotNone(parser.buildParser(grammar))


class TestTheHeader(unittest.TestCase):
    """Each form the grammar names, and one it must refuse."""

    def setUp(self):
        self.parser = parser.buildParser()

    def accepts(self, text):
        success, _results, consumed = self.parser.parse(text)
        return bool(success) and consumed == len(text)

    def test_the_encodings_own_header(self):
        self.assertTrue(self.accepts('#X3D 3.0 utf8\nPROFILE Immersive\n'))

    def test_a_version_written_with_its_v(self):
        self.assertTrue(self.accepts('#X3D V3.0 utf8\nPROFILE Immersive\n'))

    def test_a_plain_comment_line_in_place_of_it(self):
        self.assertTrue(self.accepts('#anything at all\nPROFILE Immersive\n'))

    def test_a_component_statement(self):
        self.assertTrue(self.accepts(HEADER + 'COMPONENT Core : 1\n'))

    def test_several_component_statements(self):
        self.assertTrue(self.accepts(
            HEADER + 'COMPONENT Core : 1\nCOMPONENT Grouping : 2\n'))

    def test_a_meta_statement(self):
        self.assertTrue(self.accepts(HEADER + 'META "author" "someone"\n'))

    def test_the_profile_is_required(self):
        """It is what says which of the encoding's nodes the file may use."""
        self.assertFalse(self.accepts('#X3D 3.0 utf8\n'))


class TestParsingAScene(unittest.TestCase):
    def setUp(self):
        self.parser = parser.buildParser()

    def parse(self, text):
        success, results, consumed = self.parser.parse(text)
        self.assertTrue(success, 'the grammar did not accept the source')
        self.assertEqual(consumed, len(text), 'only part of the source was read')
        scene = results[1]
        self.assertIsInstance(scene, SceneGraph)
        return scene

    def test_it_reads_a_scene(self):
        self.assertTrue(self.parse(SCENE).children)

    def test_a_field_value_comes_back_coerced(self):
        transform = self.parse(SCENE).children[0]
        self.assertEqual(list(transform.translation), [1.0, 2.0, 3.0])

    def test_a_nested_node_is_reached_through_its_field(self):
        shape = self.parse(SCENE).children[0].children[0]
        self.assertEqual(list(shape.geometry.size), [2.0, 2.0, 2.0])

    def test_a_comment_inside_the_scene_is_skipped(self):
        scene = self.parse(
            HEADER + '# a comment on its own line\nTransform { translation 0 1 0 }\n')
        self.assertEqual(list(scene.children[0].translation), [0.0, 1.0, 0.0])

    def test_a_header_with_no_scene_reads_as_no_children(self):
        self.assertEqual(list(self.parse(HEADER).children), [])

    def test_a_def_name_is_recorded(self):
        scene = self.parse(HEADER + 'DEF Root Transform { translation 0 0 1 }\n')
        self.assertIn('Root', scene.defNames)


if __name__ == '__main__':
    unittest.main()
