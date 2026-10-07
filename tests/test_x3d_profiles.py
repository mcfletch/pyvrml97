"""X3D's profiles: the tables in `vrml.x3d.profiles` and the record of their
transcription in `specs/x3d/profiles.md` say the same."""

import os
import re
import unittest

from vrml.x3d import profiles

RECORD = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                      'specs', 'x3d', 'profiles.md')


def recorded():
    """Each section of the record's tables, by heading"""
    sections, current = {}, None
    with open(RECORD, encoding='utf-8') as stream:
        for line in stream:
            heading = re.match(r'## (.+)', line)
            if heading:
                current = sections.setdefault(heading.group(1).strip(), {})
                continue
            row = re.match(r'\| (\w+) \| (\d+) \|', line)
            if row and current is not None:
                current[row.group(1)] = int(row.group(2))
    return sections


class TestTheRecord(unittest.TestCase):
    def test_every_profile_is_recorded_as_it_is_held(self):
        sections = recorded()
        for name, profile in profiles.PROFILES.items():
            with self.subTest(profile=name):
                self.assertEqual(sections[name], profile.levels())

    def test_the_highest_levels_are_recorded(self):
        self.assertEqual(recorded()['Highest level of each component'], profiles.COMPONENTS)

    def test_every_profiles_levels_are_within_the_highest(self):
        for name, profile in profiles.PROFILES.items():
            for component, level in profile.levels().items():
                with self.subTest(profile=name, component=component):
                    self.assertLessEqual(level, profiles.COMPONENTS[component])


if __name__ == '__main__':
    unittest.main()
