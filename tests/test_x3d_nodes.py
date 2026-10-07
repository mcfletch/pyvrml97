"""The generated X3D 4.1 declarations, `vrml.x3d.nodes`.

These read the checked-in module, so they run offline; the
`x3d-generated` tox environment is what compares it with a fresh
generation from the X3DUOM.
"""

import math
import os
import sys
import unittest

import numpy as np

from vrml import field, node, protofunctions
from vrml.vrml97 import nodetypes
from vrml.x3d import codecs
from vrml.x3d import nodes as x3d

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools'))
import generate_x3d


def abstract_types():
    return [
        value for name, value in vars(x3d).items()
        if isinstance(value, type) and name.startswith('X3D')
    ]


class TestEveryConcreteNode(unittest.TestCase):
    def test_there_are_the_266_nodes_of_x3d_4_1(self):
        # 267 concrete nodes, less ProtoInstance, which is a statement.
        self.assertEqual(len(x3d.CONCRETE_NODES), 266)
        self.assertNotIn('ProtoInstance', x3d.CONCRETE_NODES)

    def test_each_is_named_by_its_proto_name(self):
        for name, cls in x3d.CONCRETE_NODES.items():
            self.assertEqual(protofunctions.protoName(cls), name)

    def test_each_says_its_component_and_container_field(self):
        for name, cls in x3d.CONCRETE_NODES.items():
            component, level = cls.COMPONENT
            self.assertTrue(component and level >= 1, name)
            self.assertTrue(cls.CONTAINER_FIELD, name)

    def test_each_builds_with_every_default_readable(self):
        """Every default decoded from the X3DUOM coerces into its field."""
        for name, cls in x3d.CONCRETE_NODES.items():
            instance = cls()
            for declared in protofunctions.getFields(cls):
                with self.subTest(node=name, field=declared.name):
                    declared.__get__(instance)

    def test_each_default_writes_as_text_that_reads_back(self):
        for name, cls in x3d.CONCRETE_NODES.items():
            for declared in protofunctions.getFields(cls):
                type_name = declared.typeName()
                # Node fields have no text form, and the space-named
                # fields are pyvrml97's own (the DEF name, the scene root).
                if type_name in ('SFNode', 'MFNode') or declared.name.startswith(' '):
                    continue
                value = declared.coerce(declared.getDefault())
                again = declared.coerce(
                    codecs.decode(type_name, codecs.encode(type_name, value)))
                with self.subTest(node=name, field=declared.name):
                    if type_name == 'MFImage':
                        self.assertEqual(len(again), len(value))
                    else:
                        np.testing.assert_array_equal(again, value)


class TestTheAbstractTypes(unittest.TestCase):
    def test_each_carries_the_marker_the_engine_checks_for(self):
        for name, marker in generate_x3d.MARKERS.items():
            cls = getattr(x3d, name)
            self.assertTrue(issubclass(cls, getattr(nodetypes, marker)), name)

    def test_every_node_type_is_a_pyvrml97_node(self):
        for cls in abstract_types():
            if cls.__name__.endswith('Object'):
                self.assertFalse(issubclass(cls, node.Node), cls)
            else:
                self.assertTrue(issubclass(cls, node.Node), cls)

    def test_a_grouping_node_is_a_bounded_child(self):
        self.assertTrue(issubclass(x3d.X3DGroupingNode, x3d.X3DChildNode))
        self.assertTrue(issubclass(x3d.X3DGroupingNode, x3d.X3DBoundedObject))
        self.assertIn('children', {f.name for f in protofunctions.getFields(x3d.Group)})

    def test_a_movie_is_both_a_texture_and_a_sound_source(self):
        self.assertTrue(issubclass(x3d.MovieTexture, x3d.X3DTexture2DNode))
        self.assertTrue(issubclass(x3d.MovieTexture, x3d.X3DSoundSourceNode))
        self.assertTrue(issubclass(x3d.MovieTexture, x3d.X3DUrlObject))

    def test_an_engine_mix_in_that_lists_its_marker_composes(self):
        """`(marker, node.Node)` is how an engine class declares itself, and
        an implementation mixes such a class with the declaration."""
        for name, marker in generate_x3d.MARKERS.items():
            mixin = type('Mixin', (getattr(nodetypes, marker), node.Node), {})
            implementation = type(name, (mixin, getattr(x3d, name)), {})
            self.assertTrue(issubclass(implementation, getattr(x3d, name)))

    def test_every_sensor_is_a_child(self):
        for name, cls in x3d.CONCRETE_NODES.items():
            if issubclass(cls, x3d.X3DSensorNode):
                self.assertTrue(issubclass(cls, nodetypes.Children), name)


class TestFields(unittest.TestCase):
    def test_access_types(self):
        self.assertEqual(x3d.Transform.translation.accessType, 'inputOutput')
        self.assertEqual(x3d.Group.bboxSize.accessType, 'initializeOnly')
        self.assertEqual(x3d.Group.addChildren.accessType, 'inputOnly')
        self.assertEqual(x3d.TimeSensor.fraction_changed.accessType, 'outputOnly')

    def test_x3d_4_defaults(self):
        self.assertAlmostEqual(x3d.SpotLight().beamWidth, 3 * math.pi / 16, places=5)
        self.assertAlmostEqual(x3d.SpotLight().cutOffAngle, math.pi / 2, places=5)
        self.assertEqual(x3d.NavigationInfo().type, ['EXAMINE', 'ANY'])
        self.assertEqual(x3d.ElevationGrid().xSpacing, 1.0)

    def test_bounds_from_the_x3duom(self):
        self.assertEqual(x3d.PhysicalMaterial.metallic.minimum, 0.0)
        self.assertEqual(x3d.PhysicalMaterial.metallic.maximum, 1.0)

    def test_unit_categories(self):
        self.assertEqual(x3d.Transform.translation.unitCategory, 'length')
        self.assertEqual(x3d.Transform.rotation.unitCategory, 'angle')
        self.assertEqual(x3d.Group.bboxSize.unitCategory, 'length')
        self.assertEqual(x3d.SpotLight.cutOffAngle.unitCategory, 'angle')
        self.assertEqual(x3d.NavigationInfo.speed.unitCategory, 'speed')
        self.assertEqual(x3d.RigidBody.mass.unitCategory, 'mass')
        self.assertEqual(x3d.Transform.scale.unitCategory, '')

    def test_a_closed_enumeration(self):
        self.assertEqual(set(x3d.Appearance.alphaMode.choices),
                         {'AUTO', 'OPAQUE', 'MASK', 'BLEND'})
        self.assertFalse(x3d.Appearance.alphaMode.choicesOpen)

    def test_an_open_enumeration_has_its_quotes_removed(self):
        self.assertIn('EXAMINE', x3d.NavigationInfo.type.choices)
        self.assertTrue(x3d.NavigationInfo.type.choicesOpen)

    def test_double_precision_fields(self):
        self.assertEqual(x3d.CoordinateDouble(point=[[1.0000000001, 0, 0]]).point.dtype,
                         np.float64)

    def test_a_field_named_by_a_python_keyword(self):
        self.assertIs(getattr(x3d.PointLight(), 'global'), True)
        self.assertIs(getattr(x3d.DirectionalLight(), 'global'), False)
        light = x3d.DirectionalLight(**{'global': True})
        self.assertIs(getattr(light, 'global'), True)


class TestTheContentModel(unittest.TestCase):
    def test_a_field_takes_the_types_it_accepts(self):
        shape = x3d.Shape(geometry=x3d.Box(), appearance=x3d.Appearance())
        self.assertIsInstance(shape.geometry, x3d.Box)

    def test_a_field_refuses_other_types(self):
        with self.assertRaises(ValueError):
            x3d.Shape(geometry=x3d.Appearance())

    def test_children_refuse_a_node_that_is_not_a_child(self):
        with self.assertRaises(ValueError):
            x3d.Group(children=[x3d.Box()])

    def test_children_take_any_node_with_the_children_marker(self):
        class EngineChild(nodetypes.Children, node.Node):
            pass

        self.assertEqual(len(x3d.Group(children=[EngineChild()]).children), 1)

    def test_a_field_naming_a_concrete_type(self):
        self.assertEqual(x3d.X3DComposedGeometryNode.fogCoord.requiredTypes,
                         (x3d.FogCoordinate,))
        fogged = x3d.IndexedFaceSet(fogCoord=x3d.FogCoordinate())
        self.assertIsInstance(fogged.fogCoord, x3d.FogCoordinate)
        with self.assertRaises(ValueError):
            x3d.IndexedFaceSet(fogCoord=x3d.Coordinate())


class TestRenamedFields(unittest.TestCase):
    def test_vrml97_names(self):
        child = x3d.Shape()
        self.assertEqual(list(x3d.LOD(level=[child]).children), [child])
        self.assertEqual(list(x3d.Switch(choice=[child]).children), [child])
        self.assertEqual(x3d.Collision(collide=False).enabled, 0)

    def test_x3d_3_names_the_x3duom_records(self):
        texture = x3d.ImageTexture()
        self.assertIs(x3d.ComposedCubeMapTexture(back=texture).backTexture, texture)

    def test_an_alias_is_not_a_field(self):
        names = {f.name for f in protofunctions.getFields(x3d.LOD)}
        self.assertNotIn('level', names)
        self.assertIsInstance(x3d.LOD.level, field.AliasField)


class TestBehaviour(unittest.TestCase):
    def test_a_transform_computes_its_matrices(self):
        forward, inverse = x3d.Transform(translation=(1, 2, 3)).localMatrices().data
        np.testing.assert_allclose(forward[3, :3], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
