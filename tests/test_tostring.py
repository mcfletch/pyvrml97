import unittest
import os
from vrml.vrml97.parser import buildParser
from vrml.vrml97.scenegraph import SceneGraph

HERE = os.path.dirname(os.path.abspath(__file__))

# to prevent issues if more than one file uses a .wrl or if they somehow use recursive inlines
ALREADY_PROCESSED = []

VRMLPARSER = buildParser()

depth = 0


class TestToString(unittest.TestCase):

    def parsed_content(self, source):
        parser = buildParser()
        result = parser.parse(source)
        success, result, parsed = result
        if not success:
            raise RuntimeError("Did not finish parse")
        if parsed < len(source):
            raise RuntimeError("Partial parse %d/%d characters" % (parsed, len(source)))
        scene = result[1]
        assert isinstance(scene, SceneGraph), scene
        return scene

    def test_to_string_simple(self):
        source = open(os.path.join(HERE, 'fixtures', 'proto_is_simple.wrl')).read()
        scene = self.parsed_content(source)
        assert len(scene.children) == 1, scene.children
        content = scene.toString()
        assert 'PROTO' in content, content
        assert 'X {' in content, content  # TODO: relies on default formatting...

    def test_to_string_spec_file(self):
        source = open(os.path.join(HERE, 'fixtures', 'exampleD.2.wrl')).read()
        scene = self.parsed_content(source)
        content = scene.toString()
        assert 'Material' in content, content
