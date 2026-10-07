"""The package's front door: vrml.x3d.load and loads."""

import os
import tempfile
import unittest
from unittest import mock

from vrml import protofunctions
from vrml import x3d
from vrml.x3d import nodes, readers


class TestLoading(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()

    def write(self, name, text):
        path = os.path.join(self.directory, name)
        with open(path, 'w', encoding='utf-8') as stream:
            stream.write(text)
        return path

    def test_load_reads_a_file_of_any_encoding(self):
        path = self.write('a.x3dv', '#X3D V4.0 utf8\nPROFILE Core\nGroup {}\n')
        scene = x3d.load(path)
        self.assertIsInstance(scene.children[0], nodes.Group)
        self.assertEqual(scene.baseURI, path)

    def test_loads_reads_bytes_or_text(self):
        self.assertIsInstance(x3d.loads(b'#X3D V4.0 utf8\nGroup {}').children[0], nodes.Group)
        self.assertIsInstance(x3d.loads('#VRML V2.0 utf8\nGroup {}').children[0], nodes.Group)

    def test_an_external_prototype_beside_the_file_is_resolved(self):
        self.write('lamps.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                 'PROTO Lamp [ inputOutput SFFloat size 3 ] '
                                 '{ Transform { scale 1 1 1 } }\n')
        path = self.write('scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                        'EXTERNPROTO Lamp [ inputOutput SFFloat size ] '
                                        '[ "lamps.x3dv#Lamp" ]\nLamp {}\n')
        scene = x3d.load(path)
        lamp = scene.children[0]
        self.assertEqual(lamp.size, 3.0)
        self.assertIsInstance(protofunctions.getSceneGraph(lamp).children[0], nodes.Transform)
        self.assertEqual(scene.problems, [])

    def test_a_remote_external_prototype_is_not_fetched(self):
        path = self.write('scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                        'EXTERNPROTO Lamp [ ] [ "https://example.com/l.x3dv" ]\n'
                                        'Lamp {}\n')
        scene = x3d.load(path)
        self.assertEqual([p.severity for p in scene.problems], ['warning'])

    def test_a_prototype_file_that_names_itself_is_read_once(self):
        path = self.write('self.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                       'EXTERNPROTO Self [ ] [ "self.x3dv#Self" ]\n')
        scene = x3d.load(path)
        self.assertEqual([p.severity for p in scene.problems], ['warning'])

    def test_prototype_files_that_name_each_other_are_each_read_once(self):
        for own in 'abc':
            others = ''.join(
                'EXTERNPROTO P%s [ ] [ "%s.x3dv#P%s" ]\n' % (other, other, other)
                for other in 'abc' if other != own)
            self.write('%s.x3dv' % own, '#X3D V4.0 utf8\nPROFILE Core\n%s'
                       'PROTO P%s [ ] { Group { } }\n' % (others, own))
        with mock.patch.object(readers, 'read', wraps=readers.read) as reading:
            scene = x3d.load(os.path.join(self.directory, 'a.x3dv'))
        self.assertEqual(sorted(os.path.basename(call.kwargs['name'])
                                for call in reading.call_args_list),
                         ['a.x3dv', 'b.x3dv', 'c.x3dv'])
        self.assertIsNotNone(scene.getProto('Pb'))


if __name__ == '__main__':
    unittest.main()
