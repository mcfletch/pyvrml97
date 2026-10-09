"""SceneBuilder: what the calls a reader makes build.

These drive the builder directly, as a reader does, so each rule is held
here once for every encoding.
"""

import math
import unittest

import numpy as np
import pytest

from vrml import node, protofunctions
from vrml.x3d import builder as buildermodule
from vrml.x3d import loads
from vrml.x3d import nodes as x3d
from vrml.x3d import readers, writers
from vrml.x3d.builder import SceneBuilder, X3DLoadError


def problems(scene, severity=None):
    return [p for p in scene.problems if severity is None or p.severity == severity]


class Built:
    """A builder and helpers for writing a document in calls."""

    def __init__(self, **options):
        self.b = SceneBuilder(**options)

    def node(self, type_name, children=(), DEF='', USE='', containerField='', **fields):
        made = self.b.start_node(type_name, DEF=DEF, USE=USE, containerField=containerField)
        for name, text in fields.items():
            self.b.field_text(name, text)
        for child in children:
            child()
        self.b.end_node()
        return made

    def __getattr__(self, name):
        return getattr(self.b, name)


class TestNodes(unittest.TestCase):
    def test_a_root_node_and_its_fields(self):
        built = Built()
        built.document('Interchange', '4.0')
        made = built.node('Transform', translation='1 2 3')
        scene = built.end_document()
        self.assertEqual(list(scene.children), [made])
        self.assertEqual(list(made.translation), [1, 2, 3])
        self.assertEqual((scene.profile, scene.version), ('Interchange', '4.0'))
        self.assertEqual(problems(scene), [])

    def test_children_go_in_their_default_container(self):
        built = Built()
        shape = built.node('Shape', children=[
            lambda: built.node('Appearance', children=[lambda: built.node('Material')]),
            lambda: built.node('Sphere', radius='2'),
        ])
        built.end_document()
        self.assertIsInstance(shape.appearance, x3d.Appearance)
        self.assertIsInstance(shape.appearance.material, x3d.Material)
        self.assertEqual(shape.geometry.radius, 2.0)

    def test_an_explicit_container_field(self):
        built = Built()
        lod = built.node('Collision', children=[
            lambda: built.node('Shape', containerField='proxy'),
        ])
        built.end_document()
        self.assertIsInstance(lod.proxy, x3d.Shape)
        self.assertEqual(len(lod.children), 0)

    def test_a_node_whose_default_container_is_absent_finds_one_that_takes_it(self):
        built = Built()
        group = built.node('MetadataSet', children=[
            lambda: built.node('MetadataString', containerField='value'),
        ])
        built.end_document()
        self.assertEqual(len(group.value), 1)

    def test_the_implied_container(self):
        implied = buildermodule.implied_container
        self.assertEqual(implied(x3d.Shape(), x3d.Sphere()), 'geometry')
        self.assertEqual(implied(x3d.Collision(), x3d.Shape()), 'children')
        self.assertEqual(implied(x3d.MetadataSet(), x3d.MetadataString()), 'value')
        self.assertIsNone(implied(x3d.Shape(), x3d.Transform()))

    def test_a_use_of_an_enclosing_node_is_an_error_and_not_placed(self):
        built = Built()
        group = built.b.start_node('Group', DEF='LOOP')
        inner = built.b.start_node('Transform')
        built.b.start_node('Group', USE='LOOP')
        built.end_node()
        built.end_node()
        built.end_node()
        scene = built.end_document()
        self.assertEqual(list(inner.children), [])
        self.assertIn("USE of 'LOOP' inside the node it names",
                      [problem.message for problem in scene.problems])
        self.assertEqual(list(group.children), [inner])

    def test_a_script_may_hold_itself_in_a_field(self):
        scene = loads(b"""<X3D version="3.3"><Scene><Script DEF="SELF">
          <field name="me" type="SFNode" accessType="initializeOnly"><Script USE="SELF"/></field>
          </Script></Scene></X3D>""")
        self.assertEqual(problems(scene, 'error'), [])
        script = scene.getDEF('SELF')
        self.assertIs(script.me, script)

    def test_a_field_a_subclass_hides_is_not_an_implied_container(self):
        class Hiding(x3d.TextureBackground):
            # An implementation's own attribute in place of an inherited field
            backTexture = property(lambda _node: None)
        self.assertEqual(buildermodule.implied_container(Hiding(), x3d.ImageTexture()),
                         'bottomTexture')

    def test_a_named_field_takes_the_nodes_started_in_it(self):
        built = Built()
        group = built.b.start_node('Group')
        built.start_field('children')
        built.node('Shape')
        built.node('Shape')
        built.end_field()
        built.end_node()
        built.end_document()
        self.assertEqual(len(group.children), 2)

    def test_a_list_field_is_set_once(self):
        built = Built()
        counts = []
        group = built.b.start_node('Group')
        for _ in range(3):
            built.node('Shape')
        original = node.MFNode.fset

        def counting(field, client, value, notify=1):
            counts.append(field.name)
            return original(field, client, value, notify)

        node.MFNode.fset = counting
        try:
            built.end_node()
        finally:
            node.MFNode.fset = original
        self.assertEqual(counts, ['children'])
        self.assertEqual(len(group.children), 3)

    def test_an_unknown_node_type_is_a_problem_and_its_contents_are_skipped(self):
        built = Built()
        built.node('Group', children=[
            lambda: built.node('NoSuchNode', children=[lambda: built.node('Shape')]),
        ])
        scene = built.end_document()
        self.assertEqual(len(scene.children[0].children), 0)
        self.assertIn('NoSuchNode', problems(scene, 'error')[0].message)

    def test_a_node_in_the_wrong_field_is_a_problem(self):
        built = Built()
        built.node('Shape', children=[lambda: built.node('Box', containerField='appearance')])
        scene = built.end_document()
        self.assertEqual(len(problems(scene, 'error')), 1)

    def test_strict_mode_raises_at_the_first_error(self):
        built = Built(strict=True)
        with self.assertRaises(X3DLoadError):
            built.node('NoSuchNode')

    def test_a_problem_records_the_readers_position(self):
        built = Built()
        built.b.line, built.b.column = 12, 4
        built.node('NoSuchNode')
        problem = problems(built.end_document())[0]
        self.assertEqual((problem.line, problem.column), (12, 4))
        self.assertIn('line 12', str(problem))

    def test_an_engine_vocabulary(self):
        class Engine(x3d.Sphere):
            pass

        built = Built(prototypes={'Sphere': Engine})
        made = built.node('Sphere')
        built.node('Box')
        scene = built.end_document()
        self.assertIsInstance(made, Engine)
        self.assertIn('Box', [p.message.split()[2] for p in problems(scene, 'info')])

    def test_an_engine_vocabulary_is_laid_over_the_runtime(self):
        """A node the engine does not supply keeps the behaviour pyvrml97 gives it"""
        from vrml.x3d import runtime  # noqa: PLC0415 kept with its use

        class Engine(x3d.Sphere):
            pass

        built = Built(prototypes={'Sphere': Engine})
        clock = built.node('TimeSensor')
        scene = built.end_document()
        self.assertIsInstance(clock, runtime.PROTOTYPES['TimeSensor'])
        self.assertNotIn('TimeSensor', [p.message.split()[2] for p in problems(scene, 'info')])

    def test_without_a_vocabulary_nothing_is_reported_unimplemented(self):
        built = Built()
        built.node('Box')
        self.assertEqual(problems(built.end_document(), 'info'), [])

    def test_a_node_is_in_the_scene_before_its_fields_are_set(self):
        """A field that reads the node's document (a url) finds it while it is read."""
        from vrml import fieldtypes  # noqa: PLC0415 kept with its one use
        seen = []

        class WatchedURL(fieldtypes.MFString):
            fieldType = 'MFString'

            def fset(self, client, value, notify=1):
                seen.append(protofunctions.root(client))
                return super().fset(client, value, notify)

        class Watched(x3d.ImageTexture):
            url = WatchedURL('url', 1, list)

        built = Built(prototypes={'ImageTexture': Watched}, baseURI='here.x3d')
        built.node('Shape', children=[
            lambda: built.node('Appearance', children=[
                lambda: built.node('ImageTexture', url='"a.png"')])])
        scene = built.end_document()
        self.assertTrue(seen)
        self.assertIs(seen[0], scene)

    def test_an_engine_default_gives_way_to_the_declarations_in_a_document(self):
        """A document means X3D's defaults, whatever an engine's class says for code."""
        class Engine(x3d.PointLight):
            shadows = buildermodule.field.newField('shadows', 'SFBool', 1, True)

        built = Built(prototypes={'PointLight': Engine})
        quiet = built.node('PointLight')
        loud = built.node('PointLight', shadows='true')
        built.end_document()
        self.assertTrue(Engine().shadows)
        self.assertFalse(quiet.shadows)
        self.assertTrue(loud.shadows)

    def test_a_field_the_documents_version_lacks_takes_x3ds_default(self):
        """A version without shadows has none, which is what X3D's default says"""
        class Engine(x3d.PointLight):
            shadows = buildermodule.field.newField('shadows', 'SFBool', 1, True)

        built = Built(prototypes={'PointLight': Engine})
        built.document(profile='Immersive', version='3.3')
        light = built.node('PointLight')
        built.end_document()
        self.assertFalse(light.shadows)

    def test_an_engine_scene_class(self):
        from vrml.x3d.scene import X3DScene  # noqa: PLC0415 kept with its one use

        class EngineScene(X3DScene):
            pass

        built = Built(prototypes={'X3DScene': EngineScene}, baseURI='here.x3d')
        built.node('Group')
        scene = built.end_document()
        self.assertIsInstance(scene, EngineScene)
        self.assertEqual(scene.baseURI, 'here.x3d')
        self.assertEqual(len(scene.children), 1)


class TestFields(unittest.TestCase):
    def test_an_unknown_field_is_a_warning(self):
        built = Built()
        built.node('Sphere', nosuch='1')
        self.assertIn('nosuch', problems(built.end_document(), 'warning')[0].message)

    def test_a_bad_value_is_an_error_and_the_default_stays(self):
        built = Built()
        sphere = built.node('Sphere', radius='large')
        scene = built.end_document()
        self.assertEqual(sphere.radius, 1.0)
        self.assertEqual(len(problems(scene, 'error')), 1)

    def test_an_unquoted_mfstring_is_read_with_a_warning(self):
        built = Built()
        texture = built.node('ImageTexture', url='brick.png')
        scene = built.end_document()
        self.assertEqual(texture.url, ['brick.png'])
        self.assertEqual(len(problems(scene, 'warning')), 1)

    def test_a_backslash_before_another_character_is_read_with_a_warning(self):
        """Only \\" and \\\\ are escapes in an MFString; C:\\path loses its backslashes"""
        built = Built()
        texture = built.node('ImageTexture', url='"C:\\maps\\brick.png" "a\\"b"')
        scene = built.end_document()
        self.assertEqual(texture.url, ['C:mapsbrick.png', 'a"b'])
        self.assertEqual(len(problems(scene, 'warning')), 1)
        self.assertIn('backslash', problems(scene, 'warning')[0].message)

    def test_a_typed_value(self):
        built = Built()
        built.b.start_node('Transform')
        built.field('translation', [1, 2, 3])
        made = built.end_node()
        self.assertEqual(list(made.translation), [1, 2, 3])

    def test_an_event_takes_no_value(self):
        built = Built()
        built.node('Group', addChildren='')
        self.assertEqual(len(problems(built.end_document(), 'warning')), 1)


class TestNames(unittest.TestCase):
    def test_def_and_use(self):
        built = Built()
        built.node('Group', children=[
            lambda: built.node('Shape', DEF='S'),
            lambda: built.node('Shape', USE='S'),
        ])
        scene = built.end_document()
        first, second = scene.children[0].children
        self.assertIs(first, second)
        self.assertIs(scene.getDEF('S'), first)
        self.assertEqual(protofunctions.defName(first), 'S')

    def test_use_of_an_unknown_name(self):
        built = Built()
        built.node('Shape', USE='nobody')
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)

    def test_use_of_a_node_of_another_type_is_a_warning(self):
        built = Built()
        built.node('Shape', DEF='S')
        built.node('Group', USE='S')
        self.assertEqual(len(problems(built.end_document(), 'warning')), 1)

    def test_a_name_given_twice_is_a_warning_and_the_later_wins(self):
        built = Built()
        built.node('Shape', DEF='S')
        later = built.node('Shape', DEF='S')
        scene = built.end_document()
        self.assertIs(scene.getDEF('S'), later)
        self.assertEqual(len(problems(scene, 'warning')), 1)


class TestDialects(unittest.TestCase):
    def test_a_vrml97_document_takes_vrml97_defaults(self):
        built = Built()
        built.document('', '2.0')
        light = built.node('SpotLight')
        built.end_document()
        self.assertAlmostEqual(light.beamWidth, 1.570796, places=5)

    def test_a_value_in_the_document_wins_over_the_dialect_default(self):
        built = Built()
        built.document('', '2.0')
        light = built.node('SpotLight', beamWidth='0.5')
        built.end_document()
        self.assertEqual(light.beamWidth, 0.5)

    def test_old_names_are_read_as_current_ones(self):
        built = Built()
        built.document('', '2.0')
        lod = built.node('LOD', children=[lambda: built.node('Shape', containerField='level')])
        built.end_document()
        self.assertEqual(len(lod.children), 1)

    def test_an_x3d_3_3_name(self):
        built = Built()
        built.document('Immersive', '3.3')
        layer = built.node('Layer', isPickable='false')
        built.end_document()
        self.assertIs(layer.pickable, False)

    def test_a_node_the_version_lacks_is_a_warning(self):
        built = Built()
        built.document('Full', '3.0')
        built.node('PhysicalMaterial')
        warnings = problems(built.end_document(), 'warning')
        self.assertEqual([p.message for p in warnings], ['X3D 3.0 has no node PhysicalMaterial'])

    def test_a_field_the_version_lacks_is_a_warning_and_is_read(self):
        built = Built()
        built.document('', '2.0')
        viewpoint = built.node('Viewpoint', centerOfRotation='1 2 3')
        warnings = problems(built.end_document(), 'warning')
        self.assertEqual([p.message for p in warnings],
                         ['VRML97 has no field Viewpoint.centerOfRotation'])
        self.assertEqual(list(viewpoint.centerOfRotation), [1, 2, 3])

    def test_a_node_field_the_version_lacks_is_a_warning_and_is_read(self):
        built = Built()
        built.document('Full', '3.0')
        appearance = built.node('Appearance', children=[lambda: built.node('PointProperties')])
        warnings = problems(built.end_document(), 'warning')
        self.assertEqual([p.message for p in warnings], [
            'X3D 3.0 has no node PointProperties', 'X3D 3.0 has no field Appearance.pointProperties'])
        self.assertIsInstance(appearance.pointProperties, x3d.PointProperties)

    def test_a_route_to_a_field_the_version_lacks_is_a_warning_and_is_made(self):
        built = Built()
        built.document('', '2.0')
        built.node('TimeSensor', DEF='Clock')
        built.node('TimeSensor', DEF='Other')
        made = built.route('Other', 'cycleTime', 'Clock', 'pauseTime')
        warnings = problems(built.end_document(), 'warning')
        self.assertEqual([p.message for p in warnings], ['VRML97 has no field TimeSensor.pauseTime'])
        self.assertIsNotNone(made)

    def test_a_vrml97_document_names_its_version_vrml97(self):
        built = Built()
        built.document('', '2.0')
        built.node('LocalFog')
        warnings = problems(built.end_document(), 'warning')
        self.assertEqual([p.message for p in warnings], ['VRML97 has no node LocalFog'])

    def test_a_vrml97_prototype_declaring_an_x3d_field_type_is_warned_of(self):
        """VRML97 has no MFBool; X3D's converters write it into .wrl prototypes"""
        scene = readers.read(b'#VRML V2.0 utf8\nPROTO P [ field MFBool flags [ TRUE ] ] { Group {} }\n',
                             name='a.wrl')
        self.assertEqual([p.message for p in scene.problems if p.severity == 'warning'],
                         ['VRML97 has no field type MFBool (flags)'])

    def test_a_node_x3d_does_not_declare_is_no_version_warning(self):
        """An application's own node in its vocabulary is in no version of X3D"""
        class Engine(x3d.Group):
            PROTO = 'EngineGroup'

        class EngineCurve(x3d.Group):
            """Its own node, under a name X3D gives another"""
            PROTO = 'NurbsCurve'

        built = Built(prototypes={'EngineGroup': Engine, 'NurbsCurve': EngineCurve})
        built.document('', '2.0')
        made = built.node('EngineGroup')
        self.assertIsInstance(made, Engine)
        self.assertIsInstance(built.node('NurbsCurve'), EngineCurve)
        self.assertEqual(problems(built.end_document(), 'warning'), [])

    def test_an_unknown_version_reads_as_the_nearest(self):
        built = Built()
        built.document('Full', '3.9')
        self.assertEqual(len(problems(built.end_document(), 'warning')), 1)


class TestStatements(unittest.TestCase):
    def test_components_meta(self):
        built = Built()
        built.component('HAnim', 1)
        built.component('H-Anim', 2)
        built.meta('title', 'A world', lang='en')
        scene = built.end_document()
        self.assertEqual([(c.name, c.level) for c in scene.components],
                         [('HAnim', 1), ('HAnim', 2)])
        self.assertEqual((scene.meta[0].name, scene.meta[0].lang), ('title', 'en'))

    def test_an_unknown_component(self):
        built = Built()
        built.component('Telepathy', 1)
        self.assertEqual(len(problems(built.end_document(), 'warning')), 1)

    def test_an_unknown_profile(self):
        built = Built()
        built.document('Superb', '4.0')
        self.assertEqual(len(problems(built.end_document(), 'warning')), 1)


class TestUnits(unittest.TestCase):
    def built(self):
        built = Built()
        built.document('Interchange', '4.0')
        built.unit('length', 'centimetre', 0.01)
        built.unit('angle', 'degree', math.pi / 180)
        return built

    def test_lengths_are_scaled(self):
        built = self.built()
        transform = built.node('Transform', translation='100 0 0', scale='2 2 2')
        built.end_document()
        np.testing.assert_allclose(transform.translation, [1, 0, 0])
        np.testing.assert_allclose(transform.scale, [2, 2, 2])

    def test_a_rotation_scales_only_its_angle(self):
        built = self.built()
        transform = built.node('Transform', rotation='0 1 0 90')
        built.end_document()
        np.testing.assert_allclose(transform.rotation, [0, 1, 0, math.pi / 2], rtol=1e-6)

    def test_an_area_is_scaled_by_the_length_squared(self):
        built = Built()
        built.document('Full', '4.0')
        built.unit('length', 'centimetre', 0.01)
        emitter = built.node('PointEmitter', surfaceArea='10000')
        built.end_document()
        self.assertAlmostEqual(emitter.surfaceArea, 1.0)

    def test_the_scene_records_its_units(self):
        scene = self.built().end_document()
        self.assertEqual([(u.category, u.conversionFactor) for u in scene.units],
                         [('length', 0.01), ('angle', math.pi / 180)])

    def test_units_before_x3d_3_3_are_an_error(self):
        built = Built()
        built.document('Full', '3.2')
        built.unit('length', 'centimetre', 0.01)
        scene = built.end_document()
        self.assertEqual(len(scene.units), 0)
        self.assertEqual(len(problems(scene, 'error')), 1)

    def test_a_bad_factor_or_category(self):
        built = Built()
        built.unit('length', 'nothing', 0.0)
        built.unit('time', 'minute', 60)
        scene = built.end_document()
        self.assertEqual(len(problems(scene, 'error')), 2)


class TestRoutes(unittest.TestCase):
    def test_a_route_between_named_nodes(self):
        built = Built()
        built.node('TimeSensor', DEF='Clock')
        built.node('PositionInterpolator', DEF='Path')
        built.route('Clock', 'fraction_changed', 'Path', 'set_fraction')
        scene = built.end_document()
        self.assertEqual(len(scene.routes), 1)
        self.assertEqual(problems(scene), [])

    def test_a_route_from_an_input_only_field(self):
        built = Built()
        built.node('PositionInterpolator', DEF='A')
        built.node('PositionInterpolator', DEF='B')
        built.route('A', 'set_fraction', 'B', 'set_fraction')
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)

    def test_a_route_between_fields_of_different_types(self):
        built = Built()
        built.node('TimeSensor', DEF='Clock')
        built.node('Transform', DEF='Mover')
        built.route('Clock', 'fraction_changed', 'Mover', 'set_translation')
        scene = built.end_document()
        self.assertEqual(scene.routes, [])
        self.assertEqual(len(problems(scene, 'error')), 1)

    def test_a_route_to_an_unknown_node(self):
        built = Built()
        built.node('TimeSensor', DEF='Clock')
        built.route('Clock', 'fraction_changed', 'Nobody', 'set_fraction')
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)

    def test_a_route_to_an_imported_node_waits(self):
        built = Built()
        built.node('Inline', DEF='House')
        built.node('TimeSensor', DEF='Clock')
        built.import_('House', 'Door', 'FrontDoor')
        built.route('Clock', 'fraction_changed', 'FrontDoor', 'set_fraction')
        scene = built.end_document()
        self.assertEqual(len(scene.pendingRoutes), 1)
        self.assertEqual(scene.imports[0].localDEF, 'FrontDoor')
        self.assertEqual(problems(scene), [])

    def test_binding_imports_makes_the_waiting_routes(self):
        built = Built()
        inline = built.node('Inline', DEF='House')
        built.node('TimeSensor', DEF='Clock')
        built.import_('House', 'Door', 'FrontDoor')
        built.route('Clock', 'fraction_changed', 'FrontDoor', 'set_fraction')
        scene = built.end_document()
        inner = Built()
        door = inner.node('PositionInterpolator', DEF='DoorPath')
        inner.export('DoorPath', 'Door')
        inlined = inner.end_document()
        self.assertEqual(buildermodule.bind_imports(scene, inline, inlined), ['FrontDoor'])
        self.assertIs(scene.getDEF('FrontDoor'), door)
        self.assertEqual(len(scene.pendingRoutes), 0)
        self.assertEqual(len(scene.routes), 1)

    def test_an_export_of_an_unknown_name(self):
        built = Built()
        built.export('Nobody')
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)


class TestPrototypes(unittest.TestCase):
    def declare(self, built):
        built.start_proto('Lamp')
        built.proto_field('lightColor', 'SFColor', 'inputOutput', '1 0 0')
        built.proto_field('size', 'SFFloat', 'initializeOnly', '2')
        built.start_proto_body()
        built.b.start_node('Group')
        built.b.start_node('PointLight')
        built.connect('color', 'lightColor')
        built.end_node()
        built.b.start_node('Shape')
        built.b.start_node('Sphere', DEF='Bulb')
        built.connect('radius', 'size')
        built.end_node()
        built.end_node()
        built.end_node()
        built.end_proto_body()
        return built.end_proto()

    def test_a_prototype_and_an_instance(self):
        built = Built()
        Lamp = self.declare(built)
        lamp = built.node('Lamp', lightColor='0 1 0')
        scene = built.end_document()
        self.assertIs(scene.getProto('Lamp'), Lamp)
        self.assertIsInstance(lamp, Lamp)
        body = protofunctions.getSceneGraph(lamp)
        light = body.children[0].children[0]
        self.assertEqual(list(light.color), [0, 1, 0])
        self.assertEqual(problems(scene), [])

    def test_each_instance_has_a_body_of_its_own(self):
        built = Built()
        self.declare(built)
        first = built.node('Lamp', size='3')
        second = built.node('Lamp')
        built.end_document()
        sphere = protofunctions.getSceneGraph(first).children[0].children[1].geometry
        other = protofunctions.getSceneGraph(second).children[0].children[1].geometry
        self.assertIsNot(sphere, other)
        self.assertEqual((sphere.radius, other.radius), (3.0, 2.0))

    def test_an_instance_stands_where_its_first_node_does(self):
        built = Built()
        Lamp = self.declare(built)
        self.assertIs(Lamp.nodeType, x3d.Group)
        group = built.node('Transform', children=[lambda: built.node('Lamp')])
        shape = built.node('Shape', children=[lambda: built.node('Lamp', containerField='geometry')])
        scene = built.end_document()
        self.assertEqual(len(group.children), 1)
        self.assertIs(shape.geometry, node.NULL)
        self.assertEqual(len(problems(scene, 'error')), 1)

    def test_body_names_are_the_bodys_own(self):
        built = Built()
        self.declare(built)
        scene = built.end_document()
        self.assertIsNone(scene.getDEF('Bulb'))

    def test_connecting_an_undeclared_field(self):
        built = Built()
        built.start_proto('Broken')
        built.start_proto_body()
        built.b.start_node('Group')
        built.connect('children', 'nosuch')
        built.end_node()
        built.end_proto_body()
        built.end_proto()
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)

    def test_an_is_connection_between_fields_of_different_types(self):
        built = Built()
        built.start_proto('Broken')
        built.proto_field('where', 'SFFloat', 'inputOutput', '1')
        built.start_proto_body()
        built.b.start_node('Transform')
        built.connect('translation', 'where')
        built.end_node()
        built.end_proto_body()
        Broken = built.end_proto()
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)
        self.assertEqual(protofunctions.getSceneGraph(Broken).children[0].translation.tolist(),
                         [0, 0, 0])

    def test_is_connections_follow_the_access_rules(self):
        """X3D 4.4.4.3: an inputOutput node field takes a prototype field of any
        access; an inputOutput prototype field needs an inputOutput node field.
        A connection against the rules is a warning, and is made"""
        cases = [('initializeOnly', 'Sphere', 'radius', 0),
                 ('inputOutput', 'Sphere', 'radius', 1),
                 ('initializeOnly', 'Transform', 'scale', 0),
                 ('inputOnly', 'Transform', 'scale', 0),
                 ('outputOnly', 'Transform', 'scale', 0),
                 ('initializeOnly', 'PositionInterpolator', 'set_fraction', 1),
                 ('inputOnly', 'PositionInterpolator', 'set_fraction', 0)]
        for access, type_name, node_field, wrong in cases:
            built = Built()
            built.start_proto('P')
            kind, default = ('SFVec3f', '1 1 1') if node_field == 'scale' else ('SFFloat', '1')
            if access in ('inputOnly', 'outputOnly'):
                default = None
            built.proto_field('f', kind, access, default)
            built.start_proto_body()
            built.b.start_node(type_name)
            built.connect(node_field, 'f')
            built.end_node()
            built.end_proto_body()
            built.end_proto()
            with self.subTest(access=access, node=type_name):
                scene = built.end_document()
                self.assertEqual(len(problems(scene, 'warning')), wrong)
                self.assertEqual(problems(scene, 'error'), [])

    def test_a_prototype_declared_in_a_body_is_the_bodys(self):
        built = Built()
        built.start_proto('Outer')
        built.start_proto_body()
        built.start_proto('Inner')
        built.start_proto_body()
        built.node('Group')
        built.end_proto_body()
        Inner = built.end_proto()
        built.node('Inner')
        built.end_proto_body()
        Outer = built.end_proto()
        scene = built.end_document()
        self.assertIsNone(scene.getProto('Inner'))
        self.assertIs(protofunctions.getSceneGraph(Outer).protoTypes['Inner'], Inner)

    def test_a_node_valued_default(self):
        built = Built()
        built.start_proto('Holder')
        built.proto_field('content', 'MFNode', 'inputOutput')
        built.start_proto_field_nodes('content')
        built.node('Shape')
        built.end_proto_field_nodes()
        built.start_proto_body()
        built.b.start_node('Group')
        built.connect('children', 'content')
        built.end_node()
        built.end_proto_body()
        Holder = built.end_proto()
        built.end_document()
        self.assertEqual(len(Holder().content), 1)

    def test_prototypes_declared_inside_a_node(self):
        """Classic VRML declares a PROTO among a node's fields; its body, and a
        body inside that one, leave the node open for the rest of its fields"""
        built = Built()
        group = built.b.start_node('Group')
        built.start_proto('Outer')
        built.start_proto_body()
        built.start_proto('Inner')
        built.start_proto_body()
        built.node('Group')
        built.end_proto_body()
        built.end_proto()
        built.node('Inner')
        built.end_proto_body()
        built.end_proto()
        built.node('Outer')
        built.end_node()
        scene = built.end_document()
        self.assertEqual(problems(scene), [])
        self.assertEqual(scene.children, [group])
        self.assertEqual(len(group.children), 1)

    def test_a_node_valued_default_declared_inside_a_node(self):
        built = Built()
        group = built.b.start_node('Group')
        built.start_proto('Holder')
        built.proto_field('content', 'SFNode', 'inputOutput')
        built.start_proto_field_nodes('content')
        built.node('Box')
        built.end_proto_field_nodes()
        built.start_proto_body()
        built.b.start_node('Shape')
        built.connect('geometry', 'content')
        built.end_node()
        built.end_proto_body()
        Holder = built.end_proto()
        built.end_node()
        scene = built.end_document()
        self.assertEqual(problems(scene), [])
        self.assertEqual(group.children, [])
        self.assertIsInstance(Holder().content, x3d.Box)


class TestExternalPrototypes(unittest.TestCase):
    def test_an_unresolved_prototype_has_its_interface(self):
        built = Built()
        built.start_proto('Far', extern=True)
        built.proto_field('size', 'SFFloat', 'initializeOnly')
        built.proto_url(['far.x3d#Far'])
        Far = built.end_proto()
        made = built.node('Far', size='2')
        built.end_document()
        self.assertEqual(made.size, 2.0)
        self.assertEqual(protofunctions.getExternalURL(Far), ['far.x3d#Far'])

    def test_with_no_resolver_an_extern_prototype_is_noted(self):
        built = Built()
        built.start_proto('Far', extern=True)
        built.proto_url(['far.x3d'])
        built.end_proto()
        found = problems(built.end_document(), 'info')
        self.assertEqual(len(found), 1)
        self.assertIn('Far', found[0].message)

    def test_an_unresolved_instance_goes_in_children(self):
        """19776-1: a ProtoInstance's containerField is children unless it
        names another; nothing else is known of a node type not yet read"""
        built = Built()
        built.start_proto('Far', extern=True)
        built.proto_url(['far.x3d'])
        built.end_proto()
        group = built.node('Transform', children=[lambda: built.node('Far')])
        shape = built.node('Shape', children=[lambda: built.node('Far')])
        scene = built.end_document()
        self.assertEqual(len(group.children), 1)
        self.assertIs(shape.appearance, node.NULL)
        self.assertIs(shape.geometry, node.NULL)
        self.assertEqual(len(problems(scene, 'error')), 1)

    def test_a_definition_that_arrives_later_reaches_existing_instances(self):
        built = Built()
        built.start_proto('Far', extern=True)
        built.proto_field('size', 'SFFloat', 'initializeOnly')
        built.proto_url(['far.x3d'])
        Far = built.end_proto()
        made = built.node('Far')
        built.end_document()
        definer = Built()
        TestPrototypes().declare(definer)
        Lamp = definer.end_document().getProto('Lamp')
        buildermodule.complete_extern_proto(Far, Lamp)
        self.assertIsInstance(protofunctions.getSceneGraph(made).children[0], x3d.Group)
        self.assertIs(Far.nodeType, x3d.Group)

    def test_a_resolver_supplies_the_definition(self):
        definer = Built()
        TestPrototypes().declare(definer)
        Lamp = definer.end_document().getProto('Lamp')
        asked = []

        def resolve(urls, base, name):
            asked.append((list(urls), base, name))
            return Lamp

        built = Built(extern_resolver=resolve, baseURI='https://example.com/a.x3d')
        built.start_proto('Lamp', extern=True)
        built.proto_url(['lamp.x3d#Lamp'])
        built.end_proto()
        made = built.node('Lamp')
        built.end_document()
        self.assertEqual(asked, [(['lamp.x3d#Lamp'], 'https://example.com/a.x3d', 'Lamp')])
        self.assertIsInstance(protofunctions.getSceneGraph(made).children[0], x3d.Group)

    def test_a_resolver_that_finds_nothing(self):
        built = Built(extern_resolver=lambda _urls, _base, _name: None)
        built.start_proto('Lamp', extern=True)
        built.proto_url(['lamp.x3d'])
        built.end_proto()
        self.assertEqual(len(problems(built.end_document(), 'warning')), 1)


class TestDeclaredFields(unittest.TestCase):
    def test_a_script_declares_fields_of_its_own(self):
        built = Built()
        script = built.b.start_node('Script', DEF='S')
        built.declare_field('speed', 'SFFloat', 'initializeOnly', '2.5')
        built.declare_field('set_time', 'SFTime', 'inputOnly')
        built.declare_field('position', 'SFVec3f', 'outputOnly')
        built.end_node()
        built.node('TimeSensor', DEF='Clock')
        built.route('Clock', 'time', 'S', 'set_time')
        scene = built.end_document()
        self.assertEqual(script.speed, 2.5)
        self.assertIsInstance(script, x3d.Script)
        self.assertNotIn('speed', {f.name for f in protofunctions.getFields(x3d.Script)})
        self.assertEqual(len(scene.routes), 1)
        self.assertEqual([p.severity for p in scene.problems], ['warning'])
        self.assertIn('not run', scene.problems[0].message)

    def test_a_script_declaring_one_of_its_own_fields_is_an_error(self):
        built = Built()
        script = built.b.start_node('Script', DEF='S')
        built.field_text('url', '"a.js"')
        built.declare_field('url', 'MFString', 'inputOutput')
        built.end_node()
        scene = built.end_document()
        self.assertEqual(script.url, ['a.js'])
        self.assertIs(protofunctions.getField(script, 'url'), protofunctions.getField(x3d.Script, 'url'))
        self.assertEqual([p.message for p in scene.problems if p.severity == 'error'],
                         ['Script declares url, a field of its node type'])

    def test_a_script_declares_a_field_its_version_does_not_give_it(self):
        """Script has a description field from X3D 4.0"""
        built = Built()
        built.document('Immersive', '3.3')
        script = built.b.start_node('Script')
        built.declare_field('description', 'MFString', 'initializeOnly', '"a" "b"')
        built.end_node()
        scene = built.end_document()
        self.assertEqual(script.description, ['a', 'b'])
        self.assertEqual([p.message for p in scene.problems if p.severity == 'error'], [])

    def test_a_shape_declares_no_fields(self):
        built = Built()
        built.b.start_node('Shape')
        built.declare_field('speed', 'SFFloat', 'initializeOnly', '2.5')
        built.end_node()
        self.assertEqual(len(problems(built.end_document(), 'error')), 1)


def test_a_prototype_event_field_of_nodes_has_no_default():
    scene = readers.read(b"""<X3D version='3.3'><Scene><ProtoDeclare name='P'><ProtoInterface>
        <field accessType='inputOnly' name='set_m' type='SFNode'/>
        <field accessType='outputOnly' name='ms_changed' type='MFNode'/>
        <field accessType='initializeOnly' name='m' type='SFNode'><Material/></field>
        </ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare></Scene></X3D>""",
                         name='a.x3d')
    assert [str(problem) for problem in scene.problems if problem.severity != 'info'] == []


def test_nodes_given_to_a_prototype_event_field_are_reported():
    scene = readers.read(b"""<X3D version='3.3'><Scene><ProtoDeclare name='P'><ProtoInterface>
        <field accessType='inputOnly' name='set_m' type='SFNode'><Material/></field>
        </ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare></Scene></X3D>""",
                         name='a.x3d')
    assert any('set_m' in str(problem) for problem in scene.problems)


def test_an_attribute_naming_no_field_of_a_prototype_instance_is_reported():
    """`nodeType` is an attribute of every prototype instance's class, not a field"""
    scene = readers.read(b"""<X3D version='3.3'><Scene><ProtoDeclare name='P'><ProtoInterface>
        </ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare>
        <ProtoInstance name='P'><fieldValue name='nodeType' value='Group'/></ProtoInstance>
        </Scene></X3D>""", name='a.x3d')
    assert any('nodeType' in str(problem) for problem in scene.problems)



def test_an_element_attribute_naming_no_field_of_a_prototype_instance_is_reported():
    """A prototype used as an element: its class's `nodeType` is not a field"""
    scene = readers.read(b"""<X3D version='3.3'><Scene><ProtoDeclare name='P'><ProtoInterface>
        </ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare>
        <P nodeType='Group'/></Scene></X3D>""", name='a.x3d')
    assert any('nodeType' in str(problem) for problem in scene.problems)


def test_a_prototype_event_connected_by_is_instantiates():
    scene = readers.read(b"""#VRML V2.0 utf8
PROTO P [ eventIn MFNode addChildren ] { Group { addChildren IS addChildren } }
P {}
""", name='a.wrl')
    assert [str(problem) for problem in scene.problems if problem.severity == 'error'] == []
    assert len(scene.children) == 1


def test_a_prototype_named_as_a_node_keeps_its_own_field_names():
    """A dialect renames the X3D node's fields, not a prototype's of the same name"""
    scene = readers.read(b"""<X3D version='3.0'><Scene>
        <ProtoDeclare name='LoadSensor'><ProtoInterface>
          <field accessType='inputOutput' name='watchList' type='MFNode'/>
        </ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare>
        <ImageTexture DEF='I' url='"a.png"'/>
        <LoadSensor><ImageTexture USE='I' containerField='watchList'/></LoadSensor>
        </Scene></X3D>""", name='a.x3d')
    assert [str(problem) for problem in scene.problems if problem.severity != 'info'] == []
    assert len(scene.children[-1].watchList) == 1


def test_a_name_that_is_no_field_of_the_node_is_reported_as_none():
    scene = readers.read(b"""<X3D version='3.3'><Scene><ProtoDeclare name='P'><ProtoInterface>
        </ProtoInterface><ProtoBody><Group/></ProtoBody></ProtoDeclare>
        <P nodeType='Group'/></Scene></X3D>""", name='a.x3d')
    assert [problem.message for problem in scene.problems] == ['P has no field nodeType']



METADATA_IN_SET = """<X3D version='%s'><Scene><WorldInfo>
    <MetadataSet name='s'><MetadataString name='a' value='"x"'/></MetadataSet>
    </WorldInfo></Scene></X3D>"""


def test_a_metadata_sets_child_is_one_of_its_values_from_4_0():
    found = readers.read((METADATA_IN_SET % '4.0').encode(), name='a.x3d').children[0].metadata
    assert not found.metadata and [type(item).__name__ for item in found.value] == ['MetadataString']


@pytest.mark.parametrize('version', ['3.0', '3.3'])
def test_a_metadata_sets_child_is_its_metadata_in_3_x(version):
    """X3D 3.x's default container for a metadata node is `metadata`"""
    found = readers.read((METADATA_IN_SET % version).encode(), name='a.x3d').children[0].metadata
    assert not found.value and isinstance(found.metadata, x3d.MetadataString)


def test_a_version_writes_a_container_field_where_its_default_differs():
    """Written as 3.3, a metadata node in `value` says so"""
    scene = readers.read((METADATA_IN_SET % '4.0').encode(), name='a.x3d')
    assert 'containerField="value"' in writers.write(scene, 'xml', version='3.3')
    assert 'containerField' not in writers.write(scene, 'xml', version='4.0')


if __name__ == '__main__':
    unittest.main()
