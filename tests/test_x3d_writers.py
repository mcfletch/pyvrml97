"""Writing scenes: each encoding reads back as the scene it was written from.

The writers walk an `X3DScene` and write it in an encoding and a version:
`DEF`/`USE` from the graph's shared nodes, only the fields that differ from
the target version's defaults, prototypes, routes and the document's
statements. A version's renames apply on the way out, and what it cannot say
is refused.
"""

import gzip
import json
import os
import tempfile
import unittest

from vrml import node, protofunctions
from vrml import x3d
from vrml.x3d import nodes, writers
from vrml.x3d.compare import first_difference
from vrml.x3d.scene import LoadProblem, X3DScene
from vrml.x3d.writers import X3DWriteError

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, 'fixtures', 'x3d-schema', 'x3d-4.1.xsd')

#: A document with something of everything the writers write.
DOCUMENT = r'''#X3D V4.1 utf8
PROFILE Immersive
COMPONENT Scripting:1
UNIT length centimetre 0.01
META "title" "Everything"
PROTO Lamp [
  inputOutput SFColor lightColor 1 0 0
  initializeOnly SFFloat size 2
  inputOutput MFNode extra [ Shape { geometry Box { } } ]
  inputOnly SFBool switchOn
]
{
  Group {
    children [
      PointLight { color IS lightColor on IS switchOn }
      Shape { geometry DEF Bulb Sphere { radius IS size } }
    ]
  }
  Script { initializeOnly SFFloat scale IS size }
}
EXTERNPROTO Remote [ inputOutput SFFloat speed ] [ "remote.x3dv#Remote" "https://example.com/remote.x3dv#Remote" ]
DEF Top Transform {
  translation 100 0 -50
  rotation 0 1 0 1.5
  metadata MetadataString { name "note" value [ "say \"hi\"" "back\\slash" ] }
  children [
    DEF Ball Shape {
      appearance Appearance {
        material Material { diffuseColor 0.8 0.2 0.1 transparency 0.25 }
        texture PixelTexture { image 2 1 3 0xFF0000 0x00FF00 }
      }
      geometry IndexedFaceSet {
        coord Coordinate { point [ 0 0 0, 1 0 0, 1 1 0 ] }
        coordIndex [ 0 1 2 -1 ]
        solid FALSE
      }
    }
    USE Ball
    Lamp { lightColor 0 1 0 }
    Remote { speed 3 }
    DEF Clock TimeSensor { cycleInterval 4 loop TRUE }
    DEF Mover PositionInterpolator { key [ 0 1 ] keyValue [ 0 0 0, 0 200 0 ] }
    LOD { range [ 10 ] children [ Group { } Group { } ] }
    DEF Brain Script {
      inputOnly SFFloat tick
      outputOnly SFVec3f where
      initializeOnly MFString words [ "a" "b c" ]
      sourceCode "ecmascript: function tick(value) { where = new SFVec3f(0, value, 0); }"
    }
    Shape { geometry Text { string [ "line one" "line \"two\"" ] } }
    DEF World Inline { url "world.x3d" }
  ]
}
ROUTE Clock.fraction_changed TO Mover.set_fraction
ROUTE Mover.value_changed TO Top.set_translation
IMPORT World.Door AS FrontDoor
EXPORT Top AS Root
'''

ENCODINGS = ('xml', 'classic', 'json')


def everything():
    return x3d.loads(DOCUMENT, name=os.path.join(HERE, 'scene.x3dv'))


def errors(scene):
    return [str(p) for p in scene.problems if p.severity == 'error']


class TestRoundTrip(unittest.TestCase):
    def test_the_document_reads_without_errors(self):
        self.assertEqual(errors(everything()), [])

    def test_each_encoding_reads_back_as_the_scene(self):
        scene = everything()
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                text = x3d.dumps(scene, encoding=encoding)
                again = x3d.loads(text, name=scene.baseURI)
                self.assertEqual(errors(again), [])
                self.assertIsNone(first_difference(scene, again))

    def test_each_encoding_writes_the_prototype_bodies(self):
        scene = everything()
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                Lamp = again.getProto('Lamp')
                body = protofunctions.getSceneGraph(Lamp)
                self.assertIsNone(first_difference(
                    protofunctions.getSceneGraph(scene.getProto('Lamp')), body, header=False))
                self.assertEqual(sorted(node.ismaps(Lamp)), ['lightColor', 'size', 'switchOn'])

    def test_an_external_prototype_keeps_its_urls(self):
        scene = everything()
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertEqual(protofunctions.getExternalURL(again.getProto('Remote')),
                                 ['remote.x3dv#Remote', 'https://example.com/remote.x3dv#Remote'])

    def test_a_shared_node_is_written_once(self):
        scene = everything()
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                top = again.getDEF('Top')
                self.assertIs(top.children[0], top.children[1])

    def test_a_shared_node_with_no_name_is_given_one(self):
        sphere = nodes.Sphere(radius=3)
        scene = X3DScene(children=[nodes.Shape(geometry=sphere), nodes.Shape(geometry=sphere)])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertIs(again.children[0].geometry, again.children[1].geometry)
                self.assertEqual(protofunctions.defName(sphere), '')

    def test_routed_nodes_are_given_names(self):
        clock, light = nodes.TimeSensor(), nodes.PointLight()
        scene = X3DScene(children=[clock, light])
        scene.addRoute(clock, 'isActive', light, 'on')
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertEqual(errors(again), [])
                self.assertEqual(len(again.routes), 1)

    def test_two_nodes_of_one_name_are_told_apart(self):
        first, second = nodes.Group(), nodes.Group()
        protofunctions.defName(first, 'Same')
        protofunctions.defName(second, 'Same')
        scene = X3DScene(children=[first, second, nodes.Transform(children=[second])])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertEqual([p for p in again.problems if p.severity != 'info'], [])
                self.assertIsNot(again.children[0], again.children[1])
                self.assertIs(again.children[1], again.children[2].children[0])

    def test_a_given_name_is_kept_where_a_shared_node_would_take_it(self):
        shape = nodes.Shape()
        mover = nodes.Transform()
        protofunctions.defName(mover, 'Shape')
        scene = X3DScene(children=[shape, shape, mover])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertIsInstance(again.getDEF('Shape'), nodes.Transform)
                self.assertIs(again.children[0], again.children[1])

    def test_a_name_an_import_or_export_uses_is_not_given_to_a_shared_node(self):
        scene = x3d.loads(
            '<X3D profile="Immersive" version="4.0"><Scene>'
            '<Inline DEF="House" url=\'"house.x3d"\'/>'
            '<IMPORT inlineDEF="House" importedDEF="Door" AS="Box"/>'
            '<TimeSensor DEF="Clock"/>'
            '<ROUTE fromNode="Clock" fromField="fraction_changed" toNode="Box" toField="set_fraction"/>'
            '</Scene></X3D>')
        box = nodes.Box()
        scene.children.extend([nodes.Shape(geometry=box), nodes.Shape(geometry=box)])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertIsNone(again.getDEF('Box'))
                self.assertEqual(len(again.pendingRoutes), 1)

    def test_a_name_the_encoding_cannot_hold_is_refused(self):
        cases = [('classic', 'my mat#1'), ('classic', '1st'), ('classic', '+ab'), ('classic', '.a'),
                 ('xml', 'a b'), ('xml', '1st'), ('xml', 'a:b'), ('json', 'a b')]
        for encoding, name in cases:
            group = nodes.Group()
            protofunctions.defName(group, name)
            with self.subTest(encoding=encoding, name=name):
                with self.assertRaises(X3DWriteError) as raised:
                    x3d.dumps(X3DScene(children=[group]), encoding=encoding)
                self.assertIn(repr(name), str(raised.exception))

    def test_names_each_encoding_holds(self):
        cases = [('classic', 'a-b'), ('classic', 'Box.3.6.9'), ('classic', 'Caf\u00e9'), ('xml', 'a-b.c'),
                 ('xml', '_1'), ('json', 'Caf\u00e9')]
        for encoding, name in cases:
            group = nodes.Group()
            protofunctions.defName(group, name)
            with self.subTest(encoding=encoding, name=name):
                again = x3d.loads(x3d.dumps(X3DScene(children=[group]), encoding=encoding))
                self.assertIsInstance(again.getDEF(name), nodes.Group)

    def test_values_in_document_units_are_written_back_in_them(self):
        scene = everything()
        self.assertAlmostEqual(scene.getDEF('Top').translation[0], 1.0)
        text = x3d.dumps(scene, encoding='classic')
        self.assertIn('translation 100 0 -50', text)

    def test_a_version_without_units_is_written_in_base_units(self):
        scene = x3d.loads(x3d.dumps(everything(), encoding='classic', version='3.2'))
        self.assertEqual(list(scene.units), [])
        self.assertAlmostEqual(scene.getDEF('Top').translation[0], 1.0)

    def test_the_problems_reading_found_are_not_written(self):
        scene = everything()
        scene.problems = [LoadProblem(message='x')]
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                self.assertNotIn('LoadProblem', x3d.dumps(scene, encoding=encoding))


class TestFieldsWritten(unittest.TestCase):
    def test_a_default_value_is_not_written(self):
        text = x3d.dumps(X3DScene(children=[nodes.Sphere(radius=1), nodes.Box(size=(1, 2, 3))]))
        self.assertIn('<Sphere/>', text)
        self.assertIn("size='1 2 3'", text.replace('"', "'"))

    def test_a_value_set_back_to_its_default_is_not_written(self):
        sphere = nodes.Sphere(radius=2)
        sphere.radius = 1
        self.assertIn('<Sphere/>', x3d.dumps(X3DScene(children=[sphere])))

    def test_numbers_are_written_at_their_own_precision(self):
        text = x3d.dumps(X3DScene(children=[nodes.Material(diffuseColor=(0.8, 0.1, 0.3))]))
        self.assertIn('0.8 0.1 0.3', text)

    def test_a_field_with_a_newline_survives_xml(self):
        info = nodes.WorldInfo(title='one\ntwo\t"three" & <four>')
        again = x3d.loads(x3d.dumps(X3DScene(children=[info])))
        self.assertEqual(again.children[0].title, 'one\ntwo\t"three" & <four>')

    def test_an_mfstring_with_quotes_and_apostrophes_survives_every_encoding(self):
        info = nodes.WorldInfo(info=['it\'s "quoted"', 'back\\slash', ''])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                again = x3d.loads(x3d.dumps(X3DScene(children=[info]), encoding=encoding))
                self.assertEqual(again.children[0].info, info.info)

    def test_program_source_with_a_cdata_end_survives_xml(self):
        script = nodes.Script(sourceCode='ecmascript: var s = "]]>";')
        again = x3d.loads(x3d.dumps(X3DScene(children=[script])))
        self.assertEqual(again.children[0].sourceCode.strip(), script.sourceCode)


class TestXML(unittest.TestCase):
    def test_the_header(self):
        text = x3d.dumps(everything(), encoding='xml')
        self.assertTrue(text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n'))
        self.assertIn("<X3D profile='Immersive' version='4.1'", text.replace('"', "'"))
        self.assertNotIn('<!DOCTYPE', text)

    def test_canonical_form_names_the_dtd_and_schema(self):
        text = x3d.dumps(everything(), encoding='xml', canonical=True)
        self.assertIn('<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.1//EN" '
                      '"https://www.web3d.org/specifications/x3d-4.1.dtd">', text)
        self.assertIn('xsd:noNamespaceSchemaLocation=', text)

    def test_attributes_are_in_canonical_order(self):
        shape = nodes.Shape()
        protofunctions.defName(shape, 'S')
        collision = nodes.Collision(proxy=shape, enabled=False, bboxSize=(1, 1, 1))
        text = x3d.dumps(X3DScene(children=[collision]))
        self.assertIn("<Collision bboxSize='1 1 1' enabled='false'>", text.replace('"', "'"))
        self.assertIn("<Shape DEF='S' containerField='proxy'/>", text.replace('"', "'"))

    def test_an_implied_container_field_is_not_written(self):
        text = x3d.dumps(X3DScene(children=[nodes.Shape(geometry=nodes.Sphere())]))
        self.assertNotIn('containerField', text)

    def test_an_mfstring_attribute_is_single_quoted(self):
        text = x3d.dumps(X3DScene(children=[nodes.WorldInfo(info=['a', 'b'])]))
        self.assertIn("""info='"a" "b"'""", text)

    def test_a_prototype_instance(self):
        text = x3d.dumps(everything())
        self.assertIn("<ProtoInstance name='Lamp'>", text.replace('"', "'"))
        self.assertIn("<fieldValue name='lightColor' value='0 1 0'/>", text.replace('"', "'"))

    def test_written_xml_is_valid_against_the_schema(self):
        from lxml import etree  # noqa: PLC0415 a test-only dependency
        with open(SCHEMA, 'rb') as stream:
            schema = etree.XMLSchema(etree.parse(stream, base_url=SCHEMA))
        for canonical in (False, True):
            with self.subTest(canonical=canonical):
                text = x3d.dumps(everything(), canonical=canonical)
                document = etree.fromstring(text.encode('utf-8'), etree.XMLParser(
                    load_dtd=False, no_network=True, resolve_entities=False))
                self.assertTrue(schema.validate(document), schema.error_log)


class TestClassic(unittest.TestCase):
    def test_the_header_and_statements(self):
        text = x3d.dumps(everything(), encoding='classic')
        lines = text.splitlines()
        self.assertEqual(lines[:5], ['#X3D V4.1 utf8', 'PROFILE Immersive', 'COMPONENT Scripting:1',
                                     'UNIT length centimetre 0.01', 'META "title" "Everything"'])
        self.assertIn('ROUTE Clock.fraction_changed TO Mover.set_fraction', lines)
        self.assertIn('IMPORT World.Door AS FrontDoor', lines)
        self.assertIn('EXPORT Top AS Root', lines)

    def test_values(self):
        text = x3d.dumps(everything(), encoding='classic')
        self.assertIn('loop TRUE', text)
        self.assertIn('keyValue [ 0 0 0, 0 200 0 ]', text)
        self.assertIn('words [ "a" "b c" ]', text)


class TestJSON(unittest.TestCase):
    def test_the_document(self):
        document = json.loads(x3d.dumps(everything(), encoding='json'))
        top = document['X3D']
        self.assertEqual((top['@profile'], top['@version']), ('Immersive', '4.1'))
        self.assertEqual(top['head']['component'], [{'@name': 'Scripting', '@level': 1}])
        children = top['Scene']['-children']
        self.assertEqual(children[0]['ProtoDeclare']['@name'], 'Lamp')

    def test_values_are_typed(self):
        material = nodes.Material(diffuseColor=(0.8, 0.2, 0.1), transparency=0.25)
        shape = nodes.Shape(appearance=nodes.Appearance(material=material),
                            geometry=nodes.Box(solid=False))
        document = json.loads(x3d.dumps(X3DScene(children=[shape]), encoding='json'))
        written = document['X3D']['Scene']['-children'][0]['Shape']
        self.assertEqual(written['-geometry']['Box'], {'@solid': False})
        self.assertEqual(written['-appearance']['Appearance']['-material']['Material'],
                         {'@diffuseColor': [0.8, 0.2, 0.1], '@transparency': 0.25})


class TestVRML97(unittest.TestCase):
    def scene(self):
        return X3DScene(children=[
            nodes.LOD(range=[10], children=[nodes.Group(), nodes.Group()]),
            nodes.NavigationInfo(),
            nodes.Collision(enabled=False),
        ])

    def test_the_header_and_its_names(self):
        text = x3d.dumps(self.scene(), encoding='classic', version='2.0')
        self.assertTrue(text.startswith('#VRML V2.0 utf8\n'))
        self.assertIn('level [', text)
        self.assertIn('collide FALSE', text)
        self.assertNotIn('PROFILE', text)

    def test_a_value_equal_to_x3ds_default_is_written_for_vrml97(self):
        text = x3d.dumps(self.scene(), encoding='classic', version='2.0')
        self.assertIn('type [ "EXAMINE" "ANY" ]', text)

    def test_it_reads_back_as_the_scene(self):
        scene = self.scene()
        again = x3d.loads(x3d.dumps(scene, encoding='classic', version='2.0'))
        self.assertEqual(errors(again), [])
        self.assertIsNone(first_difference(scene, again, header=False))

    def test_declarations_use_vrml97_words(self):
        scene = x3d.loads('#X3D V4.1 utf8\nScript { inputOnly SFFloat a inputOutput SFFloat b 1 }')
        text = x3d.dumps(scene, encoding='classic', version='2.0')
        self.assertIn('eventIn SFFloat a', text)
        self.assertIn('exposedField SFFloat b 1', text)

    def test_program_source_is_written_as_an_inline_url(self):
        script = nodes.Script(sourceCode='ecmascript: function f() {}', url=['f.js'])
        text = x3d.dumps(X3DScene(children=[script]), encoding='classic', version='2.0')
        self.assertIn('url [ "ecmascript: function f() {}" "f.js" ]', text)

    def test_a_node_vrml97_lacks_is_refused(self):
        scene = X3DScene(children=[nodes.Shape(appearance=nodes.Appearance(
            material=nodes.PhysicalMaterial()))])
        with self.assertRaises(X3DWriteError) as raised:
            x3d.dumps(scene, encoding='classic', version='2.0')
        self.assertIn('PhysicalMaterial', str(raised.exception))

    def test_a_field_vrml97_lacks_is_refused_unless_at_its_default(self):
        x3d.dumps(X3DScene(children=[nodes.Transform(visible=True)]),
                  encoding='classic', version='2.0')
        with self.assertRaises(X3DWriteError) as raised:
            x3d.dumps(X3DScene(children=[nodes.Transform(visible=False)]),
                      encoding='classic', version='2.0')
        self.assertIn('Transform.visible', str(raised.exception))
        self.assertEqual(raised.exception.problems,
                         ['VRML97 has no field Transform.visible'])

    def test_vrml97_has_only_the_classic_encoding(self):
        with self.assertRaises(X3DWriteError):
            x3d.dumps(self.scene(), encoding='xml', version='2.0')

    def test_a_scene_read_from_vrml97_writes_as_vrml97(self):
        scene = x3d.loads('#VRML V2.0 utf8\nLOD { level [ Group {} ] }')
        self.assertTrue(x3d.dumps(scene, encoding='classic').startswith('#VRML V2.0 utf8'))
        self.assertIn("version='4.1'", x3d.dumps(scene).replace('"', "'"))


class TestVersions(unittest.TestCase):
    def test_a_field_an_older_x3d_lacks_is_refused(self):
        scene = X3DScene(children=[nodes.Shape(appearance=nodes.Appearance(
            backMaterial=nodes.Material()))])
        with self.assertRaises(X3DWriteError) as raised:
            x3d.dumps(scene, version='3.3')
        self.assertEqual(raised.exception.problems,
                         ['X3D 3.3 has no field Appearance.backMaterial'])

    def test_an_older_x3d_takes_its_own_names(self):
        layer = nodes.Layer(pickable=False)
        text = x3d.dumps(X3DScene(children=[nodes.LayerSet(layers=[layer])]), version='3.3')
        self.assertIn("isPickable='false'", text.replace('"', "'"))

    def test_an_unknown_version(self):
        with self.assertRaises(ValueError):
            x3d.dumps(X3DScene(), version='9.9')


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()

    def test_the_suffix_chooses_the_encoding(self):
        scene = everything()
        for name, start in (('a.x3d', b'<?xml'), ('a.x3dv', b'#X3D'), ('a.json', b'{'),
                            ('a.wrl', b'#VRML')):
            with self.subTest(name=name):
                path = os.path.join(self.directory, name)
                if name.endswith('.wrl'):
                    x3d.dump(X3DScene(children=[nodes.Group()]), path)
                else:
                    x3d.dump(scene, path)
                with open(path, 'rb') as stream:
                    self.assertTrue(stream.read().startswith(start))

    def test_a_compressed_suffix_is_gzipped(self):
        path = os.path.join(self.directory, 'a.x3dz')
        x3d.dump(everything(), path)
        with gzip.open(path, 'rb') as stream:
            self.assertTrue(stream.read().startswith(b'<?xml'))
        self.assertIsNone(first_difference(everything(), x3d.load(path)))

    def test_a_failed_write_leaves_no_file(self):
        path = os.path.join(self.directory, 'a.wrl')
        with self.assertRaises(X3DWriteError):
            x3d.dump(X3DScene(children=[nodes.PhysicalMaterial()]), path)
        self.assertEqual(os.listdir(self.directory), [])

    def test_an_unknown_suffix(self):
        with self.assertRaises(ValueError):
            x3d.dump(X3DScene(), os.path.join(self.directory, 'a.txt'))


class TestWritersModule(unittest.TestCase):
    def test_every_encoding_has_a_writer(self):
        self.assertEqual(sorted(writers.WRITERS), ['classic', 'json', 'xml'])

    def test_write_answers_text(self):
        self.assertIsInstance(writers.write(X3DScene(), 'xml'), str)


if __name__ == '__main__':
    unittest.main()
