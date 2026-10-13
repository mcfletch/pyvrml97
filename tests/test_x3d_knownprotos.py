"""EXTERNPROTO references that name a node the vocabulary has."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from vrml import node, x3d
from vrml.vrml97 import nurbs
from vrml.x3d import knownprotos, nodes

VRML = '#VRML V2.0 utf8\n'

#: The declaration the published blaxxun NURBS worlds open with.
SURFACE = '''EXTERNPROTO NurbsSurface [
  field        SFInt32  uDimension
  field        SFInt32  vDimension
  field        MFFloat  uKnot
  field        MFFloat  vKnot
  field        SFInt32  uOrder
  field        SFInt32  vOrder
  exposedField MFVec3f  controlPoint
  exposedField MFFloat  weight
  exposedField SFInt32  uTessellation
  exposedField SFInt32  vTessellation
  exposedField SFNode   texCoord
  field        SFBool   ccw
  field        SFBool   solid
] [ %s ]
Shape { geometry NurbsSurface {
  uDimension 2 vDimension 2 uOrder 2 vOrder 2
  uKnot [ 0 0 1 1 ] vKnot [ 0 0 1 1 ]
  controlPoint [ 0 0 0, 1 0 0, 0 1 0, 1 1 0 ]
} }
'''

URN = '"urn:inet:blaxxun.com:node:NurbsSurface"'
FILE = '"nurbs.wrl#NurbsSurface"'
URL = '"http://www.blaxxun.com/vrml/protos/nurbs.wrl#NurbsSurface"'

VOCABULARY = {'NurbsSurface': nurbs.NurbsSurface, 'NurbsCurve': nurbs.NurbsCurve}


def geometry(scene):
    return scene.children[0].geometry


def messages(scene, severity):
    return [str(item.message) for item in scene.problems if item.severity == severity]


class TestKnownReferences(unittest.TestCase):
    def setUp(self):
        self.resolver = mock.Mock(return_value=None)

    def read(self, urls, text=SURFACE, vocabulary=VOCABULARY):
        return x3d.loads(VRML + text % urls, prototypes=vocabulary,
                         extern_resolver=self.resolver)

    def test_a_blaxxun_urn_is_read_as_the_vocabularys_node(self):
        scene = self.read(', '.join((URN, FILE, URL)))
        found = geometry(scene)
        self.assertIs(type(found), nurbs.NurbsSurface)
        self.assertEqual(found.uDimension, 2)
        self.assertEqual(len(found.controlPoint), 4)
        self.assertEqual(messages(scene, 'warning'), [])
        self.assertEqual(messages(scene, 'error'), [])
        self.resolver.assert_not_called()

    def test_the_load_says_which_reference_it_read_as_which_node(self):
        scene = self.read(URN)
        self.assertIn(
            'EXTERNPROTO NurbsSurface: urn:inet:blaxxun.com:node:NurbsSurface '
            'is read as the node NurbsSurface', messages(scene, 'info'))

    def test_the_published_url_is_known_and_not_fetched(self):
        found = geometry(self.read(URL))
        self.assertIs(type(found), nurbs.NurbsSurface)
        self.resolver.assert_not_called()

    def test_the_bitmanagement_urn_is_known(self):
        found = geometry(self.read('"urn:inet:bitmanagement.de:node:NurbsSurface"'))
        self.assertIs(type(found), nurbs.NurbsSurface)

    def test_a_known_reference_is_used_ahead_of_a_file_listed_before_it(self):
        found = geometry(self.read(', '.join((FILE, URN))))
        self.assertIs(type(found), nurbs.NurbsSurface)
        self.resolver.assert_not_called()

    def test_references_that_are_not_known_go_to_the_resolver(self):
        for urls in ('"urn:inet:example.com:node:NurbsSurface"',
                     '"urn:inet:blaxxun.com:node:NoSuchNode"',
                     FILE,
                     '"http://example.com/vrml/protos/nurbs.wrl#NurbsSurface"'):
            with self.subTest(urls=urls):
                self.resolver.reset_mock()
                found = geometry(self.read(urls))
                self.assertIsInstance(found, node.PrototypedNode)
                self.resolver.assert_called_once()

    def test_a_node_the_vocabulary_lacks_goes_to_the_resolver(self):
        found = geometry(self.read(URN, vocabulary={'NurbsCurve': nurbs.NurbsCurve}))
        self.assertIsInstance(found, node.PrototypedNode)
        self.resolver.assert_called_once()

    def test_field_against_exposedField_is_not_reported(self):
        text = SURFACE.replace('exposedField SFInt32  uTessellation',
                               'field SFInt32  uTessellation')
        scene = self.read(URN, text)
        self.assertIs(type(geometry(scene)), nurbs.NurbsSurface)
        self.assertEqual(messages(scene, 'warning'), [])

    def test_a_declared_field_the_node_lacks_leaves_the_declaration_as_it_was(self):
        text = SURFACE.replace('field        SFBool   solid',
                               'field        SFBool   solid\n  field SFBool closedSurface')
        scene = self.read(URN, text)
        self.assertIsInstance(geometry(scene), node.PrototypedNode)
        self.assertIn(
            'EXTERNPROTO NurbsSurface: urn:inet:blaxxun.com:node:NurbsSurface is known '
            'as the node NurbsSurface, which has no field closedSurface',
            messages(scene, 'warning'))
        self.resolver.assert_called_once()

    def test_a_declared_field_of_another_type_leaves_the_declaration_as_it_was(self):
        """X3D's NurbsCurve holds its control points in a node, the blaxxun one in a list"""
        text = ('EXTERNPROTO NurbsCurve [ exposedField MFVec3f controlPoint ] [ %s ]\n'
                'Shape { geometry NurbsCurve { controlPoint [ 0 0 0, 1 1 0 ] } }\n')
        scene = self.read('"urn:inet:blaxxun.com:node:NurbsCurve"', text,
                          vocabulary={'NurbsCurve': nodes.NurbsCurve})
        self.assertIsInstance(geometry(scene), node.PrototypedNode)
        self.assertIn(
            'EXTERNPROTO NurbsCurve: urn:inet:blaxxun.com:node:NurbsCurve is known '
            'as the node NurbsCurve, whose controlPoint is an SFNode, not an MFVec3f',
            messages(scene, 'warning'))

    def test_a_reference_inside_a_prototype_body_is_known(self):
        text = ('PROTO Sheet [ ] {\n' + SURFACE + '}\nSheet {}\n')
        scene = self.read(URN, text)
        self.assertEqual(messages(scene, 'warning'), [])
        self.resolver.assert_not_called()

    def test_a_file_an_externproto_names_is_read_with_the_same_table(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory, True)
        with open(os.path.join(directory, 'sheet.wrl'), 'w', encoding='utf-8') as stream:
            stream.write(VRML + 'PROTO Sheet [ ] {\n' + SURFACE % URN + '}\n')
        path = os.path.join(directory, 'world.wrl')
        with open(path, 'w', encoding='utf-8') as stream:
            stream.write(VRML + 'EXTERNPROTO Sheet [ ] [ "sheet.wrl#Sheet" ]\nSheet {}\n')
        scene = x3d.load(path, prototypes=VOCABULARY)
        self.assertEqual(messages(scene, 'warning'), [])
        shape = scene.children[0].scenegraph.children[0]
        self.assertIs(type(shape.geometry), nurbs.NurbsSurface)


class TestTheTable(unittest.TestCase):
    def test_a_reference_is_matched_whatever_its_case_and_scheme(self):
        for url in ('URN:INET:Blaxxun.com:node:NurbsSurface',
                    ' urn:inet:blaxxun.com:node:NurbsSurface ',
                    'https://www.blaxxun.com/vrml/protos/nurbs.wrl#NurbsSurface',
                    'HTTP://WWW.BLAXXUN.COM/vrml/protos/nurbs.wrl#NurbsSurface'):
            with self.subTest(url=url):
                reference, entry = knownprotos.KNOWN.find([url])
                self.assertEqual(reference, url.strip())
                self.assertEqual(entry.readAs, 'NurbsSurface')

    def test_the_node_name_keeps_its_case(self):
        self.assertIsNone(knownprotos.KNOWN.find(['urn:inet:blaxxun.com:node:nurbssurface']))

    def test_no_entry_for_no_urls(self):
        self.assertIsNone(knownprotos.KNOWN.find([]))
        self.assertIsNone(knownprotos.KNOWN.find(['', 'nurbs.wrl#NurbsSurface']))

    def test_the_first_known_url_decides(self):
        reference, entry = knownprotos.KNOWN.find([
            'nurbs.wrl#NurbsCurve',
            'urn:inet:blaxxun.com:node:NurbsCurve',
            'urn:inet:blaxxun.com:node:NurbsSurface'])
        self.assertEqual(reference, 'urn:inet:blaxxun.com:node:NurbsCurve')
        self.assertEqual(entry.readAs, 'NurbsCurve')

    def test_the_blaxxun_nurbs_nodes_are_in_the_table(self):
        named = {entry.readAs for entry in knownprotos.KNOWN}
        self.assertLessEqual(set(knownprotos.BLAXXUN_NURBS), named)
        for name in knownprotos.BLAXXUN_NURBS:
            for prefix in knownprotos.BLAXXUN_REFERENCES:
                self.assertIsNotNone(knownprotos.KNOWN.find([prefix + name]), prefix + name)

    def test_an_entry_is_a_node(self):
        entry = knownprotos.KnownPrototype(
            references=['urn:example:node:Ball'], readAs='Sphere')
        self.assertIsInstance(entry, node.Node)
        self.assertEqual(entry.copy().references, ['urn:example:node:Ball'])


class TestAnApplicationsEntry(unittest.TestCase):
    def setUp(self):
        self.entry = knownprotos.KnownPrototype(
            references=['urn:example:node:Ball'], readAs='Sphere')
        knownprotos.KNOWN.add(self.entry)
        self.addCleanup(knownprotos.KNOWN.remove, self.entry)

    def test_an_added_entry_is_matched(self):
        self.assertIs(knownprotos.KNOWN.find(['urn:example:node:Ball'])[1], self.entry)

    def test_a_removed_entry_is_not(self):
        knownprotos.KNOWN.remove(self.entry)
        self.addCleanup(knownprotos.KNOWN.add, self.entry)
        self.assertIsNone(knownprotos.KNOWN.find(['urn:example:node:Ball']))

    def test_a_declared_name_is_read_as_the_node_the_entry_names(self):
        scene = x3d.loads(
            '#X3D V4.0 utf8\nPROFILE Interchange\n'
            'EXTERNPROTO Ball [ initializeOnly SFFloat radius ] [ "urn:example:node:Ball" ]\n'
            'Shape { geometry DEF B Ball { radius 3 } }\n')
        found = geometry(scene)
        self.assertIs(type(found), nodes.Sphere)
        self.assertEqual(found.radius, 3)
        self.assertEqual(messages(scene, 'error'), [])
        self.assertEqual(messages(scene, 'warning'), [])

    def test_the_node_is_written_under_its_own_name(self):
        scene = x3d.loads(
            '#X3D V4.0 utf8\nPROFILE Interchange\n'
            'EXTERNPROTO Ball [ initializeOnly SFFloat radius ] [ "urn:example:node:Ball" ]\n'
            'Shape { geometry Ball { radius 3 } }\n')
        text = x3d.dumps(scene, encoding='classic')
        self.assertIn('Sphere', text)
        self.assertNotIn('Ball', text)


if __name__ == '__main__':
    unittest.main()
