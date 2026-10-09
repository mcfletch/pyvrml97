"""Reading the X3D XML encoding (ISO/IEC 19776-1)."""

import gzip
import os
import tempfile
import unittest

import numpy as np

from vrml import protofunctions
from vrml.x3d import nodes as x3d
from vrml.x3d import readers
from vrml.x3d.builder import X3DLoadError

HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
'''


def document(scene, head='', profile='Interchange', version='4.0'):
    return (HEADER + '<X3D profile="%s" version="%s"><head>%s</head><Scene>%s</Scene></X3D>'
            % (profile, version, head, scene)).encode('utf-8')


def read(scene, **options):
    return readers.read(document(scene, **options.pop('wrap', {})), encoding='xml', **options)


def errors(scene):
    return [p for p in scene.problems if p.severity == 'error']


class TestTheDocument(unittest.TestCase):
    def test_profile_version_and_head(self):
        scene = readers.read(document(
            '<Group/>',
            head='<component name="HAnim" level="1"/>'
                 '<unit category="length" name="centimetre" conversionFactor="0.01"/>'
                 '<meta name="title" content="A world"/>',
            profile='Immersive', version='3.3'), encoding='xml')
        self.assertEqual((scene.profile, scene.version), ('Immersive', '3.3'))
        self.assertEqual(scene.components[0].name, 'HAnim')
        self.assertEqual(scene.units[0].conversionFactor, 0.01)
        self.assertEqual(scene.meta[0].content, 'A world')
        self.assertEqual(scene.problems, [])

    def test_the_encoding_is_known_from_the_content(self):
        self.assertIsInstance(readers.read(document('<Group/>')).children[0], x3d.Group)

    def test_a_compressed_document(self):
        scene = readers.read(gzip.compress(document('<Group/>')))
        self.assertIsInstance(scene.children[0], x3d.Group)

    def test_the_dtd_is_not_fetched_and_external_entities_are_not_read(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as secret:
            secret.write('do not read me')
        try:
            text = ('<?xml version="1.0"?>\n<!DOCTYPE X3D [<!ENTITY leak SYSTEM "file://%s">]>\n'
                    '<X3D profile="Core" version="4.0"><Scene>'
                    '<WorldInfo title="&leak;"/></Scene></X3D>' % secret.name)
            scene = readers.read(text.encode('utf-8'), encoding='xml')
            titles = [child.title for child in scene.children]
            self.assertNotIn('do not read me', ''.join(titles))
        finally:
            os.unlink(secret.name)

    def test_malformed_xml_is_an_error_with_its_line(self):
        scene = readers.read(b'<X3D profile="Core" version="4.0">\n<Scene>\n<Group>\n</Scene></X3D>',
                             encoding='xml')
        self.assertEqual(len(errors(scene)), 1)
        self.assertEqual(errors(scene)[0].line, 4)

    def test_strict_mode_raises(self):
        with self.assertRaises(X3DLoadError):
            readers.read(b'<X3D><Scene><Group></Scene></X3D>', encoding='xml', strict=True)


class TestNodes(unittest.TestCase):
    def test_a_boolean_in_classic_form_is_read_with_a_warning(self):
        """19776-1 writes SFBool and MFBool as true and false"""
        scene = read('<TimeSensor loop="TRUE"/><BooleanSequencer keyValue="FALSE true"/>')
        self.assertIs(scene.children[0].loop, True)
        self.assertEqual(list(scene.children[1].keyValue), [False, True])
        self.assertEqual([p.severity for p in scene.problems], ['warning', 'warning'])

    def test_a_boolean_in_xml_form_is_read_quietly(self):
        scene = read('<TimeSensor loop="true"/>')
        self.assertEqual(scene.problems, [])

    def test_fields_children_def_and_use(self):
        scene = read(
            '<Transform DEF="T" translation="0 1 0">'
            '<Shape DEF="S"><Appearance><Material diffuseColor="1 0 0"/></Appearance>'
            '<Box size="1 2 3"/></Shape></Transform>'
            '<Transform translation="2 0 0"><Shape USE="S"/></Transform>')
        first, second = scene.children
        self.assertEqual(list(first.translation), [0, 1, 0])
        self.assertIs(first.children[0], second.children[0])
        self.assertEqual(list(first.children[0].geometry.size), [1, 2, 3])
        self.assertIs(scene.getDEF('T'), first)
        self.assertEqual(scene.problems, [])

    def test_container_field_attribute(self):
        scene = read('<Collision><Shape containerField="proxy"/></Collision>')
        self.assertIsInstance(scene.children[0].proxy, x3d.Shape)

    def test_encoding_attributes_are_not_fields(self):
        scene = read('<Group class="c" id="g" style="color:red"/>'
                     '<Shape><Text><FontStyle style="BOLD"/></Text></Shape>')
        self.assertEqual(scene.problems, [])
        self.assertEqual(scene.children[1].geometry.fontStyle.style, 'BOLD')

    def test_a_field_problem_has_its_line(self):
        scene = read('\n\n<Sphere radius="big"/>')
        self.assertEqual(errors(scene)[0].line, 5)

    def test_routes_imports_and_exports(self):
        scene = read(
            '<TimeSensor DEF="Clock" loop="true"/>'
            '<PositionInterpolator DEF="Path" key="0 1" keyValue="0 0 0 1 1 1"/>'
            '<ROUTE fromNode="Clock" fromField="fraction_changed" toNode="Path" toField="set_fraction"/>'
            '<Inline DEF="House" url=\'"house.x3d"\'/>'
            '<IMPORT inlineDEF="House" importedDEF="Door" AS="FrontDoor"/>'
            '<EXPORT localDEF="Clock" AS="Timer"/>')
        self.assertEqual(len(scene.routes), 1)
        self.assertEqual(scene.imports[0].localDEF, 'FrontDoor')
        self.assertEqual(scene.exports[0].AS, 'Timer')
        self.assertEqual(scene.problems, [])

    def test_old_version_names(self):
        scene = read('<LOD><Group containerField="level"/></LOD>',
                     wrap={'version': '2.0', 'profile': 'Full'})
        self.assertEqual(len(scene.children[0].children), 1)


class TestPrototypes(unittest.TestCase):
    SOURCE = (
        '<ProtoDeclare name="Lamp"><ProtoInterface>'
        '<field name="lightColor" type="SFColor" accessType="inputOutput" value="1 0 0"/>'
        '<field name="extra" type="MFNode" accessType="initializeOnly"><Shape/></field>'
        '</ProtoInterface><ProtoBody>'
        '<Group><IS><connect nodeField="children" protoField="extra"/></IS></Group>'
        '<PointLight><IS><connect nodeField="color" protoField="lightColor"/></IS></PointLight>'
        '</ProtoBody></ProtoDeclare>'
    )

    def test_a_prototype_declared_and_instanced(self):
        scene = read(self.SOURCE + '<ProtoInstance name="Lamp" DEF="L">'
                     '<fieldValue name="lightColor" value="0 0 1"/></ProtoInstance>')
        lamp = scene.getDEF('L')
        self.assertEqual(list(lamp.lightColor), [0, 0, 1])
        body = protofunctions.getSceneGraph(lamp)
        self.assertEqual(list(body.children[1].color), [0, 0, 1])
        self.assertEqual(scene.problems, [])

    def test_a_node_valued_field_value(self):
        scene = read(self.SOURCE + '<ProtoInstance name="Lamp">'
                     '<fieldValue name="extra"><Shape/><Shape/></fieldValue></ProtoInstance>')
        self.assertEqual(len(scene.children[0].extra), 2)

    def test_an_event_field_written_as_an_element_declares_the_event(self):
        """HAnim's prototypes write their addChildren events with a closing tag."""
        scene = read('<ProtoDeclare name="Joint"><ProtoInterface>'
                     '<field name="addChildren" type="MFNode" accessType="inputOnly"></field>'
                     '</ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare>'
                     '<ProtoInstance name="Joint"/>')
        self.assertEqual(scene.problems, [])
        self.assertEqual(protofunctions.getField(scene.children[0], 'addChildren').name,
                         'addChildren')

    def test_an_input_only_node_field_has_no_default(self):
        scene = read('<ProtoDeclare name="Holder"><ProtoInterface>'
                     '<field name="addChildren" type="MFNode" accessType="inputOnly"/>'
                     '<field name="set_target" type="SFNode" accessType="inputOnly"/>'
                     '</ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare>'
                     '<ProtoInstance name="Holder"/>')
        self.assertEqual(len(scene.children), 1)
        self.assertEqual(scene.problems, [])

    def test_an_input_only_node_field_connected_to_the_body(self):
        scene = read('<ProtoDeclare name="Holder"><ProtoInterface>'
                     '<field name="addChildren" type="MFNode" accessType="inputOnly"/>'
                     '</ProtoInterface><ProtoBody><Group><IS>'
                     '<connect nodeField="addChildren" protoField="addChildren"/>'
                     '</IS></Group></ProtoBody></ProtoDeclare>'
                     '<ProtoInstance name="Holder"/>')
        self.assertEqual(len(scene.children), 1)
        self.assertEqual(scene.problems, [])

    def test_nodes_given_for_an_input_only_field_are_reported(self):
        scene = read('<ProtoDeclare name="Holder"><ProtoInterface>'
                     '<field name="addChildren" type="MFNode" accessType="inputOnly">'
                     '<Group/></field></ProtoInterface><ProtoBody><Group/></ProtoBody>'
                     '</ProtoDeclare><ProtoInstance name="Holder"/>')
        self.assertEqual(len(scene.children), 1)
        self.assertEqual([p.severity for p in scene.problems], ['error'])

    def test_an_external_prototype(self):
        scene = read('<ExternProtoDeclare name="Far" url=\'"far.x3d#Far"\'>'
                     '<field name="size" type="SFFloat" accessType="initializeOnly"/>'
                     '</ExternProtoDeclare><ProtoInstance name="Far">'
                     '<fieldValue name="size" value="2"/></ProtoInstance>')
        self.assertEqual(scene.children[0].size, 2.0)
        self.assertEqual(protofunctions.getExternalURL(scene.getProto('Far')),
                         ['far.x3d#Far'])


class TestScripts(unittest.TestCase):
    def test_declared_fields_and_inline_source_are_kept(self):
        scene = read(
            '<Script DEF="S"><field name="speed" type="SFFloat" accessType="initializeOnly" value="2"/>'
            '<field name="target" type="SFNode" accessType="initializeOnly"><Group/></field>'
            '<![CDATA[ecmascript:\nfunction initialize() {}\n]]></Script>')
        script = scene.getDEF('S')
        self.assertEqual(script.speed, 2.0)
        self.assertIsInstance(script.target, x3d.Group)
        self.assertIn('function initialize', script.sourceCode)
        self.assertEqual([p.severity for p in scene.problems], ['warning'])

    def test_a_shader_part_keeps_its_source(self):
        scene = read('<Shape><Appearance><ComposedShader language="GLSL">'
                     '<ShaderPart type="VERTEX"><![CDATA[void main() {}]]></ShaderPart>'
                     '</ComposedShader></Appearance></Shape>')
        part = scene.children[0].appearance.shaders[0].parts[0]
        self.assertEqual(part.sourceCode, 'void main() {}')


class TestValues(unittest.TestCase):
    def test_the_codec_reads_each_type(self):
        scene = read('<Shape><IndexedFaceSet coordIndex="0 1 2 -1" solid="false">'
                     '<Coordinate point="0 0 0, 1 0 0, 0 1 0"/>'
                     '<ColorRGBA color="1 0 0 1, 0 1 0 1, 0 0 1 0.5"/>'
                     '</IndexedFaceSet></Shape>')
        faces = scene.children[0].geometry
        self.assertIs(faces.solid, False)
        self.assertEqual(faces.coord.point.shape, (3, 3))
        np.testing.assert_allclose(faces.color.color[2], [0, 0, 1, 0.5])


if __name__ == '__main__':
    unittest.main()


def test_an_element_of_another_namespace_is_skipped_with_its_content():
    """An XML Signature, or an application's own element, is not an X3D node"""
    scene = readers.read(b"""<X3D version='3.3' xmlns:ds='http://www.w3.org/2000/09/xmldsig#'>
        <Scene><Group/><ds:Signature><ds:SignedInfo><Shape/></ds:SignedInfo></ds:Signature>
        <Transform/></Scene></X3D>""", name='a.x3d')
    assert [type(child).__name__ for child in scene.children] == ['Group', 'Transform']
    assert [problem.severity for problem in scene.problems] == ['info']
    assert 'ds:Signature' in scene.problems[0].message


def test_a_def_name_that_is_no_xml_name_is_kept_with_a_warning():
    """An XML DEF is an xs:ID, an NCName; a scene read with another can be
    written only where its encoding allows the name"""
    scene = readers.read(b"""<X3D version='4.0'><Scene><Group DEF='Left Hand'/>
        <Group DEF='1st'/><Group DEF='a-b.c'/></Scene></X3D>""", name='a.x3d')
    assert isinstance(scene.getDEF('Left Hand'), x3d.Group)
    assert [(problem.severity, problem.message) for problem in scene.problems] == [
        ('warning', "DEF name 'Left Hand' is not an XML name"),
        ('warning', "DEF name '1st' is not an XML name"),
    ]
