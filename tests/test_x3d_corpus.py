"""Web3D's example scenes, read in each encoding they are published in.

Every scene is published as .x3d, .x3dv, .wrl, .json and .x3db. Reading each
X3D encoding builds the graph the XML encoding builds: one test that holds
the readers to one another. The .wrl files are VRML97 translations, which
drop what VRML97 cannot say (X3D-only fields and nodes), so they are held to
reading without errors rather than to the XML graph. `tests/fixtures/x3d-corpus` is a committed subset;
`tools/fetch_x3d_corpus.py` fetches whole archives into a cache this test
also reads, every archive in it, when it is there.
The examples are under the Web3D Consortium Open-Source License
(`tests/fixtures/x3d-corpus/*/license.html`).
"""

import glob
import os
import unittest

from vrml.x3d import corpus, readers, writers
from vrml.x3d.compare import first_difference

HERE = os.path.dirname(os.path.abspath(__file__))
SUBSET = os.path.join(HERE, 'fixtures', 'x3d-corpus')
SCHEMA = os.path.join(HERE, 'fixtures', 'x3d-schema', 'x3d-4.1.xsd')

#: The encodings compared with the XML encoding's graph, by file suffix,
#: with the fields each does not carry: Web3D's ClassicVRML converter writes
#: FontStyle's `style` as a comment.
ENCODINGS = {
    '.json': (),
    '.x3dv': (('FontStyle', 'style'), ('ScreenFontStyle', 'style')),
}

#: Scenes whose translation into an encoding says something else, by suffix.
#: The ClassicVRML converter writes a nested MetadataSet's children twice (the
#: STEP scenes) or before the nodes they USE (MetadataNodeExamples), gives a
#: declared MFString with no value one empty string (speed_*, the fish,
#: TextString and CircleFishLod prototypes), and splits an unquoted MFString differently (XmpMetadata).
#: The JSON converter collapses runs of spaces in strings and empties the
#: blank lines of Script source.
CONVERTED_DIFFERENTLY = {
    '.x3dv': (
        'STEP/', 'speed_range', 'speed_scaling', 'FishPrototype', 'SeaStarPrototype',
        'PositionInterpolatorPrototype', 'MetadataNodeExamplesX3D', 'XmpMetadataEmbedded',
        'TextStringPrototype', 'CircleFishLodPrototype',
    ),
    '.json': (
        'TextHaveFunWithX3D', 'TextSpecialCharacters', 'IntroductionMessage',
        'ElevationGridSimpleWaveAnimation', 'ChangingFog', 'BindingOperations',
        'MaterialModulatorPrototypeExpanded', 'Chapter14Prototypes/MaterialModulator.',
    ),
}

#: What the ClassicVRML converter writes in place of Script source that prints.
REWRITTEN_SCRIPT = b'### X3D Browser.print() not supported'


def converted_differently(path, suffix):
    """Whether the converter's translation of a scene into `suffix` says something else"""
    if any(name in path for name in CONVERTED_DIFFERENTLY.get(suffix, ())):
        return True
    with open(path, 'rb') as stream:
        return REWRITTEN_SCRIPT in stream.read()

#: The values Web3D's .x3db files write a second time under a name their
#: node does not take: an Anchor's url, an Inline's bboxSize, a LOD's range,
#: a Viewpoint's centerOfRotation, and a NurbsPatchSurface's weights.
DOUBLED_IN_BINARY = (
    'Anchor.autoRefresh', 'Anchor.load', 'Anchor.visible', 'Inline.visible',
    'LOD.forceTransitions', 'Viewpoint.retainUserOffsets', 'NurbsPatchSurface.solid',
)

#: VRML97 files with errors the reader reports: the STEP translations move
#: a metadata field out of its node, script.wrl routes from names it never
#: defines, the X3dForWebAuthors translations keep X3D's metadata fields, and
#: MaterialModulator routes from an EXTERNPROTO's field, and
#: test-binding2Translated routes an SFTime to a Script's SFBool eventIn.
VRML97_ERRORS = ('STEP/', 'Background/script.wrl', 'EmptySceneCoreProfile',
                 'MetadataNodeExamplesX3D', 'WorldInfoExample', 'MaterialModulator',
                 'test-binding2Translated')


def scenes(directory):
    return sorted(glob.glob(os.path.join(directory, '**', '*.x3d'), recursive=True))


def read(path):
    with open(path, 'rb') as stream:
        return readers.read(stream.read(), name=path)


def errors(scene):
    """The error messages, without the positions that differ between encodings"""
    return [problem.message for problem in scene.problems if problem.severity == 'error']


#: What reading says of a DEF name the XML and JSON encodings do not allow.
NOT_AN_XML_NAME = ' is not an XML name'


def written(test, scene, encoding, **options):
    """The scene written in `encoding`, or None where the writer refuses
    only what reading reported: a node or field the version lacks, or a DEF
    name the XML and JSON encodings do not allow"""
    try:
        return writers.write(scene, encoding, **options)
    except writers.X3DWriteError as error:
        reported = {problem.message for problem in scene.problems}
        reported |= {message[:-len(NOT_AN_XML_NAME)] for message in reported
                     if message.endswith(NOT_AN_XML_NAME)}
        refused = {problem.split(' cannot be written')[0] for problem in error.problems}
        test.assertLessEqual(refused, reported, error.problems)
        return None


def lacks(problem):
    """Whether a problem is a node, field or field type the document's version does not have"""
    return any(words in problem.message
               for words in (' has no node ', ' has no field ', ' has no field type '))


def problems(scene):
    """Errors and warnings, less the note that scripts are not run and the
    warnings that an MFString value is not quoted

    Thousands of the Savage, Basic and HumanoidAnimation scenes write a single
    url or geoSystem without the quotes the XML encoding asks for; the reader
    reads them as one string and says so, and a misread string would show in
    the graphs the other encodings build.
    """
    return [str(problem) for problem in scene.problems
            if problem.severity != 'info' and 'not run' not in problem.message
            and 'value not quoted' not in problem.message]


#: Scenes of the larger archives with faults of their own, which the reader
#: reports, by part of their path.
AUTHORING_FAULTS = (
    # Deliberately faulty: Basic/development's tests of validators and
    # diagnostics, X3dRetreatProtoExercise's undeclared field types, and the
    # CAD alternatives that show what CADPart and CADFace do not allow.
    'development/Test', 'X3dRetreatProtoExercise', 'CADPartChildTransformationAlternative',
    # Drafts and conversions kept as they were: originals folders, an Office
    # export's files, and a converter's Cesium skin with its own node types.
    '/originals/', '_files/', 'CesiumManCastleOnlineConverter',
    # Lattice's XVL nodes, which are not X3D, and Xj3D's own components.
    'LatticeXvl/', 'basic_point_sprites', 'CarDemoMain',
    # Prototypes shadowing X3D nodes with EXTERNPROTOs the scene does not
    # load, and prototypes of DIS nodes whose fields are events.
    'MetadataExamples', 'RadioCommunicationsPrototypes', 'QuadTreeExamples',
    'SpinGroupInternalSubsetDeclaration',
    # Fields, routes and USE that the scene gets wrong: a ROUTE or USE naming a
    # DEF the scene does not have before it, between fields of different types, to an
    # event by its bare name or from a field the node lacks; a USE given
    # fields or naming another node type; a DEF given twice; an IS between
    # fields of different types or access.
    'NurbsPrototypes', 'newGeospatialScene', 'Trebuchet', 'TwoLeggedTablePrototype',
    'BooleanSequencerPrototype', 'EventUtilityPrototypes', 'LODlevelChangedExample',
    'MetadataPrototypes', 'ViewpointGroupPrototype', 'JinLOA4MarkersAnimated',
    'JinFacsAu12LipCornerPullerMorpher', 'JinFacsAu25LipsPartMorpher',
    'BvhConversion1Illustrated', 'HAnimDisplacerExamples',
    'HAnimPosePrototype', 'AllenStandShootRifleM24',
    'InterchangableActorsViaDynamicRoutingPrototypes', 'WinterAndSpring/FlowerGardens',
    'UHRB/Hospital', 'SeaWebBuoyExample', 'SeaWebBuoyPrototype', 'CampPendletonRaidWithRez',
    'NancyTeamAddRoutes', 'Sovremenny-initial/Superstructure',
    'Sovremenny-initial/YardArm', 'PatrolCraftNavalAcademyBrazil/Propeller',
    'ColorSequencerPrototype', 'PointTrackGeneratorPrototype5', 'PushButtonPrototype',
    'DTEDMultiGrid', 'DTEDSingleGrid', 'PajekVisualizationPrototypes',
    'ParallelepipedPrototype', 'MultiTextureTeapot', 'SplitChannels',
)


class CorpusTests:
    """The checks, over whichever directory of scenes a subclass names"""

    directory = ''
    #: Scenes whose content has a problem the readers report: the first two
    #: route to an initializeOnly field of their own prototype, and
    #: XmpMetadataEmbedded gives MFString values without quotes.
    KNOWN_ERRORS = (
        'KeySensorActivationKeySwitchTest', 'Figure31_7DonutExternalPrototype',
        'XmpMetadataEmbedded',
    )

    def setUp(self):
        self.paths = scenes(self.directory)
        if not self.paths:
            self.skipTest('no scenes in %s' % self.directory)

    def test_each_xml_scene_reads_without_a_problem(self):
        for path in self.paths:
            if any(name in path for name in self.KNOWN_ERRORS + AUTHORING_FAULTS):
                continue
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                self.assertEqual(problems(read(path)), [])

    def test_each_encoding_builds_the_xml_graph(self):
        for path in self.paths:
            expected = read(path)
            for suffix, ignore in ENCODINGS.items():
                other = path[:-len('.x3d')] + suffix
                if not os.path.exists(other) or converted_differently(other, suffix):
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


    def test_each_binary_scene_reads(self):
        """The .x3db files are earlier revisions of their scenes than the
        .x3d beside them, so are held to reading rather than to its graph"""
        for path in glob.glob(os.path.join(self.directory, '**', '*.x3db'), recursive=True):
            with open(path, 'rb') as stream:
                data = stream.read()
            if not data or not data.endswith(b'\xff'):
                continue                        # published empty, or cut short
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                scene = readers.read(data, name=path)
                self.assertEqual([message for message in errors(scene)
                                  if not any(name in message for name in DOUBLED_IN_BINARY)], [])

    def test_each_scene_written_in_each_encoding_reads_back_as_itself(self):
        for path in self.paths:
            scene = read(path)
            for encoding in sorted(writers.WRITERS):
                with self.subTest(scene=os.path.relpath(path, self.directory), encoding=encoding):
                    text = written(self, scene, encoding)
                    if text is None:
                        continue
                    again = readers.read(text.encode('utf-8'), name=path)
                    # What reading refused is not in the scene, so is not written.
                    self.assertLessEqual(set(errors(again)), set(errors(scene)))
                    self.assertIsNone(first_difference(scene, again))

    def test_each_scene_written_as_xml_is_valid_against_the_schema(self):
        from lxml import etree  # noqa: PLC0415 a test-only dependency
        schema = etree.XMLSchema(etree.parse(SCHEMA))
        # huge_tree: GrampsAnimations writes one text node past libxml2's default limit.
        parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False,
                                 huge_tree=True)
        for path in self.paths:
            with self.subTest(scene=os.path.relpath(path, self.directory)):
                text = written(self, read(path), 'xml', version='4.1', canonical=True)
                if text is None:
                    continue
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
    directory = corpus.directory()


if __name__ == '__main__':
    unittest.main()
