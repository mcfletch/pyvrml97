"""Routes -- how one node's field feeds another's -- and the prototype helpers.

A ROUTE is VRML97's wiring: a change to a source field is forwarded to a
destination field on another node. `protofunctions` is the accessor set for the
things a node holds outside its own fields -- its prototype name, its DEF name,
the scene graph it belongs to, the URL an EXTERNPROTO came from.
"""

import unittest

from vrml import node, protofunctions, route
from vrml.vrml97 import basenodes
from vrml.vrml97.scenegraph import SceneGraph


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

    def test_a_value_the_destination_refuses_is_reported_not_raised(self):
        """A route runs inside a field notification, which has nobody to raise
        to, so a bad value is reported and the rest of the cascade goes on."""
        wired = route.ROUTE(self.source, 'translation',
                            self.destination, 'whichChoice')
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
        from vrml import copier
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
        from vrml import field
        added = field.newField('radius', 'SFFloat', 1, 1.0)
        protofunctions.addField(self.built, added)
        self.assertIs(protofunctions.getField(self.built, 'radius'), added)

    def test_a_field_can_be_removed_by_name(self):
        from vrml import field
        protofunctions.addField(self.built, field.newField('radius', 'SFFloat', 1, 1.0))
        protofunctions.removeField(self.built, 'radius')
        with self.assertRaises(AttributeError):
            protofunctions.getField(self.built, 'radius')

    def test_a_field_can_be_removed_by_object(self):
        from vrml import field
        added = field.newField('radius', 'SFFloat', 1, 1.0)
        protofunctions.addField(self.built, added)
        protofunctions.removeField(self.built, added)
        with self.assertRaises(AttributeError):
            protofunctions.getField(self.built, 'radius')

    def test_asking_for_a_field_that_is_not_there_raises(self):
        with self.assertRaises(AttributeError):
            protofunctions.getField(self.built, 'nosuchfield')

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
