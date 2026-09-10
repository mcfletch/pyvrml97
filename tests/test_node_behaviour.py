"""A node: how it is built, what it says about itself, and what it holds.

A node is built from named arguments -- the fields its prototype declares, and
nothing else -- and what it refuses says which name it did not recognise. The
node-valued fields beside that are what make a scene a graph: an SFNode holds
one node, an MFNode a list of them, and each passes the scene root down as it
is filled so that anything put into a scene can reach the file it is in.

`tests/test_node_definitions.py` covers declaring a node type;
`tests/test_field_assignment.py` covers assigning to one;
`tests/test_copying.py` covers copying one.
"""

import unittest

from vrml import node, protofunctions
from vrml.vrml97 import basenodes
from vrml.vrml97.scenegraph import SceneGraph


class TestBuildingOne(unittest.TestCase):
    def test_a_declared_field_may_be_given(self):
        built = basenodes.Transform(translation=(1, 2, 3))
        self.assertEqual(list(built.translation), [1.0, 2.0, 3.0])

    def test_a_def_name_may_be_given(self):
        self.assertEqual(protofunctions.defName(
            basenodes.Transform(DEF='Shared')), 'Shared')

    def test_a_name_it_does_not_declare_says_which_one(self):
        with self.assertRaises(AttributeError) as caught:
            basenodes.Transform(nosuchfield=1)
        self.assertIn('nosuchfield', str(caught.exception))
        self.assertIn('Transform', str(caught.exception))

    def test_a_name_that_is_not_a_field_says_so(self):
        """A method is reachable by name and is not something to set."""

        class Odd(node.Node):
            PROTO = 'Odd'

            def method(self):
                return None

        with self.assertRaises(TypeError) as caught:
            Odd(method=1)
        self.assertIn('method', str(caught.exception))

    def test_a_value_the_field_refuses_is_refused(self):
        with self.assertRaises(ValueError):
            basenodes.Transform(translation='not a vector')


class TestWhatANodeSaysAboutItself(unittest.TestCase):
    def test_an_unnamed_one_names_its_type(self):
        self.assertIn('Transform', str(basenodes.Transform()))

    def test_a_named_one_says_its_name(self):
        self.assertIn("'Shared'", str(basenodes.Transform(DEF='Shared')))

    def test_its_representation_lists_the_values_that_were_set(self):
        text = repr(basenodes.Transform(translation=(1, 2, 3)))
        self.assertIn('translation', text)
        self.assertIn('Transform', text)

    def test_a_value_that_was_not_set_is_not_listed(self):
        self.assertNotIn('scale', repr(basenodes.Transform()))

    def test_a_child_node_is_named_rather_than_written_out(self):
        """A node's representation would otherwise be the whole graph
        below it."""
        text = repr(basenodes.Shape(geometry=basenodes.Sphere(radius=2.0)))
        self.assertIn('Sphere(', text)
        self.assertNotIn('radius', text)


class TestTheNullNode(unittest.TestCase):
    """NULL is what an SFNode holds when it holds nothing."""

    def test_it_is_false(self):
        self.assertFalse(node.NULL)

    def test_it_is_written_as_the_word(self):
        self.assertEqual(str(node.NULL), 'NULL')

    def test_its_representation_says_what_it_is(self):
        self.assertIn('NULL', repr(node.NULL))

    def test_a_copy_of_it_is_itself(self):
        self.assertIs(node.NULL.clone(), node.NULL)

    def test_it_equals_another_null(self):
        self.assertEqual(node.NULL, node.NullNode())

    def test_comparing_it_to_something_that_is_not_a_node_says_so(self):
        self.assertNotEqual(node.NULL, 42)

    def test_it_can_be_a_key(self):
        """A copier keeps the nodes it has copied in a dictionary, and NULL
        turns up in one wherever a node field is empty."""
        self.assertEqual({node.NULL: 'kept'}[node.NullNode()], 'kept')

    def test_copying_a_field_that_holds_it_answers_it_again(self):
        self.assertIs(node.SFNode('geometry', 1, node.NULL)
                      .copyValue(node.NULL), node.NULL)

    def test_copying_a_node_without_a_copier_makes_one(self):
        held = basenodes.Sphere(radius=2.0)
        copied = node.SFNode('geometry', 1, node.NULL).copyValue(held)
        self.assertIsNot(copied, held)
        self.assertAlmostEqual(copied.radius, 2.0, places=5)


class TestASingleNodeField(unittest.TestCase):
    def field(self):
        return node.SFNode('geometry', 1, node.NULL)

    def test_a_node_is_taken(self):
        held = basenodes.Sphere()
        self.assertIs(self.field().coerce(held), held)

    def test_nothing_becomes_null(self):
        self.assertIs(self.field().coerce(None), node.NULL)

    def test_a_list_of_one_is_that_one(self):
        held = basenodes.Sphere()
        self.assertIs(self.field().coerce([held]), held)

    def test_a_lazy_sequence_is_drawn_out_first(self):
        """A map or a zip has no length until the values are taken from it."""
        held = basenodes.Sphere()
        self.assertIs(self.field().coerce(map(lambda each: each, [held])),
                      held)

    def test_a_string_is_refused_and_says_why(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce('Sphere')
        self.assertIn('string', str(caught.exception))

    def test_something_that_is_not_a_node_says_what_was_needed(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(42)
        self.assertIn('Node', str(caught.exception))

    def test_an_unrestricted_field_takes_anything(self):
        """A field that names no required types is what a Script's fields
        are, and it holds whatever it is given."""
        declared = node.SFNode('anything', 1, node.NULL)
        declared.requiredTypes = ()
        given = object()
        self.assertIs(declared.coerce(given), given)

    def test_the_scene_root_reaches_what_is_put_in_it(self):
        scene = SceneGraph()
        shape = basenodes.Shape()
        scene.children.append(shape)
        geometry = basenodes.Sphere()
        shape.geometry = geometry
        self.assertIs(protofunctions.root(geometry), scene)


class TestAListOfNodesField(unittest.TestCase):
    def field(self):
        return node.MFNode('children', 1, list)

    def test_a_single_node_becomes_a_list_of_one(self):
        held = basenodes.Group()
        self.assertEqual(list(self.field().coerce(held)), [held])

    def test_nothing_is_an_empty_list(self):
        self.assertEqual(len(self.field().coerce(None)), 0)

    def test_a_sequence_is_taken_node_by_node(self):
        held = [basenodes.Group(), basenodes.Group()]
        self.assertEqual(list(self.field().coerce(held)), held)

    def test_something_that_is_neither_says_which_field(self):
        with self.assertRaises(ValueError) as caught:
            self.field().coerce(42)
        self.assertIn('children', str(caught.exception))

    def test_the_scene_root_reaches_everything_put_in_it(self):
        scene = SceneGraph()
        group = basenodes.Group()
        scene.children.append(group)
        child = basenodes.Shape()
        group.children = [child]
        self.assertIs(protofunctions.root(child), scene)


class TestPassingTheSceneRootDown(unittest.TestCase):
    """Setting a node's scene root walks what it holds, so that a subtree
    attached in one go all learns which file it is in. What it walks is a
    scene as a program may have left it, so each step answers for what it
    finds rather than for what it expects."""

    def test_a_field_that_cannot_answer_is_passed_over(self):
        """A node field can refuse its own default -- a restricted one that
        does not allow NULL has nothing to answer with."""

        class Restricted(node.Node):
            PROTO = 'Restricted'
            held = node.SFNode('held', 1, None)

        Restricted.held.allowNULL = 0
        Restricted.held.requiredTypes = (basenodes.Group,)
        scene = SceneGraph()
        held = Restricted()
        scene.children.append(held)
        self.assertIs(protofunctions.root(held), scene)

    def test_a_root_that_is_not_a_scene_graph_registers_no_names(self):
        """`root` takes whatever it is given, and only a scene graph has a
        namespace to put a DEF name in."""
        held = basenodes.Transform(DEF='Shared')
        other = basenodes.Group()
        protofunctions.root(held, other)
        self.assertIs(protofunctions.root(held), other)


class TestDeclaringAPrototype(unittest.TestCase):
    """`node.prototype` builds the class a PROTO declaration stands for."""

    def test_it_is_named_for_the_prototype(self):
        built = node.prototype('Wheel')
        self.assertEqual(protofunctions.protoName(built), 'Wheel')

    def test_the_fields_it_is_given_are_declared_on_it(self):
        from vrml import fieldtypes

        built = node.prototype('Wheel', [fieldtypes.SFFloat('radius', 1, 1.0)])
        self.assertAlmostEqual(built().radius, 1.0, places=5)

    def test_a_body_may_be_given(self):
        body = SceneGraph(children=[basenodes.Group()])
        built = node.prototype('Wheel', sceneGraph=body)
        self.assertIsNotNone(protofunctions.getSceneGraph(built))

    def test_a_url_may_be_given(self):
        built = node.prototype('Wheel', externalURL=['wheel.wrl'])
        self.assertEqual(list(protofunctions.getExternalURL(built)),
                         ['wheel.wrl'])

    def test_an_instance_of_one_with_no_body_still_has_a_scene_graph(self):
        """Instantiating is what fills the body in, and a prototype declared
        with none gets an empty one rather than failing."""
        self.assertEqual(len(node.prototype('Wheel')().scenegraph.children), 0)


class TestWhatAPrototypeInstanceRenders(unittest.TestCase):
    """`renderedChildren` is what a renderer walks into: the body the
    instance was built with."""

    def instance(self):
        body = SceneGraph(children=[basenodes.Shape(), basenodes.Group()])
        return node.prototype('Wheel', sceneGraph=body)()

    def test_it_is_the_body_it_was_built_with(self):
        self.assertEqual(len(self.instance().renderedChildren()), 2)

    def test_it_may_be_asked_for_one_kind(self):
        found = self.instance().renderedChildren(basenodes.Shape)
        self.assertEqual(len(found), 1)
        self.assertIsInstance(found[0], basenodes.Shape)


if __name__ == '__main__':
    unittest.main()
