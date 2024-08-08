import unittest, os
from vrml.vrml97.parser import buildParser
from vrml.vrml97.basenodes import Transform
from vrml.vrml97.shaders import (
    ShaderGeometry,
    Shader,
    ShaderAttribute,
    GLSLObject,
    FloatUniform,  # not functional, but ok
)
from vrml.vrml97.scenegraph import SceneGraph
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# to prevent issues if more than one file uses a .wrl or if they somehow use recursive inlines
ALREADY_PROCESSED = []

VRMLPARSER = buildParser()

depth = 0


def fixup_vrml(file: str):
    global depth
    depth += 1
    file_display = os.path.basename(file)
    depth_indicator = "-" * depth
    print(depth_indicator, "Opening", file_display, "...")
    with open(file, 'rb') as f:
        cn = charset_normalizer.from_fp(f)
        cs = cn.best()
        print(
            depth_indicator,
            "Charset detected as",
            cs.encoding,
            f"(aka {'/'.join(cs.encoding_aliases)})",
        )
        wrldata = str(cs)
    print(depth_indicator, "Parsing", file_display, "...")
    wrl = VRMLPARSER.parse(wrldata)[1][1]  # type: SceneGraph
    print(depth_indicator, "Scanning", file_display, "...")
    fixup_node(wrl)
    print(depth_indicator, "Fixed", fixed_verts_stack[-1], "verts")
    if fixed_verts_stack[-1] > 0:
        print(depth_indicator, "Saving", file_display, "...")
        wrldata = wrl.toString()
        with open(file, 'w') as f:
            f.write(wrldata)
    depth -= 1


class TestToString(unittest.TestCase):
    def test_to_string_simple(self):
        source = open(os.path.join(HERE, 'fixtures', 'proto_is_simple.wrl')).read()
        result = VRMLPARSER.parse(source)
        success, result, parsed = result
        if not success:
            raise RuntimeError("Did not finish parse")
        if parsed < len(source):
            raise RuntimeError("Partial parse %d/%d characters" % (parsed, len(source)))
        scene = result[1]
        assert isinstance(scene, SceneGraph), scene
        assert len(scene.children) == 1, scene.children
        content = scene.toString()
        assert 'PROTO' in content, content
        assert 'X {' in content, content  # TODO: relies on default formatting...
