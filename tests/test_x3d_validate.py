"""Validating a scene against the X3D model: ranges, enumerations, and the
components its profile and COMPONENT statements allow."""

import unittest

from vrml.x3d import nodes as x3d
from vrml.x3d.scene import ComponentInfo, X3DScene
from vrml.x3d.validate import validate


def messages(problems):
    return [p.message for p in problems]


class TestValues(unittest.TestCase):
    def test_a_valid_scene_has_no_problems(self):
        scene = X3DScene(profile='Interchange', children=[
            x3d.Shape(appearance=x3d.Appearance(material=x3d.Material(transparency=0.5)),
                      geometry=x3d.Sphere(radius=2)),
        ])
        self.assertEqual(validate(scene), [])

    def test_a_value_below_its_minimum(self):
        found = validate(X3DScene(children=[x3d.Shape(geometry=x3d.Sphere(radius=-1))]))
        self.assertEqual(len(found), 1)
        self.assertIn('Sphere.radius', found[0].message)
        self.assertIsInstance(found[0].node, x3d.Sphere)

    def test_an_exclusive_minimum(self):
        # Sphere.radius is (0, inf): zero is outside.
        self.assertEqual(len(validate(X3DScene(children=[
            x3d.Shape(geometry=x3d.Sphere(radius=0))]))), 1)

    def test_each_component_of_a_vector_is_held_to_the_range(self):
        material = x3d.PhysicalMaterial()
        material.__dict__['baseColor'] = material.baseColor * 2
        found = validate(X3DScene(children=[x3d.Shape(
            appearance=x3d.Appearance(material=material))]))
        self.assertIn('PhysicalMaterial.baseColor', messages(found)[0])

    def test_a_value_outside_a_closed_enumeration(self):
        found = validate(X3DScene(children=[x3d.Shape(
            appearance=x3d.Appearance(alphaMode='SOMETIMES'))]))
        self.assertIn('Appearance.alphaMode', messages(found)[0])

    def test_an_open_enumeration_takes_other_values(self):
        self.assertEqual(validate(X3DScene(children=[x3d.NavigationInfo(type=['HOVER'])])), [])

    def test_a_list_enumeration_checks_each_entry(self):
        found = validate(X3DScene(children=[x3d.Shape(geometry=x3d.Text(
            fontStyle=x3d.FontStyle(justify=['MIDDLE', 'NOWHERE'])))]))
        self.assertIn('FontStyle.justify', messages(found)[0])

    def test_a_shared_node_is_reported_once(self):
        sphere = x3d.Sphere(radius=-1)
        found = validate(X3DScene(children=[x3d.Shape(geometry=sphere),
                                            x3d.Shape(geometry=sphere)]))
        self.assertEqual(len(found), 1)


class TestComponents(unittest.TestCase):
    def test_a_node_outside_the_profile(self):
        found = validate(X3DScene(profile='Interchange', children=[x3d.TouchSensor()]))
        self.assertEqual(messages(found),
                         ['TouchSensor needs PointingDeviceSensor level 1, '
                          'which profile Interchange and the COMPONENT statements do not give'])

    def test_a_component_statement_adds_to_the_profile(self):
        scene = X3DScene(profile='Interchange', children=[x3d.TouchSensor()],
                         components=[ComponentInfo(name='PointingDeviceSensor', level=1)])
        self.assertEqual(validate(scene), [])

    def test_a_level_beyond_the_one_declared(self):
        # Interchange has Geometry3D at level 2; Extrusion is level 4.
        found = validate(X3DScene(profile='Interchange', children=[
            x3d.Shape(geometry=x3d.Extrusion())]))
        self.assertIn('Geometry3D level 4', messages(found)[0])

    def test_a_profile_given_to_validate_wins(self):
        scene = X3DScene(profile='Full', children=[x3d.TouchSensor()])
        self.assertEqual(validate(scene), [])
        self.assertEqual(len(validate(scene, profile='Interchange')), 1)

    def test_an_unknown_profile(self):
        found = validate(X3DScene(profile='Imaginary'))
        self.assertIn('Imaginary', messages(found)[0])


class TestTheVersion(unittest.TestCase):
    def test_a_node_the_scenes_version_lacks(self):
        scene = X3DScene(version='3.3', children=[x3d.Shape(
            appearance=x3d.Appearance(material=x3d.PhysicalMaterial()))])
        self.assertIn('X3D 3.3 has no node PhysicalMaterial', messages(validate(scene)))

    def test_a_field_the_scenes_version_lacks(self):
        scene = X3DScene(version='3.3', children=[x3d.Shape(castShadow=False)])
        self.assertIn('X3D 3.3 has no field Shape.castShadow', messages(validate(scene)))

    def test_an_engines_own_field_is_not_held_to_a_version(self):
        from vrml import field  # noqa: PLC0415 kept with its use

        class Glossy(x3d.Material):
            x3dExtension = 'Glossy'
            sheen = field.newField('sheen', 'SFFloat', 1, 0.0)
        scene = X3DScene(children=[x3d.Shape(appearance=x3d.Appearance(material=Glossy(sheen=1)))])
        self.assertEqual(validate(scene), [])

    def test_a_component_level_past_the_highest(self):
        scene = X3DScene(components=[ComponentInfo(name='Shape', level=9)])
        self.assertTrue(any('Shape' in message and '9' in message
                            for message in messages(validate(scene))))


class TestWhatIsWalked(unittest.TestCase):
    def test_a_prototype_body(self):
        from vrml.x3d import files  # noqa: PLC0415 kept with its use
        scene = files.loads('#X3D V4.0 utf8\nPROFILE Immersive\n'
                            'PROTO P [ ] { Shape { geometry Sphere { radius -1 } } }\n')
        self.assertTrue(any('Sphere.radius' in message for message in messages(validate(scene))))

    def test_a_number_that_is_not_finite(self):
        scene = X3DScene(children=[x3d.Transform(translation=(0, float('nan'), 0))])
        self.assertIn('Transform.translation', ' '.join(messages(validate(scene))))


if __name__ == '__main__':
    unittest.main()
