"""Reading the ClassicVRML encoding (ISO/IEC 19776-2) and VRML97."""

import time
import unittest

import numpy as np
import pytest

from vrml import protofunctions
from vrml.x3d import codecs, readers
from vrml.x3d import nodes as x3d
from vrml.x3d.readers import classic


def read(text, **options):
    return readers.read(text.encode('utf-8'), encoding='classic', **options)


def x3d_document(body, header='#X3D V4.0 utf8\nPROFILE Interchange\n'):
    return read(header + body)


def errors(scene):
    return [p for p in scene.problems if p.severity == 'error']


class TestHeaders(unittest.TestCase):
    def test_an_x3d_header_and_its_statements(self):
        scene = read('#X3D V3.3 utf8\n'
                     '# a comment\n'
                     'PROFILE Immersive\n'
                     'COMPONENT HAnim:1\n'
                     'UNIT length centimetre 0.01\n'
                     'META "title" "A world"\n'
                     'Transform { translation 100 0 0 }\n')
        self.assertEqual((scene.profile, scene.version), ('Immersive', '3.3'))
        self.assertEqual((scene.components[0].name, scene.components[0].level), ('HAnim', 1))
        self.assertEqual(scene.meta[0].content, 'A world')
        np.testing.assert_allclose(scene.children[0].translation, [1, 0, 0])
        self.assertEqual(scene.problems, [])

    def test_the_version_may_be_written_without_v(self):
        self.assertEqual(read('#X3D 4.0 utf8\nPROFILE Core\n').version, '4.0')

    def test_a_vrml97_header(self):
        scene = read('#VRML V2.0 utf8\nLOD { level [ Group {} ] }\nSpotLight {}\n')
        self.assertEqual(scene.version, '2.0')
        self.assertEqual(len(scene.children[0].children), 1)
        self.assertAlmostEqual(scene.children[1].beamWidth, 1.570796, places=5)
        self.assertEqual(scene.problems, [])

    def test_an_unknown_version_is_one_warning_on_the_header(self):
        scene = read('#X3D V4.2 utf8\nPROFILE Interchange\nTransform {}\n')
        self.assertEqual([(p.severity, p.line) for p in scene.problems], [('warning', 1)])
        self.assertEqual(scene.profile, 'Interchange')

    def test_a_missing_header_is_an_error(self):
        self.assertEqual(len(errors(read('Group {}'))), 1)

    def test_it_is_recognised_by_its_header(self):
        self.assertIsInstance(readers.read(b'#X3D V4.0 utf8\nPROFILE Core\nGroup {}').children[0],
                              x3d.Group)


class TestNodes(unittest.TestCase):
    def test_fields_and_children(self):
        scene = x3d_document('''
            DEF T Transform {
              translation 0 1 0
              rotation 0, 1, 0, 1.57
              children [
                DEF S Shape {
                  appearance Appearance { material Material { diffuseColor 1 0 0 } }
                  geometry IndexedFaceSet {
                    coordIndex [ 0 1 2 -1 ]
                    solid FALSE
                    coord Coordinate { point [ 0 0 0, 1 0 0, 0 1 0 ] }
                  }
                }
              ]
            }
            Transform { children USE S }
        ''')
        first, second = scene.children
        self.assertIs(first.children[0], second.children[0])
        faces = first.children[0].geometry
        self.assertEqual(faces.coord.point.shape, (3, 3))
        self.assertIs(faces.solid, False)
        self.assertEqual(list(faces.coordIndex), [0, 1, 2, -1])
        self.assertEqual(scene.problems, [])

    def test_strings_with_escapes_and_comment_characters(self):
        scene = x3d_document('WorldInfo { title "a \\"quoted\\" # not a comment" '
                             'info [ "one", "two\\\\" ] }')
        self.assertEqual(scene.children[0].title, 'a "quoted" # not a comment')
        self.assertEqual(scene.children[0].info, ['one', 'two\\'])

    def test_comments(self):
        scene = x3d_document('Group { # line\n#/* a block\n with } inside */#\n children [] }')
        self.assertEqual(scene.problems, [])

    def test_null_and_single_values_of_list_fields(self):
        scene = x3d_document('Shape { appearance NULL geometry Text { string "one" length 2 } }')
        self.assertEqual(scene.children[0].geometry.string, ['one'])
        self.assertEqual(list(scene.children[0].geometry.length), [2.0])

    def test_hex_integers(self):
        scene = x3d_document('Shape { appearance Appearance { texture PixelTexture '
                             '{ image 1 1 3 0xFF8800 } } }')
        self.assertEqual(list(scene.children[0].appearance.texture.image), [1, 1, 3, 0xFF8800])

    def test_an_unknown_field_is_skipped_with_a_warning(self):
        scene = x3d_document('Transform { nosuch [ 1 2 3 ] translation 1 2 3 }')
        self.assertEqual(list(scene.children[0].translation), [1, 2, 3])
        self.assertEqual(len([p for p in scene.problems if p.severity == 'warning']), 1)

    def test_a_syntax_error_has_its_line(self):
        scene = x3d_document('Group {\n children [\n Shape { ]\n')
        self.assertTrue(errors(scene))
        self.assertEqual(errors(scene)[0].line, 5)


class TestProblems(unittest.TestCase):
    def test_a_problem_names_the_x3d_type_not_the_engines_class(self):
        class EngineTransform(x3d.Transform):
            pass
        scene = read('#X3D V4.0 utf8\nPROFILE Core\nTransform { nosuch 1 }\n',
                     prototypes={'Transform': EngineTransform})
        messages = [p.message for p in scene.problems if p.severity == 'warning']
        self.assertEqual(messages, ['Transform has no field nosuch'])


class TestNumberLists(unittest.TestCase):
    """A bracketed list of numbers is read as one span, which its field type decodes"""

    def test_signs_exponents_commas_and_hex(self):
        scene = x3d_document('Shape { geometry IndexedFaceSet { coordIndex [ 0x2, 1, -1 ]\n'
                             'coord Coordinate { point [ 1, -2.5e1 +3, .5 0. 4E0\n 7 8 9 ] } } }')
        faces = scene.children[0].geometry
        self.assertEqual(list(faces.coordIndex), [2, 1, -1])
        np.testing.assert_allclose(faces.coord.point, [[1, -25, 3], [0.5, 0, 4], [7, 8, 9]])
        self.assertEqual(scene.problems, [])

    def test_empty_lists_of_nodes(self):
        scene = x3d_document('Group { children [ ] } Group { children [] }')
        self.assertEqual([group.children for group in scene.children], [[], []])
        self.assertEqual(scene.problems, [])

    def test_comments_strings_and_words_among_the_values(self):
        scene = x3d_document('Coordinate { point [ 1 2 3 # the first\n 4 5 6 ] }\n'
                             'WorldInfo { info [ "1", "2" ] }\n'
                             'Switch { }')
        np.testing.assert_allclose(scene.children[0].point, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(scene.children[1].info, ['1', '2'])
        self.assertEqual(scene.problems, [])

    def test_a_malformed_number_is_an_error(self):
        scene = x3d_document('Coordinate { point [ 1.2.3 0 0 ] }')
        self.assertEqual(len(errors(scene)), 1)
        self.assertIn('Coordinate.point', errors(scene)[0].message)

    @pytest.mark.serial
    def test_parsing_a_list_costs_less_than_decoding_it(self):
        """The grammar does not take the numbers of a list one by one"""
        body = ' '.join('%.6f' % value for value in np.random.default_rng(1).normal(size=200000))
        document = '#X3D V3.3 utf8\nCoordinate { point [ %s ] }\n' % body

        def fastest(call):
            times = []
            for _ in range(5):
                start = time.perf_counter()
                call()
                times.append(time.perf_counter() - start)
            return min(times)
        parsing = fastest(lambda: classic.PARSER.parse(document))
        decoding = fastest(lambda: codecs.decode('MFVec3f', body))
        self.assertLess(parsing, 0.75 * decoding)


class TestStatements(unittest.TestCase):
    def test_routes_imports_exports(self):
        scene = x3d_document('''
            DEF Clock TimeSensor { loop TRUE }
            DEF Path PositionInterpolator { key [ 0 1 ] keyValue [ 0 0 0, 1 1 1 ] }
            ROUTE Clock.fraction_changed TO Path.set_fraction
            DEF House Inline { url "house.x3dv" }
            IMPORT House.Door AS FrontDoor
            EXPORT Clock AS Timer
        ''')
        self.assertEqual(len(scene.routes), 1)
        self.assertEqual(scene.imports[0].localDEF, 'FrontDoor')
        self.assertEqual(scene.exports[0].AS, 'Timer')
        self.assertEqual(scene.problems, [])


class TestPrototypes(unittest.TestCase):
    SOURCE = '''
        PROTO Lamp [
          inputOutput SFColor lightColor 1 0 0
          initializeOnly MFNode extra [ Shape {} ]
        ] {
          Group { children IS extra }
          PointLight { color IS lightColor }
        }
    '''

    def test_declared_and_instanced(self):
        scene = x3d_document(self.SOURCE + 'DEF L Lamp { lightColor 0 0 1 extra [ Shape {} Shape {} ] }')
        lamp = scene.getDEF('L')
        self.assertEqual(list(protofunctions.getSceneGraph(lamp).children[1].color), [0, 0, 1])
        self.assertEqual(len(lamp.extra), 2)
        self.assertEqual(scene.problems, [])

    def test_an_external_prototype(self):
        scene = x3d_document('EXTERNPROTO Far [ initializeOnly SFFloat size ] [ "far.x3dv#Far" ]\n'
                             'Far { size 2 }')
        self.assertEqual(scene.children[0].size, 2.0)

    def test_vrml97_declarations(self):
        scene = read('#VRML V2.0 utf8\n'
                     'PROTO Thing [ exposedField SFFloat r 1.0 eventIn SFFloat set_x ] '
                     '{ Sphere { radius IS r } }\n'
                     'Shape { geometry Thing { r 2 } }')
        self.assertEqual(scene.children[0].geometry.r, 2.0)
        self.assertEqual(protofunctions.getSceneGraph(scene.children[0].geometry)
                         .children[0].radius, 2.0)
        self.assertEqual([p.severity for p in scene.problems], ['warning'],
                         'an exposedField is joined to the field radius')

    def test_declared_among_a_nodes_fields(self):
        scene = x3d_document(
            'Group {\n'
            '  PROTO Outer [ inputOutput SFNode n Box { size 2 2 2 } ] {\n'
            '    PROTO Inner [ ] { Group { } }\n'
            '    Shape { geometry IS n }\n'
            '  }\n'
            '  children [ Outer { } ]\n'
            '}', header='#X3D V4.0 utf8\nPROFILE Immersive\n')
        group = scene.children[0]
        self.assertEqual(len(group.children), 1)
        self.assertEqual(list(group.children[0].n.size), [2, 2, 2])
        self.assertEqual(scene.problems, [])

    def test_vrml97_declarations_in_an_x3d_file_are_a_warning(self):
        scene = x3d_document('PROTO Thing [ field SFFloat r 1.0 ] { Group {} }')
        self.assertEqual([p.severity for p in scene.problems], ['warning'])


class TestScripts(unittest.TestCase):
    def test_declared_fields_and_source(self):
        scene = x3d_document('''
            DEF G Group {}
            DEF S Script {
              initializeOnly SFFloat speed 2
              initializeOnly SFNode target USE G
              inputOnly SFTime set_time
              outputOnly SFVec3f position
              url "ecmascript: function initialize() {}"
            }
        ''')
        script = scene.getDEF('S')
        self.assertEqual(script.speed, 2.0)
        self.assertIs(script.target, scene.getDEF('G'))
        self.assertIn('function initialize', script.url[0])
        self.assertEqual([p.severity for p in scene.problems], ['warning'])


if __name__ == '__main__':
    unittest.main()


class TestWhatWeb3DsConverterWrites(unittest.TestCase):
    """X3dToClassicVrml writes some XML documents into text the ClassicVRML
    grammar does not allow; each is read with a warning."""

    def test_a_name_with_a_full_stop(self):
        scene = x3d_document('DEF brick.jpg ImageTexture { url "brick.jpg" }\n'
                             'Shape { appearance Appearance { texture USE brick.jpg } }')
        self.assertIs(scene.children[1].appearance.texture, scene.getDEF('brick.jpg'))
        self.assertEqual([p.severity for p in scene.problems], ['warning', 'warning'])

    def test_a_route_between_names_with_full_stops(self):
        """A field name holds no full stop, so the last one ends the node's name"""
        scene = x3d_document('DEF clock.a TimeSensor { }\nDEF Spin.b.c OrientationInterpolator { }\n'
                             'ROUTE clock.a.fraction_changed TO Spin.b.c.set_fraction')
        self.assertEqual([(protofunctions.defName(r.source), r.sourceField,
                           protofunctions.defName(r.destination), r.destinationField)
                          for r in scene.routes],
                         [('clock.a', 'fraction_changed', 'Spin.b.c', 'set_fraction')])
        self.assertEqual([p.message for p in scene.problems], [
            "Name 'clock.a' holds a full stop", "Name 'Spin.b.c' holds a full stop",
            "Name 'clock.a' holds a full stop", "Name 'Spin.b.c' holds a full stop"])

    def test_a_prototype_among_a_list_of_nodes(self):
        scene = x3d_document('Group { children [ EXTERNPROTO Far [ ] "far.x3dv"\n'
                             'Far {} ] }')
        self.assertEqual(len(scene.children[0].children), 1)
        # the declaration among nodes, and the note that nothing read far.x3dv
        self.assertEqual([p.severity for p in scene.problems], ['warning', 'info'])
