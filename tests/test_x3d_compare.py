"""Comparing two scenes: the first place their graphs differ."""

import unittest

from vrml import protofunctions
from vrml.x3d import nodes as x3d
from vrml.x3d.compare import first_difference
from vrml.x3d.scene import X3DScene


def scene(*children, **fields):
    return X3DScene(children=list(children), **fields)


class TestFirstDifference(unittest.TestCase):
    def test_equal_graphs_have_none(self):
        self.assertIsNone(first_difference(
            scene(x3d.Transform(translation=(1, 2, 3), children=[x3d.Shape(geometry=x3d.Box())])),
            scene(x3d.Transform(translation=(1, 2, 3), children=[x3d.Shape(geometry=x3d.Box())])),
        ))

    def test_a_value_differs(self):
        found = first_difference(scene(x3d.Sphere(radius=1)), scene(x3d.Sphere(radius=2)))
        self.assertIn('children[0].radius', found)

    def test_a_node_type_differs(self):
        found = first_difference(scene(x3d.Sphere()), scene(x3d.Box()))
        self.assertIn('Sphere', found)
        self.assertIn('Box', found)

    def test_lists_of_different_lengths(self):
        found = first_difference(scene(x3d.Group(), x3d.Group()), scene(x3d.Group()))
        self.assertIn('children', found)

    def test_values_within_float32_precision_are_equal(self):
        self.assertIsNone(first_difference(
            scene(x3d.Transform(translation=(0.1, 0.2, 0.3))),
            scene(x3d.Transform(translation=(0.1000000001, 0.2, 0.3)))))

    def test_shared_nodes_must_be_shared_in_both(self):
        shape = x3d.Shape()
        shared = scene(x3d.Group(children=[shape, shape]))
        separate = scene(x3d.Group(children=[x3d.Shape(), x3d.Shape()]))
        self.assertIn('shared', first_difference(shared, separate))
        self.assertIsNone(first_difference(shared, scene(x3d.Group(children=[shape, shape]))))

    def test_the_header_is_compared(self):
        found = first_difference(scene(profile='Full'), scene(profile='Core'))
        self.assertIn('profile', found)

    def test_a_dag_is_compared_once_per_node(self):
        leaf = x3d.Shape()
        deep = leaf
        for _ in range(30):
            deep = x3d.Group(children=[deep, deep])
        self.assertIsNone(first_difference(scene(deep), scene(deep)))



class TestProgramSource(unittest.TestCase):
    """A Script's source inline (XML CDATA, sourceCode) and as an inline
    url (ClassicVRML's "ecmascript:...") are the same program."""

    def test_inline_source_and_an_inline_url_are_equal(self):
        cdata = x3d.Script(url=['script.js'], sourceCode='\necmascript:\nfunction f() {}\n')
        inline = x3d.Script(url=['ecmascript:\nfunction f() {}', 'script.js'])
        self.assertIsNone(first_difference(scene(cdata), scene(inline)))

    def test_different_programs_differ(self):
        found = first_difference(scene(x3d.Script(sourceCode='ecmascript: a')),
                                 scene(x3d.Script(url=['ecmascript: b'])))
        self.assertIn('source', found)


class TestIgnoring(unittest.TestCase):
    def test_a_named_field_is_not_compared(self):
        left = scene(x3d.FontStyle(style='BOLD'))
        right = scene(x3d.FontStyle())
        self.assertIsNotNone(first_difference(left, right))
        self.assertIsNone(first_difference(left, right, ignore=[('FontStyle', 'style')]))


class TestWhatIsCompared(unittest.TestCase):
    def test_times_are_compared_at_double_precision(self):
        found = first_difference(scene(x3d.TimeSensor(startTime=1.7e9 + 0.25)),
                                 scene(x3d.TimeSensor(startTime=1.7e9)))
        self.assertIn('startTime', found)

    def test_a_prototypes_interface_is_compared(self):
        from vrml.x3d import files  # noqa: PLC0415 kept with its use
        text = '#X3D V4.0 utf8\nPROFILE Immersive\nPROTO P [ initializeOnly SFFloat r %s ] { Group {} }\n'
        found = first_difference(files.loads(text % '1'), files.loads(text % '2'))
        self.assertIn('P', found)

    def test_a_prototype_field_declared_without_a_value_equals_one_declared_empty(self):
        from vrml.x3d import files  # noqa: PLC0415 kept with its use
        text = '#X3D V4.0 utf8\nPROFILE Immersive\nPROTO P [ inputOutput MFVec3f v %s ] { Group {} }\n'
        self.assertIsNone(first_difference(files.loads(text % ''), files.loads(text % '[ ]')))
        self.assertIn('P', first_difference(files.loads(text % ''), files.loads(text % '[ 0 0 0 ]')))

    def test_a_body_scripts_url_given_by_is_is_not_compared(self):
        from vrml.x3d import files  # noqa: PLC0415 kept with its use
        text = ('#X3D V4.0 utf8\nPROFILE Immersive\n'
                'PROTO P [ inputOutput MFString u [] ] { Script { url %s url IS u } }\n')
        self.assertIsNone(first_difference(files.loads(text % '"a.js"'), files.loads(text % '[]')))

    def test_a_prototypes_body_is_compared(self):
        from vrml.x3d import files  # noqa: PLC0415 kept with its use
        text = '#X3D V4.0 utf8\nPROFILE Immersive\nPROTO P [ ] { %s {} }\n'
        found = first_difference(files.loads(text % 'Group'), files.loads(text % 'Transform'))
        self.assertIn('P', found)

    def test_a_body_field_given_by_is_is_not_compared_and_the_connection_is(self):
        from vrml.x3d import files  # noqa: PLC0415 kept with its use
        text = ('#X3D V4.0 utf8\nPROFILE Immersive\n'
                'PROTO P [ initializeOnly SFFloat r 1 ] { Sphere { radius %s } }\n')
        connected = files.loads(text % 'IS r')
        protofunctions.getSceneGraph(connected.protoTypes['P']).children[0].radius = 5.0
        self.assertIsNone(first_difference(connected, files.loads(text % 'IS r')))
        self.assertIn('P', first_difference(connected, files.loads(text % '1')))

    def test_routes_between_unnamed_nodes_are_compared_by_node(self):
        def routed(which):
            clocks, light = [x3d.TimeSensor(), x3d.TimeSensor(loop=True)], x3d.PointLight()
            made = scene(clocks[0], clocks[1], light)
            made.addRoute(clocks[which], 'isActive', light, 'on')
            return made
        self.assertIsNone(first_difference(routed(0), routed(0)))
        self.assertIn('routes', first_difference(routed(0), routed(1)))


if __name__ == '__main__':
    unittest.main()
