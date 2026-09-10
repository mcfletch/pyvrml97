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

import io
import unittest

from vrml import node, protofunctions
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


class TestAnExternalPrototype(unittest.TestCase):
    """An EXTERNPROTO names the interface and says where the body is. Its
    declaration carries no values -- VRML97 has none there -- so what is
    written is the field list alone, then the URL."""

    SOURCE = ('#VRML V2.0 utf8\n'
              'EXTERNPROTO Wheel [ field SFFloat radius ] "wheel.wrl"\n'
              'Wheel { }\n')

    def written(self):
        return written(read(self.SOURCE))

    def test_it_is_written_as_an_externproto(self):
        self.assertIn('EXTERNPROTO Wheel', self.written())

    def test_the_url_is_written_after_the_interface(self):
        text = self.written()
        self.assertLess(text.index(']'), text.index('"wheel.wrl"'))

    def test_the_interface_carries_no_values(self):
        interface = self.written().split(']')[0]
        self.assertIn('field SFFloat radius', interface)
        self.assertNotIn('radius 0', interface)

    def test_the_url_is_not_written_as_a_declared_field(self):
        """`externalURL` is where the URL is kept, not part of what the
        prototype declares."""
        self.assertNotIn('externalURL', self.written())

    def test_what_it_wrote_reads_back(self):
        back = read(self.written())
        self.assertIn('Wheel', back.protoTypes)

    def test_the_url_reads_back(self):
        back = read(self.written())
        self.assertEqual(list(protofunctions.getExternalURL(
            back.protoTypes['Wheel'])), ['wheel.wrl'])


class TestAPrototypesEvents(unittest.TestCase):
    """A PROTO's interface declares events as well as fields."""

    SOURCE = ('#VRML V2.0 utf8\n'
              'PROTO Thing [\n'
              '  eventIn SFFloat set_x\n'
              '  eventOut SFFloat x_changed\n'
              '  field SFFloat r 1.0\n'
              ']\n'
              '{ Shape { geometry Sphere { radius IS r } } }\n'
              'Thing { }\n')

    def test_the_events_are_written(self):
        text = written(read(self.SOURCE))
        self.assertIn('eventIn SFFloat set_x', text)
        self.assertIn('eventOut SFFloat x_changed', text)

    def test_the_body_writes_its_is_mapping(self):
        self.assertIn('IS r', written(read(self.SOURCE)))

    def test_it_reads_back_with_the_mapping_intact(self):
        back = read(written(read(self.SOURCE)))
        instance = back.protoTypes['Thing']()
        instance.r = 3.0
        self.assertAlmostEqual(
            instance.scenegraph.children[0].geometry.radius, 3.0, places=5)

    def test_the_url_is_not_written_as_a_declared_field(self):
        self.assertNotIn('externalURL', written(read(self.SOURCE)))


class TestAScript(unittest.TestCase):
    """A Script declares its own interface and carries its source."""

    SOURCE = ('#VRML V2.0 utf8\n'
              'DEF Watcher Script {\n'
              '  eventIn SFFloat set_value\n'
              '  eventOut SFFloat value_changed\n'
              '  field SFFloat scale 2.0\n'
              '  url "javascript:function set_value(v){}"\n'
              '}\n')

    def written(self):
        return written(read(self.SOURCE))

    def test_it_is_written_as_a_script(self):
        self.assertIn('Script {', self.written())

    def test_its_name_is_written_once(self):
        self.assertIn('DEF Watcher Script {', self.written())

    def test_its_declared_interface_is_written(self):
        text = self.written()
        self.assertIn('eventIn SFFloat set_value', text)
        self.assertIn('eventOut SFFloat value_changed', text)
        self.assertIn('field SFFloat scale', text)

    def test_the_url_is_written_as_a_value_not_a_declaration(self):
        text = self.written()
        self.assertIn('javascript:', text)
        self.assertNotIn('field MFString url', text)

    def test_the_closing_comment_names_it(self):
        self.assertIn('}#Watcher', self.written())

    def test_what_it_wrote_reads_back(self):
        back = read(self.written())
        self.assertAlmostEqual(back.children[0].scale, 2.0, places=5)

    def test_a_script_with_no_name_is_written_too(self):
        text = written(read('#VRML V2.0 utf8\nScript { url "js:x" }\n'))
        self.assertIn('Script {', text)
        self.assertIn('}#Script', text)

    def test_one_in_two_places_is_written_once_and_used(self):
        script = read(self.SOURCE).children[0]
        text = written(SceneGraph(children=[
            basenodes.Group(children=[script, script])]))
        self.assertIn('DEF Watcher Script', text)
        self.assertIn('USE Watcher', text)

    def test_one_held_in_a_node_field_is_written_there(self):
        """An SFNode holds a whole node, and a Script is one."""
        script = read(self.SOURCE).children[0]
        text = written(SceneGraph(children=[
            basenodes.Collision(proxy=script)]))
        self.assertIn('proxy', text)
        self.assertIn('Script {', text)


class TestWritingOneSceneTwice(unittest.TestCase):
    """`linear` takes a sequence, and a graph that turns up twice in one is
    recognised as the graph already written.

    A scene graph has no DEF name to write a USE against, so the second
    turn is written out again with a comment saying so -- the same answer a
    node in two places without a name gets."""

    def written(self):
        scene = SceneGraph(children=[basenodes.Transform(DEF='Shared')])
        return linearise.Lineariser().linear([scene, scene])

    def test_it_says_what_it_did(self):
        self.assertIn('WARNING', self.written())

    def test_the_scene_is_there_both_times(self):
        self.assertEqual(self.written().count('DEF Shared'), 2)


class TestANodeFieldHoldingSomethingElse(unittest.TestCase):
    """A field that names no required types holds whatever a program puts
    in it, and the file format has a spelling only for nodes."""

    def test_it_says_which_field_and_what_it_held(self):
        held = node.SFNode('geometry', 1, node.NULL)
        held.requiredTypes = ()
        lineariser = linearise.Lineariser()
        lineariser.linear(SceneGraph())
        with self.assertRaises(TypeError) as caught:
            lineariser._sffield('not a node', held)
        self.assertIn('geometry', str(caught.exception))
        self.assertIn('not a node', str(caught.exception))


class TestAWeakNodeField(unittest.TestCase):
    """A weak node field points at a node it does not own, and is written
    like any other node field -- the field's own `vrmlstr` writes it."""

    class Holder(node.Node):
        PROTO = 'Holder'
        held = node.WeakSFNode('held', 1, node.NULL)

    def test_the_node_it_points_at_is_written(self):
        pointed = basenodes.Sphere(radius=2.0)
        holder = self.Holder(held=pointed)
        text = written(SceneGraph(children=[holder]))
        self.assertIn('held', text)
        self.assertIn('Sphere', text)

    def test_one_pointing_at_nothing_is_left_out(self):
        text = written(SceneGraph(children=[self.Holder()]))
        self.assertNotIn('held', text)


class TestALineariserThatKnowsAFieldType(unittest.TestCase):
    """A field type the lineariser has a method for is written by that
    method, which is how a subclass adds a spelling of its own."""

    class Knowing(linearise.Lineariser):
        def Silent(self, value):
            return '"%s"' % (value,)

    class Silent:
        """As little of a field as `_sffield` reads."""

        name = 'thing'

        def typeName(self):
            return 'Silent'

    def test_the_method_writes_the_value(self):
        lineariser = self.Knowing()
        lineariser.linear(SceneGraph())
        lineariser.buffer = io.StringIO()
        lineariser._sffield('a value', self.Silent())
        self.assertEqual(lineariser.buffer.getvalue(), '"a value"')


class TestSayingWhatABraceCloses(unittest.TestCase):
    """Where a node or a prototype runs on for many lines, the closing
    brace carries a comment naming what it closes, so that a reader
    scrolling to the end of one knows where they are."""

    def long_body(self):
        """A prototype with more in it than a screen holds."""
        return ('#VRML V2.0 utf8\n'
                'PROTO Wall [ field SFFloat height 1.0 ]\n'
                '{\n' + ''.join(
                    '  Shape { geometry Box { size %d %d %d } }\n' % (n, n, n)
                    for n in range(1, 20)) + '}\n'
                'Wall { }\n')

    def test_a_prototype_that_runs_on_says_what_it_closes(self):
        self.assertIn('#End PROTO Wall', written(read(self.long_body())))

    def test_a_short_one_does_not(self):
        scene = SceneGraph()
        scene.addProto(node.prototype('Wheel'))
        self.assertNotIn('#End PROTO', written(scene))

    def test_a_node_that_runs_on_says_what_it_closes(self):
        heights = [float(n) for n in range(400)]
        scene = SceneGraph(children=[basenodes.Shape(
            DEF='Ground',
            geometry=basenodes.ElevationGrid(height=heights))])
        self.assertIn('#EndNode', written(scene))

    def test_what_it_wrote_still_reads_back(self):
        self.assertIn('Wall', read(written(read(self.long_body()))).protoTypes)


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


class TestWritingNothing(unittest.TestCase):
    """NULL is a value a node field can hold, and it has a spelling."""

    def test_it_is_written_as_the_word(self):
        self.assertIn('NULL', linearise.Lineariser().linear(node.NULL))

    def test_a_field_left_at_null_is_not_written_at_all(self):
        """A field at its default is left out, and NULL is what a node
        field defaults to."""
        text = written(SceneGraph(children=[basenodes.Shape()]))
        self.assertNotIn('geometry', text)

    def test_a_field_set_to_something_is_written(self):
        text = written(SceneGraph(children=[
            basenodes.Shape(geometry=basenodes.Sphere())]))
        self.assertIn('geometry', text)


class TestANodeInTwoPlacesWithNoName(unittest.TestCase):
    """USE needs a DEF name. A node reached twice without one is written
    out again, with a comment saying what happened, because there is no
    other way to say it in the file format."""

    def scene(self):
        shared = basenodes.Transform(translation=(1, 2, 3))
        return SceneGraph(children=[
            basenodes.Group(children=[shared, shared])])

    def test_it_says_what_it_did(self):
        self.assertIn('WARNING', written(self.scene()))

    def test_the_node_is_written_both_times(self):
        text = written(self.scene())
        self.assertEqual(text.count('Transform'), 2)

    def test_what_it_wrote_still_reads_back(self):
        back = read(written(self.scene()))
        group = back.children[0]
        self.assertEqual(len(group.children), 2)
        self.assertEqual(list(group.children[1].translation), [1.0, 2.0, 3.0])


class TestNamingWhatARouteNames(unittest.TestCase):
    """A ROUTE names its ends by DEF name, so a routed node that has none
    is given one before the file is written."""

    def scene(self):
        clock = basenodes.TimeSensor()
        mover = basenodes.Transform()
        scene = SceneGraph(children=[clock, mover])
        scene.addRoute((clock, 'fraction_changed', mover, 'set_translation'))
        return scene

    def test_the_route_reads_back(self):
        back = read(written(self.scene()))
        self.assertTrue(back.routes)

    def test_both_ends_were_given_names(self):
        back = read(written(self.scene()))
        wired = back.routes[0]
        self.assertTrue(protofunctions.defName(wired.source))
        self.assertTrue(protofunctions.defName(wired.destination))

    def test_a_generated_name_does_not_take_one_that_is_taken(self):
        clock = basenodes.TimeSensor()
        mover = basenodes.Transform()
        scene = SceneGraph(children=[clock, mover])
        scene.regDefName('TimeSensor_0', basenodes.TimeSensor())
        scene.addRoute((clock, 'fraction_changed', mover, 'set_translation'))
        written(scene)
        self.assertNotEqual(protofunctions.defName(clock), 'TimeSensor_0')


class TestTwoPrototypesOfOneName(unittest.TestCase):
    """A file declares a name once. Where two prototypes answer to one,
    the first is written and the second stands for it."""

    def scene(self):
        """Two prototype classes registered under two names, both called
        Wheel -- which is what reading two files into one scene gives."""
        scene = SceneGraph()
        scene.addProto(node.prototype('Wheel'))
        scene.protoTypes['Other'] = node.prototype('Wheel')
        return scene

    def test_only_one_declaration_is_written(self):
        self.assertEqual(written(self.scene()).count('PROTO Wheel'), 1)

    def test_what_it_wrote_reads_back(self):
        self.assertIn('Wheel', read(written(self.scene())).protoTypes)


class TestWritingAPrototypeOnItsOwn(unittest.TestCase):
    """`linear` takes a prototype as readily as a node, which is how a
    caller writes a declaration without a scene around it."""

    def test_the_declaration_is_written(self):
        text = linearise.Lineariser().linear(node.prototype('Wheel'))
        self.assertIn('PROTO Wheel', text)


class TestAFieldTypeItCannotWrite(unittest.TestCase):
    """Every field type says how to write its value. One that says neither
    that nor anything the lineariser knows is named, rather than written as
    nothing and read back as a file with a field missing."""

    class Silent:
        """As little of a field as `_sffield` reads."""

        name = 'thing'

        def typeName(self):
            return 'Silent'

        def __str__(self):
            return 'field Silent thing'

    def test_it_says_which_field_type(self):
        lineariser = linearise.Lineariser()
        lineariser.linear(SceneGraph())
        with self.assertRaises(TypeError) as caught:
            lineariser._sffield('a value', self.Silent())
        self.assertIn('Silent', str(caught.exception))


class TestCarryingWhatWasWrittenBetweenPasses(unittest.TestCase):
    """A caller may hand in the record of what has been written already,
    which is how two writings share their USE names."""

    def test_it_is_the_dictionary_that_was_given(self):
        record = {}
        lineariser = linearise.Lineariser(alreadydone=record)
        lineariser.linear(SceneGraph(children=[basenodes.Group()]))
        self.assertIs(lineariser.alreadydone, record)


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
