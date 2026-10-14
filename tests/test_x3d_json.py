"""Reading the X3D JSON encoding: Web3D's X3D JSON design, which the
examples archives publish every scene in."""

import json
import unittest

from vrml import protofunctions
from vrml.x3d import nodes as x3d
from vrml.x3d import readers


def read(children, head=None, profile='Interchange', version='4.0', **options):
    document = {'X3D': {
        'encoding': 'UTF-8', '@profile': profile, '@version': version,
        'head': head or {}, 'Scene': {'-children': children},
    }}
    return readers.read(json.dumps(document).encode('utf-8'), **options)


class TestTheDocument(unittest.TestCase):
    def test_profile_version_and_head(self):
        scene = read([{'Group': {}}], head={
            'component': [{'@name': 'HAnim', '@level': 1}],
            'unit': [{'@category': 'length', '@name': 'mm', '@conversionFactor': 0.001}],
            'meta': [{'@name': 'title', '@content': 'A world'}],
        }, profile='Immersive', version='3.3')
        self.assertEqual((scene.profile, scene.version), ('Immersive', '3.3'))
        self.assertEqual(scene.components[0].level, 1)
        self.assertEqual(scene.units[0].conversionFactor, 0.001)
        self.assertEqual(scene.meta[0].name, 'title')
        self.assertEqual(scene.problems, [])

    def test_it_is_recognised_by_its_content(self):
        self.assertIsInstance(read([{'Group': {}}]).children[0], x3d.Group)

    def test_malformed_json_is_an_error(self):
        scene = readers.read(b'{"X3D": {', encoding='json')
        self.assertEqual([p.severity for p in scene.problems], ['error'])

    def test_a_document_without_x3d_is_an_error(self):
        scene = readers.read(b'{"model": {}}', encoding='json')
        self.assertEqual([p.severity for p in scene.problems], ['error'])

    def test_a_problem_names_its_place_in_the_document(self):
        scene = read([{'Group': {}}, {'Transform': {'-children': [
            {'Shape': {'-geometry': {'Sphere': {'@radius': 'big'}}}}]}}])
        problem = [p for p in scene.problems if p.severity == 'error'][0]
        self.assertEqual(problem.path,
                         'Scene/-children[1]/Transform/-children[0]/Shape/-geometry/Sphere/@radius')
        self.assertIn('at Scene/-children[1]', str(problem))

    def test_a_malformed_head_is_an_error_and_the_scene_is_read(self):
        scene = read([{'Group': {}}], head={
            'component': [{'@name': 'HAnim', '@level': 'x'}, 'HAnim'],
            'unit': [{'@category': 'length', '@name': 'mm', '@conversionFactor': 'small'}],
            'meta': ['title'],
        })
        self.assertEqual([p.severity for p in scene.problems], ['error'] * 4)
        self.assertIsInstance(scene.children[0], x3d.Group)

    def test_a_head_or_scene_that_is_not_an_object_is_an_error(self):
        for document in ({'X3D': {'head': ['component'], 'Scene': {}}},
                         {'X3D': {'Scene': [{'Group': {}}]}}):
            scene = readers.read(json.dumps(document).encode('utf-8'), encoding='json')
            self.assertEqual([p.severity for p in scene.problems], ['error'])

    def test_nodes_nested_past_the_readers_depth_are_an_error(self):
        # Written as text: `json.dumps` has a depth of its own to run out of.
        for depth in (400, 100000):
            nested = '{"Group":{"-children":[' * depth + '{"Group":{}}' + ']}}' * depth
            document = '{"X3D":{"Scene":{"-children":[%s]}}}' % nested
            scene = readers.read(document.encode('utf-8'), encoding='json')
            self.assertEqual([p.severity for p in scene.problems], ['error'], depth)
            self.assertIn('nested too deeply', scene.problems[0].message)


class TestNodes(unittest.TestCase):
    def test_values_children_def_and_use(self):
        scene = read([
            {'#comment': 'a comment'},
            {'Transform': {'@DEF': 'T', '@translation': [0, 1, 0], '-children': [
                {'Shape': {'@DEF': 'S',
                           '-appearance': {'Appearance': {'-material': {
                               'Material': {'@diffuseColor': [1, 0, 0]}}}},
                           '-geometry': {'Box': {'@size': [1, 2, 3], '@solid': False}}}},
            ]}},
            {'Transform': {'-children': [{'Shape': {'@USE': 'S'}}]}},
        ])
        first, second = scene.children
        self.assertEqual(list(first.translation), [0, 1, 0])
        self.assertIs(first.children[0], second.children[0])
        self.assertIs(first.children[0].geometry.solid, False)
        self.assertEqual(scene.problems, [])

    def test_strings(self):
        scene = read([{'Shape': {'-geometry': {'Text': {
            '@string': ['one', 'two'],
            '-fontStyle': {'FontStyle': {'@style': 'BOLD', '@justify': ['MIDDLE']}}}}}}])
        text = scene.children[0].geometry
        self.assertEqual(text.string, ['one', 'two'])
        self.assertEqual(text.fontStyle.style, 'BOLD')

    def test_routes_imports_exports(self):
        scene = read([
            {'TimeSensor': {'@DEF': 'Clock'}},
            {'PositionInterpolator': {'@DEF': 'Path', '@key': [0, 1],
                                      '@keyValue': [0, 0, 0, 1, 1, 1]}},
            {'ROUTE': {'@fromNode': 'Clock', '@fromField': 'fraction_changed',
                       '@toNode': 'Path', '@toField': 'set_fraction'}},
            {'Inline': {'@DEF': 'House', '@url': ['house.x3d']}},
            {'IMPORT': {'@inlineDEF': 'House', '@importedDEF': 'Door', '@AS': 'FrontDoor'}},
            {'EXPORT': {'@localDEF': 'Clock', '@AS': 'Timer'}},
        ])
        self.assertEqual(len(scene.routes), 1)
        self.assertEqual(scene.imports[0].localDEF, 'FrontDoor')
        self.assertEqual(scene.exports[0].AS, 'Timer')
        self.assertEqual(scene.problems, [])


#: A prototype declaration in the JSON encoding.
DECLARATION = {'ProtoDeclare': {
    '@name': 'Lamp',
    'ProtoInterface': {'field': [
        {'@name': 'lightColor', '@type': 'SFColor', '@accessType': 'inputOutput',
         '@value': [1, 0, 0]},
        {'@name': 'extra', '@type': 'MFNode', '@accessType': 'initializeOnly',
         '-children': [{'Shape': {}}]},
    ]},
    'ProtoBody': {'-children': [
        {'Group': {'IS': {'connect': [{'@nodeField': 'children', '@protoField': 'extra'}]}}},
        {'PointLight': {'IS': {'connect': [
            {'@nodeField': 'color', '@protoField': 'lightColor'}]}}},
    ]},
}}


class TestPrototypes(unittest.TestCase):
    def test_declared_and_instanced(self):
        scene = read([DECLARATION, {'ProtoInstance': {
            '@name': 'Lamp', '@DEF': 'L',
            'fieldValue': [{'@name': 'lightColor', '@value': [0, 0, 1]},
                           {'@name': 'extra', '-children': [{'Shape': {}}, {'Shape': {}}]}]}}])
        lamp = scene.getDEF('L')
        self.assertEqual(list(protofunctions.getSceneGraph(lamp).children[1].color), [0, 0, 1])
        self.assertEqual(len(lamp.extra), 2)
        self.assertEqual(scene.problems, [])

    def test_an_external_prototype(self):
        scene = read([{'ExternProtoDeclare': {
            '@name': 'Far', '@url': ['far.x3d#Far'],
            'field': [{'@name': 'size', '@type': 'SFFloat', '@accessType': 'initializeOnly'}]}},
            {'ProtoInstance': {'@name': 'Far', 'fieldValue': [{'@name': 'size', '@value': 2}]}}])
        self.assertEqual(scene.children[0].size, 2.0)

    def test_a_comment_among_a_value_fields_children_leaves_its_default(self):
        scene = read([{'ProtoDeclare': {
            '@name': 'Keyed',
            'ProtoInterface': {'field': [
                {'@name': 'key', '@type': 'MFFloat', '@accessType': 'inputOutput',
                 '-children': [{'#comment': 'NULL initialization value'}]},
                {'@name': 'keyValue', '@type': 'MFVec4f', '@accessType': 'inputOutput',
                 '-children': [{'#comment': 'NULL initialization value'}]}]},
            'ProtoBody': {'-children': [{'Group': {}}]}}},
            {'ProtoInstance': {'@name': 'Keyed', '@DEF': 'K'}}])
        self.assertEqual(scene.problems, [])
        self.assertEqual(list(scene.getDEF('K').key), [])
        self.assertEqual(len(scene.getDEF('K').keyValue), 0)

    def test_a_node_given_to_a_value_field_is_reported(self):
        scene = read([{'ProtoDeclare': {
            '@name': 'Keyed',
            'ProtoInterface': {'field': [
                {'@name': 'key', '@type': 'MFFloat', '@accessType': 'inputOutput',
                 '-children': [{'Shape': {}}]}]},
            'ProtoBody': {'-children': [{'Group': {}}]}}}])
        self.assertEqual([problem.message for problem in scene.problems],
                         ['Prototype field key is an MFFloat, which takes no nodes'])
        self.assertEqual(list(scene.protoTypes['Keyed'].key.getDefault()), [])


class TestScripts(unittest.TestCase):
    def test_fields_and_source(self):
        scene = read([
            {'Group': {'@DEF': 'G'}},
            {'Script': {'@DEF': 'S', 'field': [
                {'@name': 'speed', '@type': 'SFFloat', '@accessType': 'initializeOnly',
                 '@value': 2},
                {'@name': 'target', '@type': 'SFNode', '@accessType': 'initializeOnly',
                 '-children': [{'Group': {'@USE': 'G'}}]}],
                '#sourceCode': ['ecmascript:', 'function initialize() {}']}},
        ])
        script = scene.getDEF('S')
        self.assertEqual(script.speed, 2.0)
        self.assertIs(script.target, scene.getDEF('G'))
        self.assertEqual(script.sourceCode, 'ecmascript:\nfunction initialize() {}')



class TestOrder(unittest.TestCase):
    def test_a_use_before_its_def_is_the_same_node(self):
        """Members are grouped by field, so `-children` can come before the
        `-proxy` whose node it uses."""
        scene = read([{'Collision': {
            '-children': [{'Transform': {'@USE': 'P'}}],
            '-proxy': {'Transform': {'@DEF': 'P', '@translation': [0, 1, 0]}},
        }}])
        collision = scene.children[0]
        self.assertIs(collision.children[0], collision.proxy)
        self.assertEqual(list(collision.proxy.translation), [0, 1, 0])
        self.assertEqual(scene.problems, [])

    def test_a_node_used_before_its_def_keeps_a_field_called_name(self):
        scene = read([{'MetadataSet': {
            '-value': [{'MetadataString': {'@USE': 'M'}}],
            '-metadata': {'MetadataString': {'@DEF': 'M', '@name': 'colour'}},
        }}])
        self.assertEqual(scene.getDEF('M').name, 'colour')
        self.assertEqual(scene.problems, [])

    def test_a_prototype_instance_used_before_its_def(self):
        scene = read([DECLARATION, {'Collision': {
            '-children': [{'ProtoInstance': {'@USE': 'L', '@name': 'Lamp'}}],
            '-proxy': {'ProtoInstance': {'@DEF': 'L', '@name': 'Lamp', 'fieldValue': [
                {'@name': 'lightColor', '@value': [0, 0, 1]}]}},
        }}])
        collision = scene.children[0]
        self.assertIs(collision.children[0], collision.proxy)
        self.assertEqual(list(collision.proxy.lightColor), [0, 0, 1])
        self.assertEqual(scene.problems, [])


class TestWhatWeb3DsConverterWrites(unittest.TestCase):
    """X3dToJson writes some values in shapes the field type does not."""

    def test_an_mfstring_written_as_its_xml_text(self):
        scene = read([{'NavigationInfo': {'@type': '"EXAMINE" "WALK"'}}])
        self.assertEqual(scene.children[0].type, ['EXAMINE', 'WALK'])

    def test_a_string_field_given_a_boolean(self):
        scene = read([{'Script': {'@DEF': 'S', 'field': [
            {'@name': 'horizontal', '@type': 'SFString', '@accessType': 'initializeOnly',
             '@value': True}]}}])
        self.assertEqual(scene.getDEF('S').horizontal, 'true')

    def test_an_mfstring_field_given_booleans(self):
        scene = read([{'Text': {'@string': [True, 'x']}}])
        self.assertEqual(scene.children[0].string, ['true', 'x'])


def test_a_def_name_that_is_no_xml_name_is_kept_with_a_warning():
    scene = read([{'Group': {'@DEF': 'Left Hand'}}])
    assert isinstance(scene.getDEF('Left Hand'), x3d.Group)
    assert [problem.message for problem in scene.problems] == [
        "DEF name 'Left Hand' is not an XML name"]


if __name__ == '__main__':
    unittest.main()
