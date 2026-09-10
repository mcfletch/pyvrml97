"""Colour names, the IS-map, node paths and prototype namespaces.

Small pieces that carry more than their size suggests: a colour written as a
name or as `#rrggbb` is what a VRML97 file most often holds, and a node path
is what the event system hands a handler.
"""

import unittest

from vrml import arrays, csscolors, nodepath, protonamespace
from vrml.vrml97.basenodes import Transform


class TestReadingAColour(unittest.TestCase):
    def test_every_name_it_knows_reads_back(self):
        for name, value in csscolors.cssColors.items():
            self.assertEqual(csscolors.stringToColor(name), value, name)

    def test_every_name_survives_a_trip_through_hex(self):
        for _name, value in csscolors.cssColors.items():
            written = '#%02x%02x%02x' % tuple(map(csscolors.toInt, value))
            self.assertTrue(
                arrays.allclose(csscolors.stringToColor(written), value, 0.001),
                '%r read back as %r' % (value, csscolors.stringToColor(written)))

    def test_a_name_is_read_whatever_its_case(self):
        self.assertEqual(csscolors.stringToColor('ReD'),
                         csscolors.stringToColor('red'))

    def test_hex_white_and_black(self):
        self.assertEqual(csscolors.stringToColor('#ffffff'), (1.0, 1.0, 1.0))
        self.assertEqual(csscolors.stringToColor('#000000'), (0.0, 0.0, 0.0))

    def test_hex_reads_the_channels_in_order(self):
        self.assertEqual(csscolors.stringToColor('#ff0000'), (1.0, 0.0, 0.0))
        self.assertEqual(csscolors.stringToColor('#00ff00'), (0.0, 1.0, 0.0))
        self.assertEqual(csscolors.stringToColor('#0000ff'), (0.0, 0.0, 1.0))

    def test_a_name_it_does_not_know_says_so(self):
        with self.assertRaises(ValueError):
            csscolors.stringToColor('nosuchcolour')

    def test_an_empty_string_says_so(self):
        with self.assertRaises(ValueError):
            csscolors.stringToColor('')

    def test_a_byte_and_a_fraction_are_inverses(self):
        for byte in (0, 1, 127, 128, 254, 255):
            self.assertEqual(csscolors.toInt(csscolors.toFloat(byte)), byte)


class TestTheIsMapMapping(unittest.TestCase):
    """`node.ISMAPS` records which prototype field each node field is wired to.

    Keyed weakly on the node, so an entry cannot keep a scene graph alive
    after the graph itself is gone.
    """

    def test_it_starts_empty(self):
        from vrml import node as node_module
        self.assertIsInstance(len(node_module.ISMAPS), int)

    def test_a_node_gets_its_own_map(self):
        from vrml import node as node_module
        transform = Transform()
        first = node_module.ISMAPS.setdefault(transform, {})
        first['translation'] = 'protoTranslation'
        self.assertEqual(node_module.ISMAPS[transform],
                         {'translation': 'protoTranslation'})

    def test_two_nodes_do_not_share_one(self):
        from vrml import node as node_module
        one, other = Transform(), Transform()
        node_module.ISMAPS.setdefault(one, {})['a'] = 1
        self.assertEqual(node_module.ISMAPS.setdefault(other, {}), {})

    def test_an_entry_goes_when_its_node_does(self):
        from vrml import node as node_module
        transform = Transform()
        node_module.ISMAPS.setdefault(transform, {})['a'] = 1
        before = len(node_module.ISMAPS)
        del transform
        self.assertLess(len(node_module.ISMAPS), before)


class TestNodePathBasics(unittest.TestCase):
    def setUp(self):
        self.first = Transform(DEF='first')
        self.second = Transform(DEF='second')
        self.path = nodepath.NodePath([self.first, self.second])

    def test_its_representation_names_its_class(self):
        self.assertIn('NodePath', repr(self.path))

    def test_its_string_form_joins_the_nodes(self):
        self.assertIn('->', str(self.path))

    def test_a_path_and_itself_share_the_whole_of_it(self):
        self.assertEqual(list(self.path.common(self.path)),
                         [self.first, self.second])

    def test_two_paths_share_their_root(self):
        other = nodepath.NodePath([self.first, Transform(DEF='third')])
        self.assertEqual(list(self.path.common(other)), [self.first])

    def test_paths_with_no_root_in_common_share_nothing(self):
        other = nodepath.NodePath([Transform(DEF='other')])
        self.assertEqual(list(self.path.common(other)), [])

    def test_adding_a_node_extends_the_path(self):
        third = Transform(DEF='third')
        self.assertEqual(list(self.path + [third]),
                         [self.first, self.second, third])

    def test_adding_a_bare_node_extends_it_too(self):
        third = Transform(DEF='third')
        self.assertEqual(list(self.path + third),
                         [self.first, self.second, third])

    def test_two_paths_over_the_same_nodes_are_equal(self):
        self.assertTrue(self.path == nodepath.NodePath([self.first, self.second]))

    def test_paths_of_different_lengths_are_not(self):
        self.assertFalse(self.path == nodepath.NodePath([self.first]))

    def test_paths_over_different_nodes_are_not(self):
        other = nodepath.NodePath([self.first, Transform(DEF='third')])
        self.assertFalse(self.path == other)


class TestProtoNamespace(unittest.TestCase):
    def test_a_prototype_is_reached_as_an_attribute(self):
        namespace = protonamespace.ProtoNamespace({'Wheel': Transform})
        self.assertIs(namespace.Wheel, Transform)

    def test_a_name_it_does_not_hold_raises(self):
        namespace = protonamespace.ProtoNamespace()
        with self.assertRaises(AttributeError):
            _found = namespace.NoSuchProto

    def test_the_error_names_the_class_and_the_attribute(self):
        namespace = protonamespace.ProtoNamespace()
        with self.assertRaises(AttributeError) as caught:
            _found = namespace.NoSuchProto
        self.assertIn('ProtoNamespace', str(caught.exception))
        self.assertIn('NoSuchProto', str(caught.exception))

    def test_asking_for_contains_does_not_go_through_the_mapping(self):
        """It is what `in` uses, so answering a prototype for it would loop."""
        namespace = protonamespace.ProtoNamespace({'__contains__': Transform})
        with self.assertRaises(AttributeError):
            namespace.__getattr__('__contains__')


if __name__ == '__main__':
    unittest.main()
