"""The node-definition modules: what each one declares, and its fields.

`nurbs`, `shaders` and `tree` are declaration-only -- each is a set of
`node.Node` subclasses with `field.newField` calls and nothing else. So what
there is to check is that importing one registers the prototypes it names, and
that each field it declares answers its stated default. That is not much per
node, but a declaration nothing imports is a declaration nothing has ever
read: a field spelt with a type name that does not exist raises at import, and
until now no test imported these at all.
"""

import unittest

from vrml import protofunctions
from vrml.vrml97.parser import buildParser
from vrml.vrml97 import basenodes, nodetypes, nurbs, shaders, tree
from vrml.x3d import dialect
from vrml.x3d import nodes as x3d


def field_names(node_class):
    """Every field the class declares, by name."""
    return {field.name for field in protofunctions.getFields(node_class)}


class TestTheNurbsNodes(unittest.TestCase):
    """The NURBS extension proposal's nodes."""

    #: Each name, and one field it must declare.
    DECLARED = (
        ('Contour2D', 'children'),
        ('NurbsCurve', 'knot'),
        ('NurbsCurve2D', 'knot'),
        ('NurbsGroup', 'tessellationScale'),
        ('NurbsSurface', 'uKnot'),
        ('Polyline2D', 'point'),
        ('TrimmedSurface', 'trimmingContour'),
    )

    def test_it_declares_the_nodes_the_proposal_names(self):
        for name, _field in self.DECLARED:
            self.assertTrue(hasattr(nurbs, name), name)

    def test_each_node_registers_its_prototype_name(self):
        for name, _field in self.DECLARED:
            node_class = getattr(nurbs, name)
            self.assertEqual(protofunctions.protoName(node_class), name)

    def test_each_node_declares_the_field_it_is_for(self):
        for name, field in self.DECLARED:
            self.assertIn(field, field_names(getattr(nurbs, name)), name)

    def test_a_curve_holds_its_control_points(self):
        curve = nurbs.NurbsCurve(knot=[0.0, 0.0, 1.0, 1.0])
        self.assertEqual(list(curve.knot), [0.0, 0.0, 1.0, 1.0])

    def test_a_trimmed_surface_holds_a_contour(self):
        contour = nurbs.Contour2D()
        surface = nurbs.TrimmedSurface(trimmingContour=[contour])
        self.assertEqual(list(surface.trimmingContour), [contour])

    def test_a_group_defaults_its_tessellation_scale_to_one(self):
        self.assertEqual(nurbs.NurbsGroup().tessellationScale, 1.0)


class TestTheShaderNodes(unittest.TestCase):
    """The programmable-shader extension's nodes."""

    DECLARED = (
        'FloatUniform', 'GLSLImport', 'GLSLObject', 'GLSLShader',
        'IntUniform', 'Shader', 'ShaderAttribute', 'ShaderBuffer',
        'ShaderGeometry', 'ShaderIndexBuffer', 'ShaderSlice',
        'TextureBufferUniform', 'TextureUniform',
    )

    def test_it_declares_the_nodes_the_extension_names(self):
        for name in self.DECLARED:
            self.assertTrue(hasattr(shaders, name), name)

    def test_each_node_registers_its_prototype_name(self):
        for name in self.DECLARED:
            self.assertEqual(protofunctions.protoName(getattr(shaders, name)), name)

    def test_each_node_declares_the_fields_a_shader_needs(self):
        """A uniform is a name and a value; a buffer is a type and a usage."""
        self.assertLessEqual({'name', 'value'},
                             field_names(shaders.FloatUniform))
        self.assertLessEqual({'type', 'usage', 'buffer'},
                             field_names(shaders.ShaderBuffer))
        self.assertLessEqual({'attributes', 'indices', 'slices'},
                             field_names(shaders.ShaderGeometry))

    def test_a_geometry_holds_its_attributes(self):
        attribute = shaders.ShaderAttribute(name='aPosition', size=3)
        geometry = shaders.ShaderGeometry(attributes=[attribute])
        self.assertEqual(list(geometry.attributes), [attribute])

    def test_an_attribute_holds_the_name_a_shader_reads_it_at(self):
        self.assertEqual(shaders.ShaderAttribute(name='aNormal').name, 'aNormal')

    def test_a_buffer_holds_its_type(self):
        buffer = shaders.ShaderBuffer(type='GL_ARRAY_BUFFER')
        self.assertEqual(buffer.type, 'GL_ARRAY_BUFFER')

    def test_a_glsl_shader_holds_its_source(self):
        shader = shaders.GLSLShader(source=['void main(){}'])
        self.assertEqual(list(shader.source), ['void main(){}'])

    def test_a_shader_stands_where_an_appearance_does(self):
        shape = basenodes.Shape(appearance=shaders.Shader())
        self.assertIsInstance(shape.appearance, shaders.Shader)

    def test_a_glsl_object_holds_its_shaders(self):
        shader = shaders.GLSLShader(source=['void main(){}'])
        self.assertEqual(list(shaders.GLSLObject(shaders=[shader]).shaders),
                         [shader])

    def test_a_float_uniform_holds_its_value(self):
        uniform = shaders.FloatUniform(name='alpha')
        self.assertEqual(uniform.name, 'alpha')


class TestTheTreeNodes(unittest.TestCase):
    """The volumetric-tree nodes."""

    DECLARED = ('TreeAttractor', 'TreeNode', 'TreeParameters', 'VolumetricTree')

    def test_it_declares_the_nodes(self):
        for name in self.DECLARED:
            self.assertTrue(hasattr(tree, name), name)

    def test_a_node_holds_its_position_and_radius(self):
        node = tree.TreeNode(position=(1.0, 2.0, 3.0), radius=0.5)
        self.assertEqual(list(node.position), [1.0, 2.0, 3.0])
        self.assertAlmostEqual(node.radius, 0.5, places=6)

    def test_a_node_holds_its_children(self):
        child = tree.TreeNode(position=(0.0, 1.0, 0.0))
        parent = tree.TreeNode(children=[child])
        self.assertEqual(list(parent.children), [child])

    def test_an_attractor_holds_its_position_and_is_active(self):
        attractor = tree.TreeAttractor(position=(1.0, 0.0, 0.0))
        self.assertEqual(list(attractor.position), [1.0, 0.0, 0.0])
        self.assertTrue(attractor.active)

    def test_the_parameters_declare_what_the_growth_is_steered_by(self):
        declared = field_names(tree.TreeParameters)
        self.assertLessEqual(
            {'attractionDistance', 'attractorCount', 'basePosition'}, declared)

    def test_a_volumetric_tree_carries_the_growth_parameters_itself(self):
        declared = field_names(tree.VolumetricTree)
        self.assertLessEqual({'attractorCount', 'basePosition', 'barkColor'},
                             declared)


class TestTheseDoNotDisturbTheBaseNodes(unittest.TestCase):
    """Importing an extension must not rebind a VRML97 prototype.

    Each of these registers its prototypes into the same namespace the base
    nodes use, so a name collision would replace a standard node with an
    extension one for every scene loaded afterwards.
    """

    def test_the_extension_names_do_not_collide_with_the_base_nodes(self):
        for module in (nurbs, shaders, tree):
            for name in dir(module):
                if name.startswith('_'):
                    continue
                value = getattr(module, name)
                if not isinstance(value, type):
                    continue
                if hasattr(basenodes, name):
                    self.assertIs(getattr(basenodes, name), value,
                                  '%s.%s shadows a base node' % (module.__name__, name))


if __name__ == '__main__':
    unittest.main()


class TestTheVRML97Defaults(unittest.TestCase):
    """Defaults the VRML97 specification (ISO/IEC 14772-1) gives.

    The classes are the X3D 4.1 declarations; a VRML97 document is read in
    the VRML97 dialect, which supplies VRML97's defaults where X3D's differ.
    """

    def read(self, text):
        built = buildParser().parse('#VRML V2.0 utf8\n' + text + '\n')[1][1]
        return built.children[0]

    def test_an_elevation_grid_is_spaced_one_unit_apart(self):
        # 6.16 ElevationGrid: field SFFloat xSpacing 1.0, zSpacing 1.0
        grid = basenodes.ElevationGrid()
        self.assertEqual(grid.xSpacing, 1.0)
        self.assertEqual(grid.zSpacing, 1.0)

    def test_navigation_info_offers_walk_and_any(self):
        # 6.28 NavigationInfo: exposedField MFString type ["WALK", "ANY"]
        self.assertEqual(self.read('NavigationInfo {}').type, ['WALK', 'ANY'])

    def test_a_spot_light_has_vrml97_angles(self):
        # 6.44 SpotLight: beamWidth 1.570796, cutOffAngle 0.785398
        light = self.read('SpotLight {}')
        self.assertAlmostEqual(light.beamWidth, 1.570796, places=5)
        self.assertAlmostEqual(light.cutOffAngle, 0.785398, places=5)

    def test_a_value_in_the_file_wins_over_the_dialect_default(self):
        self.assertEqual(self.read('NavigationInfo { type "FLY" }').type, ['FLY'])

    def test_vrml97_field_names_are_read(self):
        lod = self.read('LOD { level [ Group {} ] }')
        self.assertEqual(len(lod.children), 1)


class TestEverySensorIsAChild(unittest.TestCase):
    """X3D puts every sensor among a grouping node's children."""

    def test_the_sensor_type_is_a_child_type(self):
        self.assertTrue(issubclass(nodetypes.Sensor, nodetypes.Children))

    def test_each_vrml97_sensor_is_a_child(self):
        for name in ('CylinderSensor', 'PlaneSensor', 'ProximitySensor',
                     'SphereSensor', 'TimeSensor', 'TouchSensor',
                     'VisibilitySensor'):
            sensor = getattr(basenodes, name)
            self.assertTrue(issubclass(sensor, nodetypes.Sensor), name)
            self.assertTrue(issubclass(sensor, nodetypes.Children), name)


class TestTheVRML97NodesAreTheX3DNodes(unittest.TestCase):
    """VRML97 is a dialect of the X3D vocabulary: one class per node name."""

    def test_each_vrml97_name_is_the_x3d_class(self):
        for name in dialect.VRML97.nodeTypes:
            if name == 'Script':
                continue
            self.assertIs(getattr(basenodes, name), x3d.CONCRETE_NODES[name], name)

    def test_a_transform_still_computes_its_matrices(self):
        forward, _inverse = basenodes.Transform(translation=(1, 0, 0)).localMatrices().data
        self.assertEqual(list(forward[3, :3]), [1, 0, 0])
