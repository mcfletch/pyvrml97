"""Reading a VRML97 file: what the parser builds out of each construct.

`tests/test_tostring.py` drives whole files through the parser and back out
again, which covers the common path well. What is here is the rest of the
grammar: every field type at least once, PROTO and EXTERNPROTO, Script with
its own field and event declarations, ROUTE, DEF and USE, and IS -- the wiring
that maps a prototype's field onto a field of a node inside its body.
"""

import unittest

from vrml import protofunctions
from vrml.vrml97.parser import buildParser
from vrml.vrml97.scenegraph import SceneGraph


PARSER = buildParser()


def parse(source):
    """The scene graph a source builds, insisting the whole of it was read."""
    success, results, consumed = PARSER.parse(source)
    if not success:
        raise AssertionError('the grammar did not accept the source')
    if consumed != len(source):
        raise AssertionError(
            'only %d of %d characters were read' % (consumed, len(source)))
    scene = results[1]
    assert isinstance(scene, SceneGraph), scene
    return scene


HEADER = '#VRML V2.0 utf8\n'


def scene(body):
    return parse(HEADER + body)


class TestTheSingleValuedFields(unittest.TestCase):
    """One of each, since each has its own handler."""

    def test_a_bool_reads_true_and_false(self):
        built = scene('Shape { geometry Sphere { } appearance NULL }\n')
        self.assertIsNotNone(built.children[0])

    def test_a_bool_field(self):
        built = scene('Collision { collide FALSE }\n')
        self.assertFalse(built.children[0].collide)
        built = scene('Collision { collide TRUE }\n')
        self.assertTrue(built.children[0].collide)

    def test_a_float_field(self):
        built = scene('Sphere { radius 2.5 }\n')
        self.assertAlmostEqual(built.children[0].radius, 2.5, places=5)

    def test_a_float_in_exponent_form(self):
        built = scene('Sphere { radius 2.5e1 }\n')
        self.assertAlmostEqual(built.children[0].radius, 25.0, places=4)

    def test_an_int_field(self):
        built = scene('Switch { whichChoice 3 }\n')
        self.assertEqual(built.children[0].whichChoice, 3)

    def test_an_int_in_hex(self):
        built = scene('Switch { whichChoice 0x10 }\n')
        self.assertEqual(built.children[0].whichChoice, 16)

    def test_a_three_vector_field(self):
        built = scene('Transform { translation 1 2 3 }\n')
        self.assertEqual(list(built.children[0].translation), [1.0, 2.0, 3.0])

    def test_a_two_vector_field(self):
        built = scene('Shape { geometry ElevationGrid { xSpacing 2.0 } }\n')
        self.assertIsNotNone(built.children[0].geometry)

    def test_a_rotation_field(self):
        built = scene('Transform { rotation 0 1 0 1.57 }\n')
        self.assertEqual(len(built.children[0].rotation), 4)

    def test_a_string_field(self):
        built = scene('WorldInfo { title "a world" }\n')
        self.assertEqual(built.children[0].title, 'a world')

    def test_a_string_with_an_escaped_quote(self):
        built = scene(r'WorldInfo { title "say \"hello\"" }' + '\n')
        self.assertIn('hello', built.children[0].title)

    def test_a_string_with_a_backslash(self):
        built = scene(r'WorldInfo { title "a\\b" }' + '\n')
        self.assertIn('a', built.children[0].title)

    def test_a_null_node_field(self):
        built = scene('Shape { appearance NULL geometry Box { } }\n')
        self.assertFalse(built.children[0].appearance)


class TestTheMultipleValuedFields(unittest.TestCase):
    def test_a_float_list(self):
        built = scene('Shape { geometry ElevationGrid { height [ 1 2 3 ] } }\n')
        self.assertEqual(list(built.children[0].geometry.height), [1.0, 2.0, 3.0])

    def test_an_int_list(self):
        built = scene(
            'Shape { geometry IndexedFaceSet { coordIndex [ 0 1 2 -1 ] } }\n')
        self.assertEqual(list(built.children[0].geometry.coordIndex),
                         [0, 1, 2, -1])

    def test_an_int_list_in_hex(self):
        built = scene(
            'Shape { geometry IndexedFaceSet { coordIndex [ 0x1 0x2 ] } }\n')
        self.assertEqual(list(built.children[0].geometry.coordIndex), [1, 2])

    def test_a_string_list(self):
        built = scene('WorldInfo { info [ "one" "two" ] }\n')
        self.assertEqual(list(built.children[0].info), ['one', 'two'])

    def test_an_empty_list(self):
        built = scene('WorldInfo { info [ ] }\n')
        self.assertEqual(list(built.children[0].info), [])

    def test_a_vector_list(self):
        built = scene(
            'Shape { geometry IndexedFaceSet { coord Coordinate '
            '{ point [ 0 0 0, 1 0 0, 0 1 0 ] } } }\n')
        self.assertEqual(len(built.children[0].geometry.coord.point), 3)

    def test_a_colour_list(self):
        built = scene('Background { skyColor [ 0 0 1, 1 1 1 ] }\n')
        self.assertEqual(len(built.children[0].skyColor), 2)


class TestDefAndUse(unittest.TestCase):
    def test_a_def_name_is_recorded(self):
        built = scene('DEF Root Transform { translation 1 0 0 }\n')
        self.assertIn('Root', built.defNames)

    def test_a_use_answers_the_same_node(self):
        built = scene(
            'Group { children [ DEF Shared Transform { }, USE Shared ] }\n')
        group = built.children[0]
        self.assertIs(group.children[0], group.children[1])

    def test_using_a_name_that_was_never_defined_says_which(self):
        with self.assertRaises(NameError) as caught:
            scene('Group { children [ USE NoSuchName ] }\n')
        self.assertIn('NoSuchName', str(caught.exception))


class TestRoutes(unittest.TestCase):
    def test_a_route_is_recorded_on_the_scene(self):
        built = scene(
            'DEF Clock TimeSensor { }\n'
            'DEF Mover Transform { }\n'
            'ROUTE Clock.fraction_changed TO Mover.set_translation\n')
        self.assertTrue(built.routes)

    def test_a_route_names_both_ends(self):
        built = scene(
            'DEF Clock TimeSensor { }\n'
            'DEF Mover Transform { }\n'
            'ROUTE Clock.fraction_changed TO Mover.set_translation\n')
        wired = built.routes[0]
        self.assertEqual(protofunctions.defName(wired.source), 'Clock')
        self.assertEqual(wired.sourceField, 'fraction_changed')
        self.assertEqual(protofunctions.defName(wired.destination), 'Mover')
        self.assertEqual(wired.destinationField, 'set_translation')

    def test_a_route_from_a_name_that_was_never_defined_says_which(self):
        with self.assertRaises(NameError):
            scene('ROUTE NoSuchNode.field TO AlsoMissing.field\n')


class TestPrototypes(unittest.TestCase):
    WHEEL = (
        'PROTO Wheel [ field SFFloat radius 1.0 ]\n'
        '{ Shape { geometry Sphere { radius 1.0 } } }\n')

    def test_a_prototype_is_registered_on_the_scene(self):
        built = scene(self.WHEEL)
        self.assertIn('Wheel', built.protoTypes)

    def test_a_prototype_declares_the_field_it_names(self):
        built = scene(self.WHEEL)
        declared = {f.name for f
                    in protofunctions.getFields(built.protoTypes['Wheel'])}
        self.assertIn('radius', declared)

    def test_a_prototype_can_be_instantiated(self):
        built = scene(self.WHEEL + 'Wheel { radius 2.0 }\n')
        self.assertAlmostEqual(built.children[0].radius, 2.0, places=5)

    def test_an_exposed_field_is_declared_too(self):
        built = scene(
            'PROTO Wheel [ exposedField SFFloat radius 1.0 ]\n'
            '{ Shape { geometry Sphere { } } }\n')
        declared = {f.name for f
                    in protofunctions.getFields(built.protoTypes['Wheel'])}
        self.assertIn('radius', declared)

    def test_an_event_declaration_is_recorded(self):
        built = scene(
            'PROTO Wheel [ eventIn SFFloat set_radius\n'
            '              eventOut SFFloat radius_changed ]\n'
            '{ Shape { geometry Sphere { } } }\n')
        declared = {f.name for f in protofunctions.getFields(
            built.protoTypes['Wheel'], events=1)}
        self.assertIn('set_radius', declared)

    def test_an_is_map_wires_a_field_through(self):
        """`IS` maps a field inside the body onto one the prototype declares."""
        built = scene(
            'PROTO Wheel [ field SFFloat radius 1.0 ]\n'
            '{ Shape { geometry Sphere { radius IS radius } } }\n')
        self.assertIn('Wheel', built.protoTypes)

    def test_an_extern_prototype_records_its_url(self):
        built = scene(
            'EXTERNPROTO Wheel [ field SFFloat radius ]\n'
            '[ "http://example.com/wheel.wrl#Wheel" ]\n')
        url = protofunctions.getExternalURL(built.protoTypes['Wheel'])
        self.assertIn('http://example.com/wheel.wrl#Wheel', list(url))

    def test_an_extern_prototype_url_may_be_a_bare_string(self):
        built = scene(
            'EXTERNPROTO Wheel [ field SFFloat radius ]\n'
            '"http://example.com/wheel.wrl"\n')
        self.assertIn('Wheel', built.protoTypes)


class TestScripts(unittest.TestCase):
    def test_a_script_node_is_built(self):
        built = scene('Script { }\n')
        self.assertEqual(protofunctions.protoName(built.children[0].__class__),
                         'Script')

    def test_a_script_declares_its_own_field(self):
        built = scene('Script { field SFFloat speed 2.0 }\n')
        self.assertAlmostEqual(built.children[0].speed, 2.0, places=5)

    def test_a_script_declares_its_own_events(self):
        built = scene(
            'Script {\n'
            '  eventIn SFFloat set_speed\n'
            '  eventOut SFFloat speed_changed\n'
            '}\n')
        self.assertIsNotNone(built.children[0])

    def test_a_script_keeps_the_standard_fields(self):
        built = scene('Script { url "javascript:" directOutput TRUE }\n')
        self.assertTrue(built.children[0].directOutput)


class TestComments(unittest.TestCase):
    def test_a_comment_on_its_own_line(self):
        built = scene('# a comment\nTransform { translation 1 0 0 }\n')
        self.assertEqual(list(built.children[0].translation), [1.0, 0.0, 0.0])

    def test_a_comment_after_a_field(self):
        built = scene('Transform { translation 1 0 0 # trailing\n }\n')
        self.assertEqual(list(built.children[0].translation), [1.0, 0.0, 0.0])

    def test_commas_separate_values(self):
        built = scene('Transform { translation 1, 2, 3 }\n')
        self.assertEqual(list(built.children[0].translation), [1.0, 2.0, 3.0])


class TestErrors(unittest.TestCase):
    def test_a_node_type_that_does_not_exist_says_which(self):
        with self.assertRaises(NameError) as caught:
            scene('NoSuchNodeType { }\n')
        self.assertIn('NoSuchNodeType', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
