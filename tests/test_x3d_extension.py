"""Fields a class adds to an X3D node, carried through a document as metadata.

A class that adds fields to an X3D node names a metadata set with
`x3dExtension`. The writers put its added fields in a `MetadataSet` of that
name, and the builder, given the class among its prototypes, sets them back.
A node with no X3D type of its own gives `x3dEquivalent()`, the node written
in its place.
"""

import os
import unittest

from vrml import field, node
from vrml import x3d
from vrml.x3d import nodes
from vrml.x3d.scene import X3DScene
from vrml.x3d.writers import X3DWriteError

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, 'fixtures', 'x3d-schema', 'x3d-4.1.xsd')
ENCODINGS = ('xml', 'classic', 'json')


class Glossy(nodes.Material):
    """A Material with fields of its own"""

    x3dExtension = 'Glossy'
    sheen = field.newField('sheen', 'SFFloat', 1, 0.0)
    tint = field.newField('tint', 'SFColor', 1, (1.0, 1.0, 1.0))
    labels = field.newField('labels', 'MFString', 1, list)
    steps = field.newField('steps', 'SFInt32', 1, 0)
    lit = field.newField('lit', 'SFBool', 1, True)
    weights = field.newField('weights', 'MFFloat', 1, list)
    path = field.newField('path', 'MFVec3f', 1, list)
    overlay = field.newField('overlay', 'SFNode', 1, node.NULL)
    layers = field.newField('layers', 'MFNode', 1, list)


class Rubbed(Glossy):
    """A Glossy with an event of its own"""

    rubbed = field.newEvent('rubbed', 'SFFloat', 1)


class Plain(nodes.Material):
    """A Material with a field and no extension set"""

    sheen = field.newField('sheen', 'SFFloat', 1, 0.0)


class Decoded(nodes.ImageTexture):
    """A texture with no X3D type of its own, written as an ImageTexture"""

    PROTO = 'Decoded'

    def x3dEquivalent(self):
        return nodes.ImageTexture(url=['data:image/png;base64,AAAA'], repeatS=False)


def scene_of(material, texture=None):
    appearance = nodes.Appearance(material=material)
    if texture is not None:
        appearance.texture = texture
    return X3DScene(children=[nodes.Shape(appearance=appearance, geometry=nodes.Box())])


def material_of(scene):
    return scene.children[0].appearance.material


def round_trip(scene, encoding='xml', **prototypes):
    text = x3d.dumps(scene, encoding=encoding)
    return x3d.loads(text, prototypes=prototypes or {'Material': Glossy}), text


class TestWriting(unittest.TestCase):
    def test_added_fields_are_a_named_metadata_set(self):
        text = x3d.dumps(scene_of(Glossy(sheen=0.5, labels=['a', 'b'])))
        self.assertIn("name='Glossy'", text.replace('"', "'"))
        self.assertIn('<MetadataFloat', text)
        self.assertIn('<MetadataString', text)

    def test_default_values_are_not_written(self):
        text = x3d.dumps(scene_of(Glossy(sheen=0.5)))
        self.assertNotIn("'tint'", text.replace('"', "'"))
        self.assertNotIn("'lit'", text.replace('"', "'"))

    def test_nothing_added_writes_no_set(self):
        self.assertNotIn('Metadata', x3d.dumps(scene_of(Glossy())))

    def test_a_class_naming_no_set_is_refused(self):
        with self.assertRaises(X3DWriteError):
            x3d.dumps(scene_of(Plain(sheen=0.5)))

    def test_the_written_document_is_valid_against_the_schema(self):
        from lxml import etree  # noqa: PLC0415 a test-only dependency
        with open(SCHEMA, 'rb') as stream:
            schema = etree.XMLSchema(etree.parse(stream, base_url=SCHEMA))
        material = Glossy(sheen=0.5, overlay=nodes.ImageTexture(url=['a.png']),
                          metadata=nodes.MetadataString(name='author', value=['me']))
        text = x3d.dumps(scene_of(material, Decoded()))
        document = etree.fromstring(text.encode('utf-8'), etree.XMLParser(
            load_dtd=False, no_network=True, resolve_entities=False))
        self.assertTrue(schema.validate(document), schema.error_log)


class TestReading(unittest.TestCase):
    def test_every_value_type_comes_back(self):
        written = Glossy(sheen=0.5, tint=(0.25, 0.5, 0.75), labels=['a', 'b c'], steps=3,
                         lit=False, weights=[0.5, 1.5], path=[(1, 2, 3), (4, 5, 6)])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                read = material_of(round_trip(scene_of(written), encoding)[0])
                self.assertIsInstance(read, Glossy)
                self.assertAlmostEqual(read.sheen, 0.5)
                self.assertEqual([round(v, 6) for v in read.tint], [0.25, 0.5, 0.75])
                self.assertEqual(list(read.labels), ['a', 'b c'])
                self.assertEqual(read.steps, 3)
                self.assertFalse(read.lit)
                self.assertEqual([round(v, 6) for v in read.weights], [0.5, 1.5])
                self.assertEqual([[round(v, 6) for v in point] for point in read.path],
                                 [[1, 2, 3], [4, 5, 6]])
                self.assertFalse(read.metadata)

    def test_a_node_value_comes_back(self):
        properties = nodes.TextureProperties(boundaryModeS='CLAMP_TO_EDGE')
        written = Glossy(overlay=nodes.ImageTexture(url=['a.png'], repeatT=False,
                                                    textureProperties=properties))
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                overlay = material_of(round_trip(scene_of(written), encoding)[0]).overlay
                self.assertIsInstance(overlay, nodes.ImageTexture)
                self.assertEqual(list(overlay.url), ['a.png'])
                self.assertFalse(overlay.repeatT)
                self.assertEqual(overlay.textureProperties.boundaryModeS, 'CLAMP_TO_EDGE')

    def test_a_list_of_nodes_comes_back(self):
        written = Glossy(layers=[nodes.ImageTexture(url=['a.png']),
                                 nodes.ImageTexture(url=['b.png'], repeatS=False)])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                layers = material_of(round_trip(scene_of(written), encoding)[0]).layers
                self.assertEqual([list(layer.url) for layer in layers], [['a.png'], ['b.png']])
                self.assertFalse(layers[1].repeatS)

    def test_a_list_of_nodes_inside_a_node_value_comes_back(self):
        group = nodes.Group(children=[nodes.Shape(geometry=nodes.Sphere(radius=2))])
        written = Glossy(overlay=group)
        overlay = material_of(round_trip(scene_of(written))[0]).overlay
        self.assertEqual(overlay.children[0].geometry.radius, 2.0)

    def test_the_nodes_own_metadata_is_kept(self):
        written = Glossy(sheen=0.5, metadata=nodes.MetadataString(name='author', value=['me']))
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                read = material_of(round_trip(scene_of(written), encoding)[0])
                self.assertAlmostEqual(read.sheen, 0.5)
                self.assertEqual(read.metadata.name, 'author')
                self.assertEqual(list(read.metadata.value), ['me'])

    def test_without_the_class_the_set_is_metadata(self):
        text = x3d.dumps(scene_of(Glossy(sheen=0.5)))
        read = material_of(x3d.loads(text))
        self.assertEqual(type(read), nodes.Material)
        self.assertEqual(read.metadata.name, 'Glossy')
        self.assertEqual(read.metadata.value[0].name, 'sheen')

    def test_an_entry_naming_no_field_is_reported(self):
        text = x3d.dumps(scene_of(Glossy(sheen=0.5))).replace("'sheen'", "'shine'").replace(
            '"sheen"', '"shine"')
        read = x3d.loads(text, prototypes={'Material': Glossy})
        self.assertTrue(any('shine' in str(problem) for problem in read.problems))

    def test_an_entry_naming_an_event_is_reported(self):
        text = x3d.dumps(scene_of(Glossy(sheen=0.5))).replace("'sheen'", "'rubbed'").replace(
            '"sheen"', '"rubbed"')
        read = x3d.loads(text, prototypes={'Material': Rubbed})
        self.assertTrue(any('rubbed' in str(problem) for problem in read.problems))


class TestEquivalents(unittest.TestCase):
    def test_a_node_is_written_as_its_equivalent(self):
        text = x3d.dumps(scene_of(nodes.Material(), Decoded()))
        self.assertNotIn('Decoded', text)
        texture = x3d.loads(text).children[0].appearance.texture
        self.assertEqual(list(texture.url), ['data:image/png;base64,AAAA'])
        self.assertFalse(texture.repeatS)

    def test_a_node_in_an_added_field_is_written_as_its_equivalent(self):
        overlay = material_of(round_trip(scene_of(Glossy(overlay=Decoded())))[0]).overlay
        self.assertEqual(list(overlay.url), ['data:image/png;base64,AAAA'])
        self.assertFalse(overlay.repeatS)

    def test_a_shared_node_shares_its_equivalent(self):
        shared = Decoded()
        scene = X3DScene(children=[
            nodes.Shape(appearance=nodes.Appearance(texture=shared)),
            nodes.Shape(appearance=nodes.Appearance(texture=shared)),
        ])
        for encoding in ENCODINGS:
            with self.subTest(encoding=encoding):
                read = x3d.loads(x3d.dumps(scene, encoding=encoding))
                self.assertIs(read.children[0].appearance.texture,
                              read.children[1].appearance.texture)


if __name__ == '__main__':
    unittest.main()
