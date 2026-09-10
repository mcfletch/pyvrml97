"""The scene graph: what it holds, and the ways of wiring something into it.

A scene graph is a node like any other, with a list of children -- and beside
that it is the namespace a file's names live in: the DEF names, the
prototypes, and the routes. Those three are what a parser fills in and what a
program asks back, so each has an accessor with several shapes.

`tests/test_routes_and_protofunctions.py` covers a ROUTE on its own;
`tests/test_linearise.py` covers writing a graph back out.
"""

import gc
import unittest

from vrml import copier as copiermodule
from vrml import node, protofunctions, route
from vrml.vrml97 import basenodes
from vrml.vrml97.scenegraph import SceneGraph


class Clock(basenodes.TimeSensor):
    """A source to route from, named for what it is used as here."""


class TestWhatAGraphStartsWith(unittest.TestCase):
    def test_it_has_no_children(self):
        self.assertEqual(len(SceneGraph().children), 0)

    def test_it_has_no_names_no_protos_and_no_routes(self):
        """An unnamed node registers no name, so a fresh graph's namespace
        is empty rather than holding the graph itself under the empty
        string."""
        scene = SceneGraph()
        self.assertEqual(len(scene.defNames), 0)
        self.assertEqual(len(scene.protoTypes), 0)
        self.assertEqual(len(scene.routes), 0)

    def test_children_may_be_given_to_it(self):
        child = basenodes.Group()
        self.assertEqual(list(SceneGraph(children=[child]).children), [child])

    def test_it_is_its_own_scene_root(self):
        """Which is what makes a node put into it reachable from anything
        else in it."""
        scene = SceneGraph()
        self.assertIs(protofunctions.root(scene), scene)

    def test_a_node_put_into_it_takes_that_root(self):
        child = basenodes.Group()
        scene = SceneGraph(children=[child])
        self.assertIs(protofunctions.root(child), scene)


class TestNamesInIt(unittest.TestCase):
    """`DEF` gives a node a name, and the graph is where the name is looked
    up."""

    def setUp(self):
        self.scene = SceneGraph()
        self.node = basenodes.Group()

    def test_a_name_reads_back(self):
        self.scene.regDefName('Shared', self.node)
        self.assertIs(self.scene.getDEF('Shared'), self.node)

    def test_the_node_knows_its_own_name(self):
        self.scene.regDefName('Shared', self.node)
        self.assertEqual(protofunctions.defName(self.node), 'Shared')

    def test_a_name_nothing_took_is_not_there(self):
        self.assertIsNone(self.scene.getDEF('Nobody'))

    def test_renaming_a_node_gives_up_its_old_name(self):
        self.scene.regDefName('First', self.node)
        self.scene.regDefName('Second', self.node)
        self.assertIsNone(self.scene.getDEF('First'))
        self.assertIs(self.scene.getDEF('Second'), self.node)

    def test_a_name_another_node_holds_is_left_alone(self):
        """Only the node's own previous name is given up, so that two nodes
        renaming past each other do not lose the other's entry."""
        other = basenodes.Group()
        self.scene.regDefName('Shared', other)
        protofunctions.defName(self.node, 'Shared')
        self.scene.regDefName('Mine', self.node)
        self.assertIs(self.scene.getDEF('Shared'), other)


class TestPrototypesInIt(unittest.TestCase):
    def prototype(self, name='Wheel'):
        return node.prototype(name)

    def test_one_added_reads_back_by_name(self):
        scene, built = SceneGraph(), self.prototype()
        scene.addProto(built)
        self.assertIs(scene.getProto('Wheel'), built)

    def test_one_nobody_declared_is_not_there(self):
        self.assertIsNone(SceneGraph().getProto('Wheel'))

    def test_an_inner_graph_finds_an_outer_ones_prototype(self):
        """A PROTO's body is a graph of its own, and what it names has to
        reach the file's declarations."""
        outer, built = SceneGraph(), self.prototype()
        outer.addProto(built)
        self.assertIs(SceneGraph(root=outer).getProto('Wheel'), built)

    def test_its_own_declaration_wins_over_the_outer_one(self):
        outer, inner = SceneGraph(), None
        outer.addProto(self.prototype())
        inner = SceneGraph(root=outer)
        mine = self.prototype()
        inner.addProto(mine)
        self.assertIs(inner.getProto('Wheel'), mine)

    def test_an_outer_graph_that_has_gone_away_is_no_longer_asked(self):
        """The reference upward is weak, so an inner graph does not keep the
        file it came from alive."""
        outer = SceneGraph()
        outer.addProto(self.prototype())
        inner = SceneGraph(root=outer)
        del outer
        gc.collect()
        self.assertIsNone(inner.getProto('Wheel'))


class TestWiringSomethingIn(unittest.TestCase):
    """`addRoute` takes a ROUTE, the four names of one, or a source and
    something to call."""

    def setUp(self):
        self.scene = SceneGraph()
        self.clock = Clock()
        self.mover = basenodes.Transform()
        self.scene.regDefName('Clock', self.clock)
        self.scene.regDefName('Mover', self.mover)

    def test_a_route_object_is_kept(self):
        wired = route.ROUTE(source=self.clock, sourceField='fraction_changed',
                            destination=self.mover,
                            destinationField='set_translation')
        self.assertIs(self.scene.addRoute(wired), wired)
        self.assertEqual(list(self.scene.routes), [wired])

    def test_four_nodes_and_fields_build_one(self):
        wired = self.scene.addRoute((self.clock, 'fraction_changed',
                                     self.mover, 'set_translation'))
        self.assertIs(wired.source, self.clock)
        self.assertEqual(wired.destinationField, 'set_translation')

    def test_the_four_may_be_given_as_arguments_rather_than_a_tuple(self):
        wired = self.scene.addRoute(self.clock, 'fraction_changed',
                                    self.mover, 'set_translation')
        self.assertIs(wired.destination, self.mover)

    def test_the_ends_may_be_named_by_their_def_names(self):
        """Which is how a parser wires a file: the names are all it has."""
        wired = self.scene.addRoute(
            ('Clock', 'fraction_changed', 'Mover', 'set_translation'))
        self.assertIs(wired.source, self.clock)
        self.assertIs(wired.destination, self.mover)

    def test_routes_may_be_given_when_the_graph_is_built(self):
        scene = SceneGraph(routes=[
            (self.clock, 'fraction_changed', self.mover, 'set_translation')])
        self.assertEqual(len(scene.routes), 1)


class TestWiringSomethingToAFunction(unittest.TestCase):
    """A three-part route ends at a callable rather than another field,
    which is how a program watches a scene for changes."""

    def setUp(self):
        self.scene = SceneGraph()
        self.node = basenodes.Transform()
        self.scene.regDefName('Mover', self.node)
        self.told = []

    def receiver(self, signal, sender, **named):
        self.told.append(signal[0])

    def test_a_change_reaches_it(self):
        self.scene.addRoute((self.node, 'translation', self.receiver))
        self.node.translation = (1, 2, 3)
        self.assertEqual(self.told, ['set'])

    def test_a_deletion_reaches_it_too(self):
        self.scene.addRoute((self.node, 'translation', self.receiver))
        self.node.translation = (1, 2, 3)
        del self.node.translation
        self.assertEqual(self.told, ['set', 'del'])

    def test_the_source_may_be_named_by_its_def_name(self):
        self.scene.addRoute(('Mover', 'translation', self.receiver))
        self.node.translation = (1, 2, 3)
        self.assertEqual(self.told, ['set'])

    def test_something_that_cannot_be_called_is_refused(self):
        with self.assertRaises(TypeError):
            self.scene.addRoute((self.node, 'translation', 'not callable'))


class TestCopyingAGraph(unittest.TestCase):
    def test_the_children_come_with_it(self):
        scene = SceneGraph(children=[basenodes.Transform(
            translation=(1, 2, 3))])
        copied = scene.copy()
        self.assertEqual(len(copied.children), 1)
        self.assertIsNot(copied.children[0], scene.children[0])
        self.assertEqual(list(copied.children[0].translation), [1.0, 2.0, 3.0])

    def test_the_names_come_with_it_and_point_at_the_copies(self):
        scene = SceneGraph()
        held = basenodes.Transform()
        scene.children.append(held)
        scene.regDefName('Shared', held)
        copied = scene.copy()
        self.assertIn('Shared', copied.defNames)
        self.assertIs(copied.getDEF('Shared'), copied.children[0])

    def test_an_empty_name_is_not_carried_over(self):
        scene = SceneGraph()
        scene.defNames[''] = basenodes.Transform()
        scene.defNames['Missing'] = None
        self.assertEqual(len(scene.copy().defNames), 0)

    def test_the_prototypes_come_with_it(self):
        scene = SceneGraph()
        built = node.prototype('Wheel')
        scene.addProto(built)
        self.assertIs(scene.copy().getProto('Wheel'), built)

    def test_it_says_so_rather_than_copying_a_prototype(self):
        """A prototype is a node class, and building a second one with the
        same body is not something the copier does."""
        scene = SceneGraph()
        scene.addProto(node.prototype('Wheel'))
        with self.assertRaises(NotImplementedError) as caught:
            scene.copy(copiermodule.Copier(shareProtos=0))
        self.assertIn('Wheel', str(caught.exception))

    def test_a_graph_with_no_prototypes_copies_either_way(self):
        scene = SceneGraph(children=[basenodes.Group()])
        copied = scene.copy(copiermodule.Copier(shareProtos=0))
        self.assertEqual(len(copied.children), 1)


if __name__ == '__main__':
    unittest.main()
