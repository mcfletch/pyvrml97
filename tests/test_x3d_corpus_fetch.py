"""Web3D's example archives as `vrml.x3d.corpus` extracts them.

The archives here are built in a temporary directory with the layout Web3D's
have, so nothing is downloaded.
"""

import os
import zipfile

import pytest

from vrml.x3d import corpus

PREFIX = 'www.web3d.org/x3d/content/examples/ConformanceNist/'


def archive(tmp_path, members):
    path = tmp_path / 'X3dExamplesConformanceNist.zip'
    with zipfile.ZipFile(path, 'w') as written:
        for name in members:
            written.writestr(name, b'data')
    return str(path)


MEMBERS = [
    PREFIX + 'Geometry/Box/texture.x3d',
    PREFIX + 'Geometry/Box/texture.wrl',
    PREFIX + 'Geometry/Box/texture.html',
    PREFIX + 'Geometry/Box/texture.java',
    PREFIX + 'Geometry/Box/texture-front.jpg',
    PREFIX + 'Geometry/Box/_viewpoints/texture.x3d._VP_Default_viewpoint.png',
    PREFIX + 'Geometry/Box/_viewpoints/texture.x3d._VP_Top_view.png',
    PREFIX + 'Geometry/Box/_thumbnails/textureThumbnail.png',
    PREFIX + 'vts.jpg',
    PREFIX + 'Sounds/movie.mpg',
    PREFIX + 'javadoc/ConformanceNist/index.html',
    PREFIX + 'classes/ConformanceNist/Geometry/Box/texture.class',
    'www.web3d.org/x3d/content/examples/license.html',
]


def extracted(root):
    return sorted(os.path.relpath(os.path.join(path, name), root)
                  for path, _dirs, names in os.walk(root) for name in names)


class TestExtraction:
    def test_the_scenes_and_the_licence(self, tmp_path):
        count = corpus.extract(archive(tmp_path, MEMBERS), str(tmp_path / 'out'))
        assert count == 1
        assert extracted(str(tmp_path / 'out')) == sorted([
            PREFIX + 'Geometry/Box/texture.x3d',
            PREFIX + 'Geometry/Box/texture.wrl',
            'www.web3d.org/x3d/content/examples/license.html',
        ])

    def test_with_the_resources_a_scene_draws_with(self, tmp_path):
        corpus.extract(archive(tmp_path, MEMBERS), str(tmp_path / 'out'), resources=True)
        found = extracted(str(tmp_path / 'out'))
        assert PREFIX + 'Geometry/Box/texture-front.jpg' in found
        assert PREFIX + 'vts.jpg' in found
        assert PREFIX + 'Geometry/Box/_viewpoints/texture.x3d._VP_Top_view.png' in found
        for left_out in ('_thumbnails', 'javadoc', 'classes', '.mpg', '.html', '.java'):
            assert not [name for name in found if left_out in name and 'license' not in name]

    def test_a_member_leaving_the_destination_is_refused(self, tmp_path):
        with pytest.raises(ValueError):
            corpus.extract(archive(tmp_path, ['../escaped.x3d']), str(tmp_path / 'out'))


class TestTheDirectory:
    def test_named_by_the_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv('PYVRML97_X3D_CORPUS', str(tmp_path))
        assert corpus.directory() == str(tmp_path)

    def test_otherwise_in_the_cache(self, monkeypatch, tmp_path):
        monkeypatch.delenv('PYVRML97_X3D_CORPUS', raising=False)
        monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path))
        assert corpus.directory() == os.path.join(str(tmp_path), 'pyvrml97', 'x3d-corpus')

    def test_fetch_extracts_an_archive_already_downloaded(self, tmp_path):
        """Into one tree, as the examples are published, so a scene's references
        into another archive resolve"""
        archive(tmp_path, MEMBERS)
        counts = corpus.fetch(['ConformanceNist'], where=str(tmp_path), resources=True)
        assert counts == {'ConformanceNist': 1}
        assert os.path.exists(tmp_path / PREFIX / 'vts.jpg')

    def test_an_archives_examples(self, tmp_path):
        assert corpus.examples('ConformanceNist', str(tmp_path)) == os.path.join(
            str(tmp_path), *PREFIX.rstrip('/').split('/'))

    def test_the_archives_an_archives_scenes_reach_into(self):
        assert corpus.with_references(['Vrml2Sourcebook']) == [
            'Vrml2Sourcebook', 'X3dForWebAuthors']
        assert corpus.with_references(['X3dForWebAuthors']) == ['X3dForWebAuthors']


class TestWeb3DsRenders:
    def test_each_viewpoints_render_by_name(self, tmp_path):
        corpus.extract(archive(tmp_path, MEMBERS), str(tmp_path / 'out'), resources=True)
        scene = str(tmp_path / 'out' / PREFIX / 'Geometry/Box/texture.x3d')
        renders = corpus.viewpoint_renders(scene)
        assert sorted(renders) == ['Default_viewpoint', 'Top_view']
        assert renders['Top_view'].endswith('texture.x3d._VP_Top_view.png')

    def test_a_viewpoints_render_name(self):
        assert corpus.render_name('Front View') == 'Front_View'
        assert corpus.render_name('extra-large.x3d') == 'extra_large.x3d'
        assert corpus.render_name('Plain_1.x3d') == 'Plain_1.x3d'

    def test_a_scene_without_any(self, tmp_path):
        assert corpus.viewpoint_renders(str(tmp_path / 'nothing.x3d')) == {}
