"""X_ITE's own nodes, read and written in every encoding.

X_ITE declares nodes in a component of its own (`X_ITE`) and one in
Texturing3D (`ImageTextureAtlas`), and adds `extensions` to PhysicalMaterial
and `blendMode` and `depthMode` to Appearance. `vrml.x3d.xite` declares them,
the readers build them, and the writers write them with the component
statement X_ITE needs to load them.
"""

import unittest

from vrml import x3d
from vrml.x3d import builder, dialects, extension, profiles, xite
from vrml.x3d import nodes
from vrml.x3d.scene import ComponentInfo, X3DScene
from vrml.x3d.writers import X3DWriteError

ENCODINGS = ('xml', 'classic', 'json')

#: Each X_ITE node with a field set off its default, and that field's value.
SAMPLES = {
    'AnisotropyMaterialExtension': ('anisotropyStrength', 0.5),
    'ClearcoatMaterialExtension': ('clearcoatRoughness', 0.25),
    'DiffuseTransmissionMaterialExtension': ('diffuseTransmission', 0.75),
    'DispersionMaterialExtension': ('dispersion', 2.0),
    'EmissiveStrengthMaterialExtension': ('emissiveStrength', 4.0),
    'IORMaterialExtension': ('indexOfRefraction', 1.25),
    'IridescenceMaterialExtension': ('iridescenceThicknessMaximum', 500.0),
    'RetroreflectionMaterialExtension': ('retroreflection', 0.5),
    'SheenMaterialExtension': ('sheenRoughness', 0.5),
    'SpecularMaterialExtension': ('specularStrength', 2.0),
    'TransmissionMaterialExtension': ('transmission', 1.0),
    'VolumeMaterialExtension': ('thickness', 0.5),
    'VolumeScatterMaterialExtension': ('scatterAnisotropy', -0.5),
}


def material_scene(material):
    return X3DScene(children=[nodes.Shape(
        appearance=xite.Appearance(material=material), geometry=nodes.Box())])


def round_trip(scene, encoding):
    return x3d.loads(x3d.dumps(scene, encoding=encoding))


class TestDeclarations(unittest.TestCase):
    def test_the_x_ite_component_has_its_seventeen_nodes(self):
        names = sorted(name for name, cls in xite.NODES.items()
                       if getattr(cls, 'COMPONENT', None) == ('X_ITE', 1))
        self.assertEqual(names, sorted(list(SAMPLES) + [
            'BlendMode', 'DepthMode', 'InstancedShape', 'SpecularGlossinessMaterial']))

    def test_defaults_are_x_ite_s(self):
        self.assertEqual(xite.IORMaterialExtension().indexOfRefraction, 1.5)
        self.assertEqual(xite.VolumeMaterialExtension().attenuationDistance, 1000000.0)
        self.assertEqual(xite.IridescenceMaterialExtension().iridescenceIndexOfRefraction, 1.3)
        self.assertEqual(xite.EmissiveStrengthMaterialExtension().emissiveStrength, 1.0)
        mode = xite.BlendMode()
        self.assertEqual((mode.sourceColorFactor, mode.sourceAlphaFactor,
                          mode.destinationColorFactor, mode.destinationAlphaFactor),
                         ('SRC_ALPHA', 'ONE', 'ONE_MINUS_SRC_ALPHA', 'ONE_MINUS_SRC_ALPHA'))
        depth = xite.DepthMode()
        self.assertEqual(depth.depthFunction, 'LESS_EQUAL')
        self.assertEqual(list(depth.depthRange), [0.0, 1.0])
        self.assertTrue(depth.depthMask)
        self.assertEqual(xite.SpecularGlossinessMaterial().glossiness, 1.0)

    def test_extension_nodes_go_in_a_material_s_extensions(self):
        self.assertEqual(xite.SheenMaterialExtension.CONTAINER_FIELD, 'extensions')
        material = xite.PhysicalMaterial(extensions=[xite.SheenMaterialExtension()])
        self.assertEqual(len(material.extensions), 1)
        with self.assertRaises((TypeError, ValueError)):
            xite.PhysicalMaterial(extensions=[nodes.Box()])

    def test_the_vocabulary_holds_x3d_and_x_ite(self):
        self.assertIs(xite.VOCABULARY['PhysicalMaterial'], xite.PhysicalMaterial)
        self.assertIs(xite.VOCABULARY['Box'], nodes.Box)
        self.assertIn('extensions', extension.vocabulary_fields('PhysicalMaterial'))
        self.assertIn('blendMode', extension.vocabulary_fields('Appearance'))

    def test_the_component_is_known(self):
        self.assertEqual(profiles.EXTENSION_COMPONENTS['X_ITE'], 1)


class TestReading(unittest.TestCase):
    def test_every_node_is_built_in_every_encoding(self):
        extensions = [xite.NODES[name](**{field_name: value})
                      for name, (field_name, value) in SAMPLES.items()]
        scene = material_scene(xite.PhysicalMaterial(extensions=extensions))
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                read = round_trip(scene, encoding)
                self.assertFalse([item for item in read.problems if item.severity != 'info'])
                material = read.children[0].appearance.material
                self.assertIsInstance(material, xite.PhysicalMaterial)
                found = {type(item).__name__: item for item in material.extensions}
                self.assertEqual(sorted(found), sorted(SAMPLES))
                for name, (field_name, value) in SAMPLES.items():
                    self.assertAlmostEqual(getattr(found[name], field_name), value)

    def test_a_document_naming_the_component_reads_without_warnings(self):
        text = """<X3D profile='Interchange' version='4.0'><head>
            <component name='X_ITE' level='1'/></head><Scene>
            <Shape><Appearance><PhysicalMaterial><SheenMaterialExtension sheenColor='1 0 0'/>
            </PhysicalMaterial><BlendMode sourceColorFactor='ONE'/><DepthMode depthMask='false'/>
            </Appearance><Box/></Shape></Scene></X3D>"""
        read = x3d.loads(text)
        self.assertEqual([item.message for item in read.problems], [])
        appearance = read.children[0].appearance
        self.assertEqual(list(appearance.material.extensions[0].sheenColor), [1.0, 0.0, 0.0])
        self.assertEqual(appearance.blendMode.sourceColorFactor, 'ONE')
        self.assertFalse(appearance.depthMode.depthMask)

    def test_classic_vrml_reads_the_nodes(self):
        text = """#X3D V4.0 utf8
PROFILE Interchange
COMPONENT X_ITE:1
InstancedShape { translations [ 1 0 0, 2 0 0 ] geometry Box {} }
"""
        read = x3d.loads(text)
        self.assertFalse([item for item in read.problems if item.severity != 'info'])
        shape = read.children[0]
        self.assertIsInstance(shape, xite.InstancedShape)
        self.assertEqual(len(shape.translations), 2)

    def test_an_engine_without_the_node_is_told_once(self):
        text = "<X3D version='4.0'><Scene><Shape><Appearance><BlendMode/></Appearance>" \
            "</Shape></Scene></X3D>"
        read = x3d.loads(text, prototypes={'Box': nodes.Box})
        self.assertIn('Node type BlendMode has no implementation here',
                      [item.message for item in read.problems])

    def test_the_vocabulary_is_the_builders(self):
        self.assertIs(builder.DEFAULT_VOCABULARY['InstancedShape'], xite.InstancedShape)


class TestWriting(unittest.TestCase):
    def test_the_component_statement_is_added_where_the_scene_lacks_it(self):
        scene = material_scene(xite.PhysicalMaterial(
            extensions=[xite.ClearcoatMaterialExtension(clearcoat=1.0)]))
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                read = round_trip(scene, encoding)
                self.assertIn(('X_ITE', 1), [(item.name, item.level) for item in read.components])
        self.assertEqual(scene.components, [])

    def test_a_declared_component_is_written_once(self):
        scene = material_scene(xite.PhysicalMaterial(
            extensions=[xite.ClearcoatMaterialExtension(clearcoat=1.0)]))
        scene.components.append(ComponentInfo(name='X_ITE', level=1))
        text = x3d.dumps(scene)
        self.assertEqual(text.count("X_ITE"), 1)

    def test_texturing3d_is_added_for_an_atlas_outside_the_profile(self):
        atlas = xite.ImageTextureAtlas(url=['atlas.png'], slicesOverX=4, slicesOverY=4,
                                       numberOfSlices=16)
        scene = X3DScene(profile='Interchange', children=[nodes.Shape(
            appearance=nodes.Appearance(texture=atlas), geometry=nodes.Box())])
        read = round_trip(scene, 'xml')
        self.assertIn(('Texturing3D', 1), [(item.name, item.level) for item in read.components])
        self.assertEqual(read.children[0].appearance.texture.numberOfSlices, 16)

    def test_nothing_x_ite_adds_no_component(self):
        scene = material_scene(nodes.PhysicalMaterial())
        self.assertNotIn('component', x3d.dumps(scene))

    def test_vrml97_has_none_of_them(self):
        scene = X3DScene(children=[xite.InstancedShape(geometry=nodes.Box())])
        with self.assertRaises(X3DWriteError):
            x3d.dumps(scene, encoding='classic', version='2.0')

    def test_x3d_3_3_has_blend_mode_and_not_depth_mode(self):
        self.assertTrue(dialects.DIALECTS['3.3'].tables().has_node('BlendMode'))
        self.assertFalse(dialects.DIALECTS['3.3'].tables().has_node('DepthMode'))
        self.assertTrue(dialects.DIALECTS['4.0'].tables().has_node('DepthMode'))
        self.assertFalse(dialects.DIALECTS['2.0'].tables().has_node('BlendMode'))


class TestValidation(unittest.TestCase):
    def test_a_node_needs_its_component(self):
        scene = X3DScene(profile='Full', children=[xite.InstancedShape(geometry=nodes.Box())])
        self.assertTrue(any('X_ITE' in item.message for item in x3d.validate(scene)))
        scene.components.append(ComponentInfo(name='X_ITE', level=1))
        self.assertFalse(any('X_ITE' in item.message for item in x3d.validate(scene)))


if __name__ == '__main__':
    unittest.main()
