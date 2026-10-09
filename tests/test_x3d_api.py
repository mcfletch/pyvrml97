"""The package's front door: vrml.x3d.load and loads."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from vrml import protofunctions
from vrml import x3d
from vrml.x3d import nodes, readers


class TestLoading(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory, True)

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

    def test_what_a_reader_handles_is_in_the_package(self):
        from vrml.x3d import builder, scene  # noqa: PLC0415 kept with its use
        self.assertIs(x3d.X3DLoadError, builder.X3DLoadError)
        self.assertIs(x3d.X3DScene, scene.X3DScene)
        self.assertIs(x3d.LoadProblem, scene.LoadProblem)
        with self.assertRaises(x3d.X3DLoadError):
            x3d.loads('#X3D V4.0 utf8\nNoSuchNode {}', strict=True)

    def test_a_staged_write_leaves_nothing_where_it_fails(self):
        from vrml.x3d.files import staged  # noqa: PLC0415 kept with its use
        path = os.path.join(self.directory, 'out.x3d')
        with self.assertRaises(RuntimeError):
            with staged(path) as stream:
                stream.write(b'half')
                raise RuntimeError('disk full')
        self.assertEqual(os.listdir(self.directory), [])
        with staged(path) as stream:
            stream.write(b'whole')
        self.assertEqual(os.listdir(self.directory), ['out.x3d'])

    def test_a_misspelt_option_is_refused(self):
        with self.assertRaises(TypeError):
            x3d.loads('#X3D V4.0 utf8\nGroup {}', strcit=True)
        with self.assertRaises(TypeError):
            readers.read(b'#X3D V4.0 utf8\nGroup {}', strcit=True)

    def test_loads_reads_bytes_or_text(self):
        self.assertIsInstance(x3d.loads(b'#X3D V4.0 utf8\nGroup {}').children[0], nodes.Group)
        self.assertIsInstance(x3d.loads('#VRML V2.0 utf8\nGroup {}').children[0], nodes.Group)

    def test_loads_reads_text_whatever_encoding_it_declares(self):
        scene = x3d.loads('<?xml version="1.0" encoding="ISO-8859-1"?>'
                          '<X3D profile="Core" version="4.0"><Scene>'
                          '<WorldInfo title="café"/></Scene></X3D>')
        self.assertEqual(scene.children[0].title, 'café')

    def test_bytes_are_read_in_the_encoding_they_declare(self):
        scene = x3d.loads('<?xml version="1.0" encoding="ISO-8859-1"?>'
                          '<X3D profile="Core" version="4.0"><Scene>'
                          '<WorldInfo title="café"/></Scene></X3D>'.encode('latin-1'))
        self.assertEqual(scene.children[0].title, 'café')

    def test_a_charset_named_outside_the_document(self):
        data = '#X3D V4.0 utf8\nPROFILE Core\nWorldInfo { title "café" }\n'.encode('latin-1')
        self.assertEqual(readers.read(data, charset='latin-1').children[0].title, 'café')

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

    def test_an_external_prototype_named_with_escapes(self):
        self.write('my lamps.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                    'PROTO Lamp [ inputOutput SFFloat size 3 ] { Group { } }\n')
        path = self.write('scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                        'EXTERNPROTO Lamp [ inputOutput SFFloat size ] '
                                        '[ "my%20lamps.x3dv#Lamp" ]\nLamp {}\n')
        self.assertEqual(x3d.load(path).children[0].size, 3.0)

    def test_an_external_prototype_url_with_no_name_takes_the_files_first(self):
        """19775-1 4.9.3: the first PROTO in the file, not counting EXTERNPROTOs,
        whatever its name (ConformanceNist EXTERNPROTO/first_proto)"""
        self.write('lamps.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                 'EXTERNPROTO Other [ ] [ "missing.x3dv" ]\n'
                                 'PROTO Blue [ inputOutput SFFloat size 3 ] { Group { } }\n'
                                 'PROTO Lamp [ inputOutput SFFloat size 5 ] { Group { } }\n')
        path = self.write('scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                        'EXTERNPROTO Lamp [ inputOutput SFFloat size ] '
                                        '[ "lamps.x3dv" ]\nLamp {}\n')
        self.assertEqual(x3d.load(path).children[0].size, 3.0)

    def test_where_an_external_prototype_url_leads(self):
        from vrml.x3d.files import local_path  # noqa: PLC0415 kept with its use
        base = os.path.join(os.sep, 'worlds', 'scene.x3d')
        cases = [
            ('lamps.x3d#Lamp', (os.path.join(os.sep, 'worlds', 'lamps.x3d'), 'Lamp')),
            ('my%20lamps.x3d', (os.path.join(os.sep, 'worlds', 'my lamps.x3d'), '')),
            ('file:///shared/lamps.x3d#L', (os.path.normpath('/shared/lamps.x3d'), 'L')),
            ('C:/protos/lamps.x3d#L', ('C:/protos/lamps.x3d', 'L')),
            ('https://example.com/lamps.x3d', None),
            ('#Lamp', None),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(local_path(url, base), expected)

    def test_a_remote_external_prototype_is_not_fetched(self):
        path = self.write('scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                        'EXTERNPROTO Lamp [ ] [ "https://example.com/l.x3dv" ]\n'
                                        'Lamp {}\n')
        with mock.patch('urllib.request.urlopen',
                        side_effect=AssertionError('a remote prototype was fetched')):
            scene = x3d.load(path)
        self.assertEqual([p.severity for p in scene.problems], ['warning'])

    def test_a_prototype_file_that_names_itself_is_read_once(self):
        path = self.write('self.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                       'EXTERNPROTO Self [ ] [ "self.x3dv#Self" ]\n')
        with mock.patch.object(readers, 'read', wraps=readers.read) as reading:
            scene = x3d.load(path)
        self.assertEqual(reading.call_count, 1)
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
