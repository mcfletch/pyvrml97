"""Dialects: what each X3D version, and VRML97, says differently.

The vocabulary is X3D 4.1. A dialect lists the node types its version has,
the fields it names differently, and the defaults it gives differently; a
reader applies it as it builds and a writer applies it on the way out.
"""

import math
import unittest

from vrml import protofunctions
from vrml.x3d import dialect, dialects
from vrml.x3d import nodes as x3d


class TestTheVRML97Dialect(unittest.TestCase):
    def setUp(self):
        self.tables = dialect.VRML97.tables()

    def test_it_has_the_54_vrml97_nodes(self):
        self.assertEqual(len(dialect.VRML97.nodeTypes), 54)
        self.assertTrue(self.tables.has_node('Transform'))
        self.assertFalse(self.tables.has_node('PhysicalMaterial'))

    def test_its_names_read_as_the_vocabulary_names(self):
        self.assertEqual(self.tables.current_name('LOD', 'level'), 'children')
        self.assertEqual(self.tables.current_name('Switch', 'choice'), 'children')
        self.assertEqual(self.tables.current_name('Collision', 'collide'), 'enabled')
        self.assertEqual(self.tables.current_name('LOD', 'range'), 'range')

    def test_the_vocabulary_names_write_as_its_names(self):
        self.assertEqual(self.tables.dialect_name('LOD', 'children'), 'level')
        self.assertEqual(self.tables.dialect_name('Group', 'children'), 'children')

    def test_its_defaults(self):
        defaults = dict(self.tables.defaults('SpotLight'))
        self.assertAlmostEqual(defaults['beamWidth'], math.pi / 2, places=5)
        self.assertAlmostEqual(defaults['cutOffAngle'], math.pi / 4, places=5)
        self.assertEqual(dict(self.tables.defaults('NavigationInfo'))['type'],
                         ['WALK', 'ANY'])
        self.assertAlmostEqual(dict(self.tables.defaults('CylinderSensor'))['diskAngle'],
                               0.262)

    def test_a_node_with_no_differences_has_no_defaults(self):
        self.assertEqual(self.tables.defaults('Transform'), [])


class TestTheX3DDialects(unittest.TestCase):
    def test_every_version_has_one(self):
        self.assertEqual(sorted(dialects.DIALECTS),
                         ['2.0', '3.0', '3.1', '3.2', '3.3', '4.0', '4.1'])
        self.assertIs(dialects.DIALECTS['2.0'], dialect.VRML97)

    def test_the_vocabulary_version_changes_nothing(self):
        tables = dialects.DIALECTS['4.1'].tables()
        self.assertEqual(tables.renames, {})
        self.assertTrue(all(tables.has_node(name) for name in x3d.CONCRETE_NODES))

    def test_x3d_4_0_lacks_the_nodes_4_1_adds(self):
        tables = dialects.DIALECTS['4.0'].tables()
        for name in ('EnvironmentLight', 'GaussianSplats', 'Tangent'):
            self.assertFalse(tables.has_node(name), name)
        self.assertTrue(tables.has_node('PhysicalMaterial'))
        self.assertEqual(tables.renames, {})

    def test_x3d_3_3_names(self):
        tables = dialects.DIALECTS['3.3'].tables()
        self.assertEqual(tables.current_name('ComposedCubeMapTexture', 'back'),
                         'backTexture')
        self.assertEqual(tables.current_name('Layer', 'isPickable'), 'pickable')
        self.assertEqual(tables.current_name('LoadSensor', 'watchList'), 'children')
        self.assertEqual(tables.current_name('ParticleSystem', 'colorRamp'), 'color')

    def test_x3d_3_3_defaults(self):
        tables = dialects.DIALECTS['3.3'].tables()
        self.assertAlmostEqual(dict(tables.defaults('SpotLight'))['beamWidth'],
                               math.pi / 4, places=4)
        self.assertEqual(list(dict(tables.defaults('SingleAxisHingeJoint'))['axis']),
                         [0, 0, 0])

    def test_x3d_3_0_has_no_rigid_body_physics(self):
        self.assertFalse(dialects.DIALECTS['3.0'].tables().has_node('RigidBody'))
        self.assertFalse(dialects.DIALECTS['3.0'].tables().has_node('PhysicalMaterial'))


class TestADialectIsANode(unittest.TestCase):
    def test_an_application_can_make_its_own(self):
        own = dialect.Dialect(
            name='Mine', version='9.9',
            renamed=[dialect.FieldRename(nodeType='Sphere', old='r', current='radius')],
            defaults=[dialect.FieldDefault(nodeType='Sphere', fieldName='radius', value='2')],
        )
        tables = own.tables()
        self.assertEqual(tables.current_name('Sphere', 'r'), 'radius')
        self.assertEqual(tables.defaults('Sphere'), [('radius', 2.0)])
        self.assertTrue(tables.has_node('Sphere'))

    def test_it_copies(self):
        copy = dialect.VRML97.copy()
        self.assertEqual(len(copy.renamed), len(dialect.VRML97.renamed))
        self.assertEqual(copy.name, 'VRML97')

    def test_a_default_for_a_field_the_node_lacks_is_refused(self):
        own = dialect.Dialect(defaults=[
            dialect.FieldDefault(nodeType='Sphere', fieldName='nosuch', value='1'),
        ])
        with self.assertRaises(AttributeError):
            own.tables()

    def test_a_default_decodes_with_its_fields_codec(self):
        default = dialect.FieldDefault(nodeType='NavigationInfo', fieldName='type',
                                       value='"FLY" "ANY"')
        self.assertEqual(default.decoded(), ['FLY', 'ANY'])
        self.assertIs(protofunctions.getField(x3d.NavigationInfo, 'type'),
                      x3d.NavigationInfo.type)


if __name__ == '__main__':
    unittest.main()
