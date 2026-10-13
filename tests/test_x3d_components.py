"""Node types an application adds to the X3D vocabulary, in a component of its own."""

import unittest

from vrml import field, x3d
from vrml.x3d import components, nodes, validate


class Marker(nodes.X3DChildNode):
    """A node of an application's own"""

    PROTO = 'ExampleMarker'
    COMPONENT = ('Example', 2)
    SINCE = '3.3'
    CONTAINER_FIELD = 'children'
    size = field.newField('size', 'SFFloat', 1, 1.0)
    label = field.newField('label', 'SFString', 0, '')


DOCUMENT = ('#X3D V4.0 utf8\nPROFILE Interchange\nCOMPONENT Example:2\n'
            'Group { children [ DEF M ExampleMarker { size 3 label "a" } ] }\n')


def said(scene):
    return [str(item.message) for item in scene.problems if item.severity != 'info']


class TestARegisteredComponent(unittest.TestCase):
    def setUp(self):
        components.register(Marker)
        self.addCleanup(components.unregister, Marker)

    def test_a_document_names_its_node(self):
        scene = x3d.loads(DOCUMENT)
        self.assertEqual(said(scene), [])
        found = scene.getDEF('M')
        self.assertIs(type(found), Marker)
        self.assertEqual(found.size, 3.0)

    def test_it_is_written_with_its_component_statement(self):
        scene = x3d.loads(DOCUMENT.replace('COMPONENT Example:2\n', ''))
        text = x3d.dumps(scene, encoding='classic')
        self.assertIn('COMPONENT Example:2', text)
        self.assertIn('ExampleMarker', text)
        self.assertNotIn('MetadataSet', text)

    def test_each_encoding_reads_back_as_itself(self):
        scene = x3d.loads(DOCUMENT)
        for encoding in ('classic', 'xml', 'json'):
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertEqual(said(again), [])
                found = again.getDEF('M')
                self.assertIs(type(found), Marker)
                self.assertEqual((found.size, found.label), (3.0, 'a'))

    def test_a_version_before_its_first_has_no_such_node(self):
        scene = x3d.loads(DOCUMENT)
        with self.assertRaises(x3d.X3DWriteError) as raised:
            x3d.dumps(scene, encoding='classic', version='3.2')
        self.assertIn('X3D 3.2 has no node ExampleMarker', str(raised.exception))
        self.assertIn('ExampleMarker', x3d.dumps(scene, encoding='classic', version='3.3'))

    def test_vrml97_has_no_such_node(self):
        with self.assertRaises(x3d.X3DWriteError):
            x3d.dumps(x3d.loads(DOCUMENT), encoding='classic', version='2.0')

    def test_a_scene_naming_the_component_is_valid(self):
        self.assertEqual(validate(x3d.loads(DOCUMENT)), [])

    def test_a_scene_without_the_component_statement_is_told(self):
        scene = x3d.loads(DOCUMENT.replace('COMPONENT Example:2\n', ''))
        found = [str(item.message) for item in validate(scene)]
        self.assertEqual(len(found), 1)
        self.assertIn('ExampleMarker needs Example level 2', found[0])

    def test_a_level_past_the_components_highest_is_told(self):
        scene = x3d.loads(DOCUMENT.replace('Example:2', 'Example:3'))
        self.assertIn('COMPONENT Example:3 is past its highest level, 2',
                      [str(item.message) for item in validate(scene)])

    def test_what_is_registered(self):
        self.assertIs(components.declaration('ExampleMarker'), Marker)
        self.assertEqual(components.component_of('ExampleMarker'), ('Example', 2))
        self.assertIn('ExampleMarker', components.types_in('4.0'))
        self.assertNotIn('ExampleMarker', components.types_in('3.2'))
        self.assertEqual(components.types_in('2.0'), frozenset())


class TestRegistering(unittest.TestCase):
    def test_an_unregistered_node_is_unknown_again(self):
        components.register(Marker)
        components.unregister(Marker)
        scene = x3d.loads(DOCUMENT)
        self.assertIn('Unknown node type ExampleMarker', said(scene))
        self.assertIn("Unknown component 'Example'", said(scene))
        self.assertIsNone(components.declaration('ExampleMarker'))

    def test_a_name_x3d_has_is_refused(self):
        class Box(nodes.X3DChildNode):
            PROTO = 'Box'
            COMPONENT = ('Example', 1)

        with self.assertRaises(ValueError):
            components.register(Box)

    def test_a_class_naming_no_component_is_refused(self):
        class Bare(nodes.X3DChildNode):
            PROTO = 'ExampleBare'
            COMPONENT = None

        with self.assertRaises(ValueError):
            components.register(Bare)

    def test_a_component_keeps_its_highest_level_while_a_node_is_in_it(self):
        class Small(nodes.X3DChildNode):
            PROTO = 'ExampleSmall'
            COMPONENT = ('Example', 1)

        components.register(Marker, Small)
        self.addCleanup(components.unregister, Marker, Small)
        from vrml.x3d import profiles  # noqa: PLC0415 kept with its use
        self.assertEqual(profiles.EXTENSION_COMPONENTS['Example'], 2)
        components.unregister(Marker)
        self.assertEqual(profiles.EXTENSION_COMPONENTS['Example'], 1)
        components.unregister(Small)
        self.assertNotIn('Example', profiles.EXTENSION_COMPONENTS)


if __name__ == '__main__':
    unittest.main()
