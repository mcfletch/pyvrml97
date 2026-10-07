"""The time a node's world is at: its scene's clock.

X3D's nodes that stamp or measure time -- a TimeTrigger, a follower, a
bindable's bindTime -- ask `vrml.x3d.timing.now_for(node)`, which reads the
`clock` of the scene the node is in, so an engine whose frames run on a clock
of its own gives that clock to its scenes. A node in no scene with a clock
has `timing.clock`.
"""

import unittest

from vrml import protofunctions
from vrml.x3d import nodes, timing
from vrml.x3d.scene import X3DScene


class ClockedScene(X3DScene):
    def clock(self):
        return 42.0


class TestNowFor(unittest.TestCase):
    def test_a_node_in_a_scene_with_a_clock_has_the_scenes_time(self):
        made = nodes.Group()
        scene = ClockedScene(children=[made])
        self.assertIs(protofunctions.root(made), scene)
        self.assertEqual(timing.now_for(made), 42.0)

    def test_a_node_in_no_scene_has_the_default_clock(self):
        saved = timing.clock
        timing.clock = lambda: 7.0
        try:
            self.assertEqual(timing.now_for(nodes.Group()), 7.0)
        finally:
            timing.clock = saved

    def test_a_scene_without_a_clock_has_the_default_clock(self):
        made = nodes.Group()
        X3DScene(children=[made])
        saved = timing.clock
        timing.clock = lambda: 8.0
        try:
            self.assertEqual(timing.now_for(made), 8.0)
        finally:
            timing.clock = saved


if __name__ == '__main__':
    unittest.main()
