"""The package's front door: vrml.x3d.load and loads."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from vrml import protofunctions
from vrml import x3d
from vrml.x3d import files, nodes, readers


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
        from vrml.x3d.files import contained_path  # noqa: PLC0415 kept with its use
        self.write('my lamps.x3d', '')
        os.mkdir(os.path.join(self.directory, 'worlds'))
        base = os.path.join(self.directory, 'worlds', 'scene.x3d')
        inside = os.path.realpath(os.path.join(self.directory, 'worlds'))
        cases = [
            ('lamps.x3d', None, os.path.join(inside, 'lamps.x3d')),
            ('my%20lamps.x3d', None, os.path.join(inside, 'my lamps.x3d')),
            ('sub/../lamps.x3d', None, os.path.join(inside, 'lamps.x3d')),
            ('../my%20lamps.x3d', None, None),
            ('../my%20lamps.x3d', self.directory,
             os.path.join(os.path.realpath(self.directory), 'my lamps.x3d')),
            (os.path.join(self.directory, 'my lamps.x3d'), None, None),
            ('file:///shared/lamps.x3d', None, None),
            ('C:/protos/lamps.x3d', None, None),
            ('//host/share/lamps.x3d', None, None),
            ('https://example.com/lamps.x3d', None, None),
            ('lamps%00.x3d', None, None),
            ('', None, None),
        ]
        for url, root, expected in cases:
            with self.subTest(url=url, root=root):
                self.assertEqual(contained_path(url, base, root), expected)

    def test_a_reference_has_no_file_without_a_document_location(self):
        from vrml.x3d.files import contained_path  # noqa: PLC0415 kept with its use
        self.assertIsNone(contained_path('lamps.x3d', ''))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'needs symbolic links')
    def test_a_link_leading_out_of_the_folder_is_not_followed(self):
        from vrml.x3d.files import contained_path  # noqa: PLC0415 kept with its use
        outside = self.write('lamps.x3dv', '')
        os.mkdir(os.path.join(self.directory, 'worlds'))
        try:
            os.symlink(outside, os.path.join(self.directory, 'worlds', 'lamps.x3dv'))
        except OSError as err:
            self.skipTest('no symbolic links here: %s' % err)
        base = os.path.join(self.directory, 'worlds', 'scene.x3dv')
        self.assertIsNone(contained_path('lamps.x3dv', base))

    def test_an_external_prototype_outside_the_folder_is_not_read(self):
        outside = self.write('lamps.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                           'PROTO Lamp [ ] { Group { } }\n')
        os.mkdir(os.path.join(self.directory, 'worlds'))
        for url in ('../lamps.x3dv#Lamp', outside + '#Lamp', 'file://' + outside + '#Lamp'):
            with self.subTest(url=url):
                path = self.write('worlds/scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                  'EXTERNPROTO Lamp [ ] [ "%s" ]\nLamp {}\n' % url)
                with mock.patch.object(readers, 'read', wraps=readers.read) as reading:
                    scene = x3d.load(path)
                self.assertEqual(reading.call_count, 1)
                self.assertEqual([p.severity for p in scene.problems], ['warning'])

    def test_a_root_widens_what_external_prototypes_may_name(self):
        from vrml.x3d.files import LocalPrototypes  # noqa: PLC0415 kept with its use
        self.write('lamps.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                 'PROTO Lamp [ inputOutput SFFloat size 3 ] { Group { } }\n')
        os.mkdir(os.path.join(self.directory, 'worlds'))
        path = self.write('worlds/scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                          'EXTERNPROTO Lamp [ inputOutput SFFloat size ] '
                          '[ "../lamps.x3dv#Lamp" ]\nLamp {}\n')
        scene = x3d.load(path, extern_resolver=LocalPrototypes(root=self.directory))
        self.assertEqual(scene.children[0].size, 3.0)

    def test_an_external_prototype_file_over_the_size_limit_is_not_read(self):
        self.write('lamps.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                 'PROTO Lamp [ ] { Group { } }\n')
        path = self.write('scene.x3dv', '#X3D V4.0 utf8\nPROFILE Core\n'
                                        'EXTERNPROTO Lamp [ ] [ "lamps.x3dv#Lamp" ]\nLamp {}\n')
        with mock.patch.object(files, 'MAX_PROTOTYPE_BYTES', 10):
            scene = x3d.load(path)
        self.assertEqual([p.severity for p in scene.problems], ['warning'])

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


class Table(files.ExternPrototypes):
    """Reads prototype files from a dict of name: document text"""

    def __init__(self, documents, **named):
        super().__init__(**named)
        self.documents = documents
        self.read_names = []

    def locate(self, reference, base):  # noqa: ARG002 the hook's signature; every document shares the table
        return 'table:' + reference if reference in self.documents else None

    def read(self, reference, base):
        self.read_names.append((reference, base))
        return self.documents[reference].encode('utf-8')


class TestExternPrototypes(unittest.TestCase):
    """What a resolver gets from the base class, wherever its files come from"""

    HEADER = '#X3D V4.0 utf8\nPROFILE Core\n'

    def test_the_named_prototype_of_the_file(self):
        table = Table({'lamps': self.HEADER + 'PROTO A [ ] { Group { } }\n'
                                              'PROTO B [ ] { Group { } }\n'})
        found = table(['lamps#B'], 'scene', 'Lamp')
        self.assertEqual(protofunctions.name(found), 'B')

    def test_the_first_prototype_where_none_is_named(self):
        table = Table({'lamps': self.HEADER + 'PROTO A [ ] { Group { } }\n'
                                              'PROTO B [ ] { Group { } }\n'})
        self.assertEqual(protofunctions.name(table(['lamps'], 'scene', 'Lamp')), 'A')

    def test_the_next_url_where_one_cannot_be_read(self):
        table = Table({'lamps': self.HEADER + 'PROTO A [ ] { Group { } }\n'})
        self.assertIsNotNone(table(['missing#A', '#A', 'lamps#Other', 'lamps#A'], 'scene', 'A'))

    def test_a_file_is_read_once_and_its_base_is_the_document_naming_it(self):
        table = Table({'lamps': self.HEADER + 'PROTO A [ ] { Group { } }\n'})
        table(['lamps#A'], 'scene', 'A')
        table(['lamps#A'], 'other', 'A')
        self.assertEqual(table.read_names, [('lamps', 'scene')])

    def test_a_file_names_prototypes_in_another(self):
        table = Table({
            'outer': self.HEADER + 'EXTERNPROTO Inner [ ] [ "inner#Inner" ]\n'
                                   'PROTO Outer [ ] { Inner { } }\n',
            'inner': self.HEADER + 'PROTO Inner [ ] { Group { } }\n',
        })
        self.assertIsNotNone(table(['outer#Outer'], 'scene', 'Outer'))
        self.assertEqual(table.read_names, [('outer', 'scene'), ('inner', 'table:outer')])
        self.assertIsNotNone(table.scenes['table:inner'].getProto('Inner'))

    def test_files_are_read_to_the_depth_limit(self):
        documents = {
            str(index): self.HEADER + 'EXTERNPROTO P [ ] [ "%d#P" ]\n' % (index + 1)
            for index in range(files.MAX_PROTOTYPE_DEPTH + 4)}
        table = Table(documents)
        table(['0#P'], 'scene', 'P')
        self.assertEqual(len(table.read_names), files.MAX_PROTOTYPE_DEPTH)

    def test_the_options_are_those_each_file_is_read_with(self):
        class Lamp(nodes.Group):
            pass
        table = Table({'lamps': self.HEADER + 'PROTO A [ ] { Lamp { } }\n'},
                      prototypes={'Lamp': Lamp})
        found = table(['lamps#A'], 'scene', 'A')
        self.assertIsInstance(protofunctions.getSceneGraph(found()).children[0], Lamp)


if __name__ == '__main__':
    unittest.main()
