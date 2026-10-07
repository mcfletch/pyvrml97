"""Web3D's example scenes, read in each encoding they are published in.

Every scene is published as .x3d, .x3dv, .wrl, .json and .x3db. Reading each
X3D encoding builds the graph the XML encoding builds: one test that holds
the readers to one another. The .wrl files are VRML97 translations, which
drop what VRML97 cannot say (X3D-only fields and nodes), so they are held to
reading without errors rather than to the XML graph. `tests/fixtures/x3d-corpus` is a committed subset;
`tools/fetch_x3d_corpus.py` fetches the whole of the ConformanceNist and
Vrml2Sourcebook archives into a cache this test also reads when it is there.
The examples are under the Web3D Consortium Open-Source License
(`tests/fixtures/x3d-corpus/*/license.html`).
"""

import glob
import os
import sys
import unittest

from vrml.x3d import readers, writers
from vrml.x3d.compare import first_difference

HERE = os.path.dirname(os.path.abspath(__file__))
SUBSET = os.path.join(HERE, 'fixtures', 'x3d-corpus')
SCHEMA = os.path.join(HERE, 'fixtures', 'x3d-schema', 'x3d-4.1.xsd')
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tools'))
import fetch_x3d_corpus  # noqa: E402 the tools directory is put on the path above

#: The encodings compared with the XML encoding's graph, by file suffix,
#: with the fields each does not carry: Web3D's ClassicVRML converter writes
#: FontStyle's `style` as a comment.
ENCODINGS = {
    '.json': (),
    '.x3dv': (('FontStyle', 'style'), ('ScreenFontStyle', 'style')),
}

#: Scenes whose translation into an encoding says something else, by suffix:
#: the converter writes a nested MetadataSet's children twice (the STEP
#: scenes), gives a declared MFString with no value one empty string, and
#: rewrites Script source that prints.
CONVERTED_DIFFERENTLY = {
    '.x3dv': (
        'STEP/', 'speed_range', 'speed_scaling', 'ScriptNodeEventOutControl_EcmaScript',
        'ScriptNodeFieldControl_EcmaScript',
        'Figure30_2ScriptBackgroundSelect', 'Figure30_3ScriptSoundActivate',
        'Figure30_5ScriptTorusBuilder',
    ),
}

#: VRML97 files with errors the reader reports: the STEP translations move
#: a metadata field out of its node, and script.wrl routes from names it
#: never defines.
VRML97_ERRORS = ('STEP/', 'Background/script.wrl')


def scenes(directory):
    return sorted(glob.glob(os.path.join(directory, '**', '*.x3d'), recursive=True))


def read(path):
    with open(path, 'rb') as stream:
        return readers.read(stream.read(), name=path)


def errors(scene):
    """The error messages, without the positions that differ between encodings"""
    return [problem.message for problem in scene.problems if problem.severity == 'error']


def lacks(problem):
    """Whether a problem is a node or field the document's version does not have"""
    return ' has no node ' in problem.message or ' has no field ' in problem.message


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
            for suffix, ignore in ENCODINGS.items():
                other = path[:-len('.x3d')] + suffix
                if not os.path.exists(other) or any(
                        name in other for name in CONVERTED_DIFFERENTLY.get(suffix, ())):
                    continue
                with self.subTest(scene=os.path.relpath(other, self.directory)):
                    self.assertIsNone(first_difference(expected, read(other), ignore=ignore))

    def test_each_vrml97_translation_reads_without_an_error(self):
        for path in glob.glob(os.path.join(self.directory, '**', '*.wrl'), recursive=True):
            if any(name in path for name in VRML97_ERRORS + self.KNOWN_ERRORS):
                continue
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                scene = read(path)
                self.assertEqual(scene.version, '2.0')
                self.assertEqual([str(p) for p in scene.problems if p.severity == 'error'], [])


    def test_each_scene_written_in_each_encoding_reads_back_as_itself(self):
        for path in self.paths:
            scene = read(path)
            for encoding in sorted(writers.WRITERS):
                with self.subTest(scene=os.path.relpath(path, self.directory), encoding=encoding):
                    again = readers.read(writers.write(scene, encoding).encode('utf-8'), name=path)
                    # What reading refused is not in the scene, so is not written.
                    self.assertLessEqual(set(errors(again)), set(errors(scene)))
                    self.assertIsNone(first_difference(scene, again))

    def test_each_scene_written_as_xml_is_valid_against_the_schema(self):
        from lxml import etree  # noqa: PLC0415 a test-only dependency
        schema = etree.XMLSchema(etree.parse(SCHEMA))
        parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)
        for path in self.paths:
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                text = writers.write(read(path), 'xml', version='4.1', canonical=True)
                self.assertTrue(schema.validate(etree.fromstring(text.encode('utf-8'), parser)),
                                schema.error_log)

    def test_each_vrml97_translation_written_as_vrml97_reads_back_as_itself(self):
        for path in glob.glob(os.path.join(self.directory, '**', '*.wrl'), recursive=True):
            scene = read(path)
            if errors(scene) or any(lacks(problem) for problem in scene.problems):
                continue
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                text = writers.write(scene, 'classic')
                self.assertTrue(text.startswith('#VRML V2.0 utf8\n'))
                again = readers.read(text.encode('utf-8'), name=path)
                self.assertEqual(errors(again), [])
                self.assertIsNone(first_difference(scene, again, header=False))


class TestTheCommittedSubset(CorpusTests, unittest.TestCase):
    directory = SUBSET

    def test_the_subset_is_there(self):
        self.assertGreaterEqual(len(self.paths), 25)


class TestTheFetchedCorpus(CorpusTests, unittest.TestCase):
    directory = fetch_x3d_corpus.corpus_directory()


if __name__ == '__main__':
    unittest.main()
