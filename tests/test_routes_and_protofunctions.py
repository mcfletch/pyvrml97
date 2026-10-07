"""Routes -- how one node's field feeds another's -- and the prototype helpers.

A ROUTE is VRML97's wiring: a change to a source field is forwarded to a
destination field on another node. `protofunctions` is the accessor set for the
things a node holds outside its own fields -- its prototype name, its DEF name,
the scene graph it belongs to, the URL an EXTERNPROTO came from.
"""

import unittest

from vrml import field, node, protofunctions, route
from vrml.vrml97 import basenodes
from vrml.vrml97.scenegraph import SceneGraph
from vrml import copier


class TestBuildingARoute(unittest.TestCase):
    def setUp(self):
        self.source = basenodes.TimeSensor(DEF='clock')
        self.destination = basenodes.Transform(DEF='mover')

    def test_it_takes_its_four_parts_by_name(self):
        wired = route.ROUTE(
            source=self.source, sourceField='fraction_changed',
            destination=self.destination, destinationField='translation')
        self.assertIs(wired.source, self.source)
        self.assertEqual(wired.sourceField, 'fraction_changed')

    def test_it_takes_its_four_parts_positionally(self):
        """`ROUTE(source, sourceField, destination, destinationField)` is how
        the parser builds one, reading them off the file in that order."""
        wired = route.ROUTE(self.source, 'fraction_changed',
                            self.destination, 'translation')
        self.assertIs(wired.source, self.source)
        self.assertEqual(wired.sourceField, 'fraction_changed')
        self.assertIs(wired.destination, self.destination)
        self.assertEqual(wired.destinationField, 'translation')

    def test_its_string_form_names_both_ends(self):
        wired = route.ROUTE(self.source, 'fraction_changed',
                            self.destination, 'translation')
        shown = str(wired)
        self.assertIn('fraction_changed', shown)
        self.assertIn('translation', shown)


class TestForwardingAValue(unittest.TestCase):
    """What a route is for: a change at one end reaching the other."""

    def setUp(self):
        self.source = basenodes.Transform(DEF='source')
        self.destination = basenodes.Transform(DEF='destination')
        self.route = route.ROUTE(self.source, 'translation',
                                 self.destination, 'translation')

    def test_building_one_binds_it(self):
        """A ROUTE connects itself as it is built -- which is what lets a
        parser wire a scene up by constructing them as it reads the file."""
        self.source.translation = (1.0, 2.0, 3.0)
        self.assertEqual(list(self.destination.translation), [1.0, 2.0, 3.0])

    def test_binding_again_does_not_double_the_value(self):
        self.route.bind()
        self.source.translation = (7.0, 8.0, 9.0)
        self.assertEqual(list(self.destination.translation), [7.0, 8.0, 9.0])

    def test_each_change_carries(self):
        self.source.translation = (1.0, 0.0, 0.0)
        self.source.translation = (0.0, 1.0, 0.0)
        self.assertEqual(list(self.destination.translation), [0.0, 1.0, 0.0])

    def test_binding_a_field_that_is_not_there_is_reported_not_raised(self):
        """A scene file can name a field the node does not have, and the rest
        of it is still worth loading."""
        wired = route.ROUTE(self.source, 'nosuchfield',
                            self.destination, 'translation')
        wired.bind()

    def test_binding_a_route_with_no_source_is_reported_not_raised(self):
        wired = route.ROUTE(None, 'translation', self.destination, 'translation')
        wired.bind()

    def test_a_field_the_destination_does_not_have_is_reported_not_raised(self):
        """A scene file can name a field the other node does not have, and
        the write that set the cascade going is not the place to raise."""
        wired = route.ROUTE(self.source, 'translation',
                            self.destination, 'whichChoice')
        wired.bind()
        self.source.translation = (1.0, 2.0, 3.0)

    def test_a_value_the_destination_refuses_is_reported_not_raised(self):
        """A route runs inside a field notification, which has nobody to raise
        to, so a bad value is reported and the rest of the cascade goes on."""
        held = basenodes.Sphere()
        wired = route.ROUTE(self.source, 'translation', held, 'radius')
        wired.bind()
        self.source.translation = (1.0, 2.0, 3.0)
        self.assertAlmostEqual(held.radius, 1.0, places=5)

    def test_deleting_the_source_field_forwards_the_default(self):
        """Putting a field back to its default is a change like any other,
        and what carries is the value a read now answers."""
        self.source.translation = (1.0, 2.0, 3.0)
        del self.source.translation
        self.assertEqual(list(self.destination.translation), [0.0, 0.0, 0.0])

    def test_an_event_may_be_the_far_end(self):
        """An eventIn is not a field, and is written into rather than set."""
        held = basenodes.Transform()
        wired = route.ROUTE(self.source, 'children', held, 'addChildren')
        wired.bind()
        child = basenodes.Group()
        self.source.children = [child]
        self.assertEqual(list(held.addChildren), [child])

    def test_a_value_an_event_refuses_is_reported_not_raised(self):
        """A node's handler for an event may refuse what reaches it, and
        that is as far as the refusal goes."""

        class Refusing(node.Node):
            PROTO = 'Refusing'
            set_size = field.newEvent('set_size', 'SFFloat', 0)

            def on_set_size(self, value):  # noqa: ARG002 an event handler takes the value
                raise ValueError('no')

        wired = route.ROUTE(self.source, 'translation',
                            Refusing(), 'set_size')
        wired.bind()
        self.source.translation = (1.0, 2.0, 3.0)


class TestCopyingARoute(unittest.TestCase):
    def setUp(self):
        self.source = basenodes.Transform(DEF='source')
        self.destination = basenodes.Transform(DEF='destination')
        self.route = route.ROUTE(self.source, 'translation',
                                 self.destination, 'translation')

    def test_it_needs_the_copier_that_is_doing_the_copy(self):
        """Both ends have to be copied first for the new route to point at
        anything, and the copier is what knows their copies."""
        with self.assertRaises(ValueError):
            self.route.copy()

    def test_it_copies_with_one(self):
        duplicate = self.route.copy(copier.Copier())
        self.assertIsNot(duplicate, self.route)
        self.assertEqual(duplicate.sourceField, 'translation')


class TestPrototypeAccessors(unittest.TestCase):
    def test_the_prototype_name_reads_back(self):
        self.assertEqual(protofunctions.protoName(basenodes.Transform),
                         'Transform')

    def test_the_prototype_name_can_be_set(self):
        built = node.prototype('Wheel')
        protofunctions.protoName(built, 'Axle')
        self.assertEqual(protofunctions.protoName(built), 'Axle')

    def test_the_def_name_reads_back(self):
        self.assertEqual(protofunctions.defName(basenodes.Transform(DEF='x')),
                         'x')

    def test_name_answers_the_def_for_a_node(self):
        self.assertEqual(protofunctions.name(basenodes.Transform(DEF='x')), 'x')

    def test_name_answers_the_prototype_for_a_class(self):
        self.assertEqual(protofunctions.name(basenodes.Transform), 'Transform')

    def test_the_root_reads_back_and_writes(self):
        graph = SceneGraph()
        transform = basenodes.Transform()
        protofunctions.root(transform, graph)
        self.assertIs(protofunctions.root(transform), graph)

    def test_a_built_in_class_says_so(self):
        self.assertTrue(protofunctions.builtin(basenodes.Transform))

    def test_a_prototype_built_here_is_not_built_in(self):
        self.assertFalse(protofunctions.builtin(node.prototype('Wheel')))


class TestFieldsOnAPrototype(unittest.TestCase):
    def setUp(self):
        self.built = node.prototype('Wheel')

    def test_a_field_can_be_added_and_read_back(self):
        added = field.newField('radius', 'SFFloat', 1, 1.0)
        protofunctions.addField(self.built, added)
        self.assertIs(protofunctions.getField(self.built, 'radius'), added)

    def test_a_field_can_be_removed_by_name(self):
        protofunctions.addField(self.built, field.newField('radius', 'SFFloat', 1, 1.0))
        protofunctions.removeField(self.built, 'radius')
        with self.assertRaises(AttributeError):
            protofunctions.getField(self.built, 'radius')

    def test_a_field_can_be_removed_by_object(self):
        added = field.newField('radius', 'SFFloat', 1, 1.0)
        protofunctions.addField(self.built, added)
        protofunctions.removeField(self.built, added)
        with self.assertRaises(AttributeError):
            protofunctions.getField(self.built, 'radius')

    def test_asking_for_a_field_that_is_not_there_raises(self):
        with self.assertRaises(AttributeError):
            protofunctions.getField(self.built, 'nosuchfield')

    def test_a_field_stored_under_another_name_is_found_by_that_name(self):
        """A node's DEF is declared as `DEF` and stored as `' DEF'`, which
        is how a field keeps a name a program cannot write."""
        found = protofunctions.getField(basenodes.Transform, ' DEF')
        self.assertEqual(found.name, ' DEF')
        self.assertTrue(hasattr(found, 'fset'))

    def test_an_event_stored_under_another_name_is_found_too(self):
        declared = field.newEvent(' hidden', 'SFFloat')
        held = type('Held', (node.Node,), {'PROTO': 'Held',
                                           'hidden': declared})
        self.assertIs(protofunctions.getField(held, ' hidden'), declared)

    def test_a_set_prefix_finds_the_field_it_names(self):
        """VRML97 writes `set_translation` for the eventIn a field has."""
        self.assertIs(
            protofunctions.getField(basenodes.Transform, 'set_translation'),
            protofunctions.getField(basenodes.Transform, 'translation'))

    def test_a_changed_suffix_finds_it_as_well(self):
        self.assertIs(
            protofunctions.getField(basenodes.Transform,
                                    'translation_changed'),
            protofunctions.getField(basenodes.Transform, 'translation'))

    def test_a_name_nothing_declares_says_which_prototype(self):
        with self.assertRaises(AttributeError) as caught:
            protofunctions.getField(basenodes.Transform, 'nosuchfield')
        self.assertIn('Transform', str(caught.exception))
        self.assertIn('nosuchfield', str(caught.exception))

    def test_the_fields_of_a_node_include_the_ones_it_declares(self):
        declared = {f.name for f in protofunctions.getFields(basenodes.Transform)}
        self.assertIn('translation', declared)


class TestTheSceneGraphAndUrlOfAPrototype(unittest.TestCase):
    def setUp(self):
        self.built = node.prototype('Wheel')

    def test_a_scene_graph_is_set_read_and_deleted(self):
        graph = SceneGraph()
        protofunctions.setSceneGraph(self.built, graph)
        self.assertIs(protofunctions.getSceneGraph(self.built), graph)
        protofunctions.delSceneGraph(self.built)
        self.assertIsNot(protofunctions.getSceneGraph(self.built), graph)

    def test_an_external_url_is_set_read_and_deleted(self):
        """An EXTERNPROTO records where its definition came from."""
        protofunctions.setExternalURL(self.built, ['http://example.com/wheel.wrl'])
        self.assertEqual(list(protofunctions.getExternalURL(self.built)),
                         ['http://example.com/wheel.wrl'])
        protofunctions.delExternalURL(self.built)
        self.assertEqual(list(protofunctions.getExternalURL(self.built)), [])

    def test_a_prototype_with_no_url_answers_an_empty_list(self):
        self.assertEqual(list(protofunctions.getExternalURL(self.built)), [])


if __name__ == '__main__':
    unittest.main()


class TestWhatAnInstanceStandsFor(unittest.TestCase):
    """A prototype instance is used where its body's first node would be

    VRML97 4.8.3 and X3D 4.4.4: the instance has the type of that node, so
    it is read as that node wherever its own interface does not answer.
    """

    WORLD = (b'#X3D V3.3 utf8\nPROFILE Immersive\n'
             b'PROTO Wood [ inputOutput SFColor tint 1 0 0 ] {\n'
             b'  Appearance { material Material { diffuseColor IS tint } } }\n'
             b'PROTO Varnished [ ] { Wood { } }\n'
             b'PROTO Nothing [ ] { }\n'
             b'Shape { appearance Wood { tint 0 1 0 } geometry Box { } }\n'
             b'Shape { appearance Varnished { } }\n'
             b'Group { children Nothing { } }\n')

    def setUp(self):
        from vrml.x3d import readers  # noqa: PLC0415 kept with its use
        self.scene = readers.read(self.WORLD, encoding='classic')
        self.wood = self.scene.children[0].appearance
        self.varnished = self.scene.children[1].appearance
        self.nothing = self.scene.children[2].children[0]

    def test_the_body_s_first_node(self):
        appearance = protofunctions.stands_for(self.wood)
        self.assertEqual(type(appearance).__name__, 'Appearance')
        self.assertIs(protofunctions.stands_for(appearance), appearance)

    def test_through_an_instance_in_another_s_body(self):
        self.assertEqual(type(protofunctions.stands_for(self.varnished)).__name__, 'Appearance')

    def test_an_instance_with_no_body_stands_for_itself(self):
        self.assertIs(protofunctions.stands_for(self.nothing), self.nothing)
        with self.assertRaises(AttributeError):
            self.nothing.material  # noqa: B018 the read is what is tested

    def test_what_the_instance_lacks_is_read_from_that_node(self):
        material = self.wood.material
        self.assertEqual(type(material).__name__, 'Material')
        self.assertEqual(list(material.diffuseColor), [0, 1, 0])

    def test_its_own_interface_comes_first(self):
        self.assertEqual(list(self.wood.tint), [0, 1, 0])

    def test_a_name_neither_has(self):
        with self.assertRaises(AttributeError):
            self.wood.noSuchThing  # noqa: B018 the read is what is tested


class TestTheFieldsOfAClass(unittest.TestCase):
    """getFields answers from what the class holds now, however it changed"""

    def made(self):
        from vrml import field as fields, node  # noqa: PLC0415 kept with its use

        class Thing(node.Node):
            PROTO = 'Thing'
            size = fields.newField('size', 'SFFloat', 1, 1.0)
        return Thing, fields

    def names(self, cls):
        return sorted(item.name for item in protofunctions.getFields(cls) if not item.name.startswith(' '))

    def test_a_field_added_by_add_field(self):
        Thing, fields = self.made()
        self.assertIn('size', self.names(Thing))
        protofunctions.addField(Thing, fields.newField('weight', 'SFFloat', 1, 0.0))
        self.assertIn('weight', self.names(Thing))

    def test_a_field_set_on_the_class(self):
        Thing, fields = self.made()
        self.names(Thing)
        Thing.colour = fields.newField('colour', 'SFColor', 1, (1, 1, 1))
        self.assertIn('colour', self.names(Thing))

    def test_a_field_added_to_a_base_reaches_the_subclass(self):
        Thing, fields = self.made()

        class Other(Thing):
            pass
        self.names(Other)
        protofunctions.addField(Thing, fields.newField('weight', 'SFFloat', 1, 0.0))
        self.assertIn('weight', self.names(Other))

    def test_a_field_removed(self):
        Thing, _fields = self.made()
        self.names(Thing)
        protofunctions.removeField(Thing, 'size')
        self.assertNotIn('size', self.names(Thing))

    def test_a_field_replaced_through_add_field(self):
        Thing, fields = self.made()
        self.names(Thing)
        replacement = fields.newField('size', 'SFFloat', 1, 2.0)
        protofunctions.addField(Thing, replacement)
        found = [item for item in protofunctions.getFields(Thing) if item.name == 'size']
        self.assertIs(found[0], replacement)

    def test_the_answer_is_the_callers_to_change(self):
        Thing, _fields = self.made()
        protofunctions.getFields(Thing).clear()
        self.assertIn('size', self.names(Thing))
