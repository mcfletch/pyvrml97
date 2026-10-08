"""HAnim's standard names, `vrml.x3d.hanimnames`, generated from the X3DUOM.

These read the checked-in module, so they run offline.
"""

import unittest

from vrml.x3d import hanimnames, readers
from vrml.x3d import nodes as x3d


class TestJoints(unittest.TestCase):
    def test_each_joint_has_its_level_of_articulation(self):
        self.assertEqual(hanimnames.JOINT_LOA['humanoid_root'], 0)
        self.assertEqual(hanimnames.JOINT_LOA['l_knee'], 1)
        self.assertEqual(hanimnames.JOINT_LOA['vc1'], 3)
        self.assertEqual(hanimnames.JOINT_LOA['l_talocalcaneonavicular'], 4)

    def test_each_joint_but_the_root_has_a_parent(self):
        self.assertNotIn('humanoid_root', hanimnames.JOINT_PARENT)
        self.assertEqual(hanimnames.JOINT_PARENT['l_knee'], 'l_hip')
        self.assertEqual(hanimnames.JOINT_PARENT['skullbase'], 'vc1')

    def test_an_alias_names_its_joint(self):
        self.assertEqual(hanimnames.JOINT_ALIASES['l_ankle'], 'l_talocrural')

    def test_a_default_center_is_a_point(self):
        self.assertEqual(hanimnames.JOINT_CENTER['humanoid_root'], (0.0, 0.824, 0.0277))

    def test_every_name_the_declaration_offers_is_listed(self):
        self.assertEqual(set(hanimnames.JOINT_LOA), set(x3d.HAnimJoint.name.choices))
        self.assertEqual(set(hanimnames.SEGMENT_LOA), set(x3d.HAnimSegment.name.choices))
        self.assertEqual(set(hanimnames.SITE_LOA), set(x3d.HAnimSite.name.choices))


class TestSegmentsAndSites(unittest.TestCase):
    def test_a_segment_hangs_from_a_joint(self):
        self.assertEqual(hanimnames.SEGMENT_PARENT['pelvis'], 'sacroiliac')
        self.assertEqual(hanimnames.SEGMENT_LOA['pelvis'], 1)

    def test_a_site_lies_on_a_segment(self):
        self.assertEqual(hanimnames.SITE_PARENT['skull_vertex'], 'skull')
        self.assertEqual(hanimnames.SITE_LOA['skull_vertex'], 1)
        self.assertEqual(hanimnames.SITE_ALIASES['skull_tip'], 'skull_vertex')


if __name__ == '__main__':
    unittest.main()


class TestWhatAJointHolds(unittest.TestCase):
    def test_a_joint_holds_sites_and_markers(self):
        scene = readers.read(b'''<X3D version="4.0"><Scene><HAnimHumanoid>
          <HAnimJoint containerField="skeleton" name="humanoid_root">
            <HAnimSite name="crotch"/><Transform><Shape/></Transform>
          </HAnimJoint>
          <LOD containerField="skin"><Shape/></LOD>
        </HAnimHumanoid></Scene></X3D>''', encoding='xml')
        self.assertEqual([p for p in scene.problems if p.severity == 'error'], [])
        humanoid = scene.children[0]
        self.assertEqual([type(c).__name__ for c in humanoid.skeleton[0].children],
                         ['HAnimSite', 'Transform'])
        self.assertEqual([type(c).__name__ for c in humanoid.skin], ['LOD'])


class TestPoses(unittest.TestCase):
    def test_a_fraction_is_routed_to_a_pose(self):
        scene = readers.read(b'''<X3D version="4.1"><Scene>
          <ScalarInterpolator DEF="I" key="0 1" keyValue="0 1"/>
          <HAnimPose DEF="P"/>
          <ROUTE fromNode="I" fromField="value_changed" toNode="P" toField="set_fraction"/>
        </Scene></X3D>''', encoding='xml')
        self.assertEqual([p for p in scene.problems if p.severity == 'error'], [])
