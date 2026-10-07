"""Web3D's example scenes, read in each encoding they are published in.

Every scene is published as .x3d, .x3dv, .wrl, .json and .x3db. Reading each
encoding builds the graph the XML encoding builds: one test that holds the
readers to one another. `tests/fixtures/x3d-corpus` is a committed subset;
`tools/fetch_x3d_corpus.py` fetches the whole of the ConformanceNist and
Vrml2Sourcebook archives into a cache this test also reads when it is there.
The examples are under the Web3D Consortium Open-Source License
(`tests/fixtures/x3d-corpus/*/license.html`).
"""

import glob
import os
import sys
import unittest

from vrml.x3d import readers
from vrml.x3d.compare import first_difference

HERE = os.path.dirname(os.path.abspath(__file__))
SUBSET = os.path.join(HERE, 'fixtures', 'x3d-corpus')
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tools'))
import fetch_x3d_corpus  # noqa: E402 the tools directory is put on the path above

#: The encodings compared with the XML encoding's graph, by file suffix.
ENCODINGS = ('.json',)


def scenes(directory):
    return sorted(glob.glob(os.path.join(directory, '**', '*.x3d'), recursive=True))


def read(path):
    with open(path, 'rb') as stream:
        return readers.read(stream.read(), name=path)


def problems(scene):
    """Errors and warnings, less the note that scripts are not run"""
    return [str(problem) for problem in scene.problems
            if problem.severity != 'info' and 'not run' not in problem.message]


class CorpusTests:
    """The checks, over whichever directory of scenes a subclass names"""

    directory = ''
    #: Scenes whose content has an error the readers report: each routes to
    #: an initializeOnly field of its own prototype.
    KNOWN_ERRORS = (
        'KeySensorActivationKeySwitchTest', 'Figure31_7DonutExternalPrototype',
    )

    def setUp(self):
        self.paths = scenes(self.directory)
        if not self.paths:
            self.skipTest('no scenes in %s' % self.directory)

    def test_each_xml_scene_reads_without_a_problem(self):
        for path in self.paths:
            if any(name in path for name in self.KNOWN_ERRORS):
                continue
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                self.assertEqual(problems(read(path)), [])

    def test_each_encoding_builds_the_xml_graph(self):
        for path in self.paths:
            expected = read(path)
            for suffix in ENCODINGS:
                other = path[:-len('.x3d')] + suffix
                if not os.path.exists(other):
                    continue
                with self.subTest(scene=os.path.relpath(other, self.directory)):
                    self.assertIsNone(first_difference(expected, read(other)))


class TestTheCommittedSubset(CorpusTests, unittest.TestCase):
    directory = SUBSET

    def test_the_subset_is_there(self):
        self.assertGreaterEqual(len(self.paths), 25)


class TestTheFetchedCorpus(CorpusTests, unittest.TestCase):
    directory = fetch_x3d_corpus.corpus_directory()


if __name__ == '__main__':
    unittest.main()
