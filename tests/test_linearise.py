"""Writing a scene graph back out as VRML97.

The strongest thing to say about a serialiser is that what it wrote reads back
as what it was given, so most of what is here parses the output again and
compares the scene. What it also has to get right is the file format's ways of
saying a thing once: `DEF` and `USE` for a node in two places, `PROTO` written
before the first instance of it, and `ROUTE` after the nodes both its ends
name.

`tests/test_tostring.py` drives two whole files through; this is each
construct on its own.
"""

import unittest

from vrml import protofunctions
from vrml.vrml97 import basenodes, linearise
from vrml.vrml97.parser import buildParser
from vrml.vrml97.scenegraph import SceneGraph

PARSER = buildParser()


def written(scene, **linvalues):
    """A scene as VRML97 text."""
    return linearise.Lineariser(**linvalues).linear(scene)


def read(text):
    """The scene a VRML97 source builds, insisting the whole of it was read."""
    success, results, consumed = PARSER.parse(text)
    if not success or consumed != len(text):
        raise AssertionError('the grammar did not accept what was written:\n%s'
                             % (text,))
    return results[1]


class TestWhatItWritesReadsBack(unittest.TestCase):
    def round_trip(self, scene):
        return read(written(scene))

    def test_an_empty_scene_is_a_header_and_nothing_else(self):
        text = written(SceneGraph())
        self.assertIn('#VRML V2.0 utf8', text)
        self.assertEqual(len(read(text).children), 0)

    def test_a_node_comes_back(self):
        scene = SceneGraph(children=[basenodes.Transform(
            translation=(1.0, 2.0, 3.0))])
        back = self.round_trip(scene)
        self.assertEqual(list(back.children[0].translation), [1.0, 2.0, 3.0])

    def test_a_nested_node_comes_back(self):
        scene = SceneGraph(children=[basenodes.Transform(children=[
            basenodes.Shape(geometry=basenodes.Sphere(radius=2.5))])])
        back = self.round_trip(scene)
        self.assertAlmostEqual(
            back.children[0].children[0].geometry.radius, 2.5, places=5)

    def test_a_string_field_comes_back(self):
        scene = SceneGraph(children=[basenodes.WorldInfo(title='a world')])
        self.assertEqual(self.round_trip(scene).children[0].title, 'a world')

    def test_a_string_with_a_quote_in_it_comes_back(self):
        scene = SceneGraph(children=[basenodes.WorldInfo(title='say "no"')])
        self.assertIn('no', self.round_trip(scene).children[0].title)

    def test_a_list_of_strings_comes_back(self):
        scene = SceneGraph(children=[basenodes.WorldInfo(
            info=['one', 'two', 'three'])])
        self.assertEqual(list(self.round_trip(scene).children[0].info),
                         ['one', 'two', 'three'])

    def test_a_long_list_of_numbers_comes_back(self):
        """Long enough that the writer breaks it across lines."""
        heights = [float(n) for n in range(200)]
        scene = SceneGraph(children=[basenodes.Shape(
            geometry=basenodes.ElevationGrid(height=heights))])
        text = written(scene)
        self.assertIn('\n', text)
        back = read(text).children[0].geometry.height
        self.assertEqual(len(back), 200)

    def test_a_boolean_comes_back(self):
        scene = SceneGraph(children=[basenodes.Collision(collide=False)])
        self.assertFalse(self.round_trip(scene).children[0].collide)


class TestSayingAThingOnce(unittest.TestCase):
    def test_a_node_used_twice_is_written_once_and_used(self):
        shared = basenodes.Transform(DEF='Shared')
        scene = SceneGraph(children=[
            basenodes.Group(children=[shared, shared])])
        text = written(scene)
        self.assertIn('DEF Shared', text)
        self.assertIn('USE Shared', text)

    def test_the_two_are_one_node_when_it_is_read_back(self):
        shared = basenodes.Transform(DEF='Shared')
        scene = SceneGraph(children=[
            basenodes.Group(children=[shared, shared])])
        group = read(written(scene)).children[0]
        self.assertIs(group.children[0], group.children[1])

    def test_a_node_used_once_needs_no_name(self):
        scene = SceneGraph(children=[basenodes.Transform()])
        self.assertNotIn('USE ', written(scene))


class TestAPrototype(unittest.TestCase):
    SOURCE = ('#VRML V2.0 utf8\n'
              'PROTO Wheel [ field SFFloat radius 1.0 ]\n'
              '{ Shape { geometry Sphere { radius 1.0 } } }\n'
              'Wheel { radius 2.0 }\n')

    def test_it_is_written_before_the_node_that_uses_it(self):
        text = written(read(self.SOURCE))
        self.assertIn('PROTO Wheel', text)
        self.assertLess(text.index('PROTO Wheel'), text.index('Wheel {'))

    def test_it_reads_back_as_a_prototype(self):
        back = read(written(read(self.SOURCE)))
        self.assertIn('Wheel', back.protoTypes)

    def test_its_instance_keeps_the_value_it_was_given(self):
        back = read(written(read(self.SOURCE)))
        self.assertAlmostEqual(back.children[0].radius, 2.0, places=5)

    def test_asking_for_it_to_be_skipped_leaves_it_out(self):
        text = linearise.Lineariser().linear(read(self.SOURCE),
                                             skipProtos=['Wheel'])
        self.assertNotIn('PROTO Wheel', text)

    def test_the_instance_is_still_written_when_it_is_skipped(self):
        """Which is the point: the fragment goes into a file that declares
        the prototype already."""
        text = linearise.Lineariser().linear(read(self.SOURCE),
                                             skipProtos=['Wheel'])
        self.assertIn('Wheel {', text)

    def test_the_prototype_itself_may_be_named_instead(self):
        scene = read(self.SOURCE)
        text = linearise.Lineariser().linear(
            scene, skipProtos=[scene.protoTypes['Wheel']])
        self.assertNotIn('PROTO Wheel', text)

    def test_a_mapping_is_read_for_its_keys(self):
        """Which is how a caller passes a scenegraph's own `protoTypes`."""
        scene = read(self.SOURCE)
        text = linearise.Lineariser().linear(scene,
                                             skipProtos=scene.protoTypes)
        self.assertNotIn('PROTO Wheel', text)

    def test_naming_none_writes_them_all(self):
        self.assertIn('PROTO Wheel', written(read(self.SOURCE)))

    def test_skipping_the_unused_ones_leaves_out_what_nothing_instantiates(self):
        source = self.SOURCE.replace('Wheel { radius 2.0 }\n', '')
        text = linearise.Lineariser().linear(read(source), skipUnusedProtos=1)
        self.assertNotIn('PROTO Wheel', text)


class TestARoute(unittest.TestCase):
    SOURCE = ('#VRML V2.0 utf8\n'
              'DEF Clock TimeSensor { }\n'
              'DEF Mover Transform { }\n'
              'ROUTE Clock.fraction_changed TO Mover.set_translation\n')

    def test_it_is_written(self):
        self.assertIn('ROUTE', written(read(self.SOURCE)))

    def test_it_names_both_ends(self):
        text = written(read(self.SOURCE))
        self.assertIn('Clock', text)
        self.assertIn('Mover', text)

    def test_it_reads_back_as_a_route(self):
        back = read(written(read(self.SOURCE)))
        self.assertTrue(back.routes)
        wired = back.routes[0]
        self.assertEqual(protofunctions.defName(wired.source), 'Clock')
        self.assertEqual(wired.sourceField, 'fraction_changed')


class TestHowItIsLaidOut(unittest.TestCase):
    """The indent and the separators are the lineariser's, and a caller may
    name their own."""

    def scene(self):
        return SceneGraph(children=[basenodes.Transform(children=[
            basenodes.Shape(geometry=basenodes.Box())])])

    def test_the_default_indent_is_a_tab(self):
        self.assertIn('\t', written(self.scene()))

    def test_a_caller_may_name_another(self):
        text = written(self.scene(), indent='    ')
        self.assertIn('\n    ', text)

    def test_what_it_wrote_reads_back_either_way(self):
        text = written(self.scene(), indent='  ')
        self.assertEqual(len(read(text).children), 1)


class TestWritingAListOfNodes(unittest.TestCase):
    """`linear` takes a sequence as well as one node, which is how a caller
    writes a fragment rather than a file."""

    def test_each_is_written(self):
        text = linearise.Lineariser().linear([
            basenodes.WorldInfo(title='first'),
            basenodes.WorldInfo(title='second'),
        ])
        self.assertIn('first', text)
        self.assertIn('second', text)


if __name__ == '__main__':
    unittest.main()
