"""HAnim's standard names, `vrml.x3d.hanimnames`, generated from the X3DUOM.

These read the checked-in module, so they run offline.
"""

import unittest

from vrml.x3d import hanimnames
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
