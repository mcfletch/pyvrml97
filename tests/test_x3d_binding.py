"""X3D's bind stacks (ISO/IEC 19775-1, 7.2.2).

Each scene has a stack per kind of bindable node: viewpoints, backgrounds,
fogs and navigation infos. `set_bind TRUE` puts a node on top of its stack,
sending `isBound TRUE` and `bindTime` from it and `isBound FALSE` from the node
it covers; `set_bind FALSE` takes a node off, and the node it uncovers is
bound again. The node on top is the bound one.
"""

import unittest

from vrml.vrml97 import nodetypes
from vrml.x3d import binding, nodes
from vrml.x3d.scene import X3DScene


class ClockedScene(X3DScene):
    now = 5.0

    def clock(self):
        return self.now


def sent(node, name):
    return node.__dict__.get(name)


class BindCase(unittest.TestCase):
    def setUp(self):
        self.first = nodes.Viewpoint(description='first')
        self.second = nodes.Viewpoint(description='second')
        self.third = nodes.OrthoViewpoint(description='third')
        self.scene = ClockedScene(children=[self.first, self.second, self.third])


class TestBinding(BindCase):
    def test_binding_puts_a_node_on_top(self):
        self.first.set_bind = True
        self.assertIs(binding.bound(self.first), self.first)
        self.assertIs(sent(self.first, 'isBound'), True)
        self.assertEqual(sent(self.first, 'bindTime'), 5.0)

    def test_binding_another_unbinds_the_one_it_covers(self):
        self.first.set_bind = True
        self.second.set_bind = True
        self.assertIs(binding.bound(self.first), self.second)
        self.assertIs(sent(self.first, 'isBound'), False)
        self.assertIs(sent(self.second, 'isBound'), True)

    def test_unbinding_the_top_rebinds_the_one_beneath(self):
        self.first.set_bind = True
        self.second.set_bind = True
        self.scene.now = 9.0
        self.second.set_bind = False
        self.assertIs(binding.bound(self.first), self.first)
        self.assertIs(sent(self.second, 'isBound'), False)
        self.assertIs(sent(self.first, 'isBound'), True)
        self.assertEqual(sent(self.first, 'bindTime'), 9.0)

    def test_unbinding_a_node_beneath_the_top_sends_nothing(self):
        self.first.set_bind = True
        self.second.set_bind = True
        self.first.__dict__.pop('isBound')
        self.first.set_bind = False
        self.assertIsNone(sent(self.first, 'isBound'))
        self.second.set_bind = False
        self.assertIsNone(binding.bound(self.first))

    def test_binding_the_top_again_sends_nothing(self):
        self.first.set_bind = True
        self.scene.now = 7.0
        self.first.set_bind = True
        self.assertEqual(sent(self.first, 'bindTime'), 5.0)

    def test_binding_a_node_already_on_the_stack_moves_it_up(self):
        for node in (self.first, self.second, self.first):
            node.set_bind = True
        self.first.set_bind = False
        self.assertIs(binding.bound(self.first), self.second)

    def test_every_viewpoint_shares_one_stack(self):
        self.first.set_bind = True
        self.third.set_bind = True
        self.assertIs(sent(self.first, 'isBound'), False)

    def test_each_kind_has_its_own_stack(self):
        fog = nodes.Fog()
        background = nodes.TextureBackground()
        self.scene.children.extend([fog, background])
        for node in (self.first, fog, background):
            node.set_bind = True
        self.assertIs(binding.bound(self.first), self.first)
        self.assertIs(binding.bound(fog), fog)
        self.assertIs(binding.bound(self.scene, nodetypes.Background), background)

    def test_each_scene_has_its_own_stacks(self):
        other = nodes.Viewpoint()
        _scene = ClockedScene(children=[other])
        self.first.set_bind = True
        other.set_bind = True
        self.assertIs(sent(self.first, 'isBound'), True)
        self.assertIs(binding.bound(self.first), self.first)

    def test_a_node_in_no_scene_is_its_own_stack(self):
        loose = nodes.Viewpoint()
        loose.set_bind = True
        self.assertIs(binding.bound(loose), loose)
        loose.set_bind = False
        self.assertIsNone(binding.bound(loose))


class TestCurrent(BindCase):
    def test_with_none_bound_the_first_is_bound(self):
        found = binding.current([self.first, self.second])
        self.assertIs(found, self.first)
        self.assertIs(sent(self.first, 'isBound'), True)

    def test_the_bound_one_is_current(self):
        self.second.set_bind = True
        self.assertIs(binding.current([self.first, self.second]), self.second)

    def test_no_candidates_is_none(self):
        self.assertIsNone(binding.current([]))
        self.assertIsNone(binding.current_path([]))

    def test_the_path_to_the_current_node(self):
        paths = [(self.scene, self.first), (self.scene, self.second)]
        self.assertIs(binding.current_path(paths), paths[0])
        self.second.set_bind = True
        self.assertIs(binding.current_path(paths), paths[1])

    def test_a_bound_node_the_paths_miss_gives_way_to_the_first_path(self):
        self.third.set_bind = True
        paths = [(self.scene, self.first)]
        self.assertIs(binding.current_path(paths), paths[0])
        self.assertIs(binding.bound(self.first), self.first)

    def test_the_topmost_node_the_paths_reach_is_bound_again(self):
        """A Switch showing a node bound before shows it bound"""
        self.first.set_bind = True
        self.second.set_bind = True
        self.third.set_bind = True
        paths = [(self.scene, self.first)]
        self.assertIs(binding.current_path(paths), paths[0])
        self.assertIs(binding.bound(self.first), self.first)
        self.assertIs(sent(self.first, 'isBound'), True)


class TestVRML97(unittest.TestCase):
    def test_vrml97s_bindables_are_x3ds(self):
        from vrml.vrml97 import basenodes  # noqa: PLC0415 kept with its use
        for name in ('Viewpoint', 'Background', 'Fog', 'NavigationInfo'):
            self.assertTrue(issubclass(getattr(basenodes, name), binding.Bindable), name)


if __name__ == '__main__':
    unittest.main()
