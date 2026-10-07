"""The event cascade: a field receives one event per cascade.

A route ending at an input event calls that node's handler, whose outputs go
on along their own routes, all within the cascade the first event began
(ISO/IEC 19775-1, 4.4.8.3). A field already reached in the cascade is not
reached again, so routes that loop through nodes' behaviour end.
"""

import unittest

from vrml.route import ROUTE
from vrml.x3d import runtime
from vrml.x3d.scene import X3DScene


class TestLoops(unittest.TestCase):
    def test_a_loop_through_two_nodes_behaviour_ends(self):
        first, second = runtime.BooleanFilter(), runtime.BooleanFilter()
        _scene = X3DScene(children=[first, second])
        routes = [ROUTE(first, 'inputNegate', second, 'set_boolean'),
                  ROUTE(second, 'inputNegate', first, 'set_boolean')]
        first.set_boolean = True
        self.assertIs(first.__dict__['inputNegate'], False)
        self.assertIs(second.__dict__['inputNegate'], True)
        self.assertEqual(len(routes), 2)

    def test_separate_cascades_each_reach_the_field(self):
        source, target = runtime.BooleanToggle(), runtime.BooleanFilter()
        _scene = X3DScene(children=[source, target])
        _route = ROUTE(source, 'toggle_changed', target, 'set_boolean')
        source.set_boolean = True
        self.assertIs(target.__dict__['inputTrue'], True)
        source.set_boolean = True
        self.assertIs(target.__dict__['inputFalse'], False)


if __name__ == '__main__':
    unittest.main()
