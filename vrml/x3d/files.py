"""Reading and writing X3D and VRML documents as files and strings

`load(path)` and `loads(data)` read any encoding. An EXTERNPROTO naming a
local file is read from there, relative to the document; nothing is fetched
over a network unless the application passes an `extern_resolver` that does.
`dump(scene, path)` and `dumps(scene)` write a scene.
"""

import gzip
import os
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from vrml import node
from vrml.x3d import nodes as x3d
from vrml.x3d import readers, writers
from vrml.x3d.scene import X3DScene

#: How deep EXTERNPROTO files may name further EXTERNPROTO files.
MAX_PROTOTYPE_DEPTH = 8


class LocalPrototypes:
    """Resolves EXTERNPROTO URLs that name local files, relative to the document

    Each file is read once per load, and a file being read is not read again
    from within itself.
    """

    def __init__(self, options: "dict[str, Any]", depth: int = 0) -> None:
        self.options = options
        self.depth = depth
        self.scenes: "dict[str, X3DScene | None]" = {}

    def __call__(self, urls: Sequence[str], base: str, name: str) -> "type | None":
        if self.depth >= MAX_PROTOTYPE_DEPTH:
            return None
        for url in urls:
            parts = urlsplit(url)
            if parts.scheme not in ('', 'file') or not parts.path:
                continue
            path = parts.path
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(base), path)
            path = os.path.normpath(path)
            scene = self._scene(path)
            if scene is None:
                continue
            found = scene.getProto(parts.fragment or name)
            if found is not None and found not in node.PENDING_PROTOTYPES:
                return found
        return None

    def _scene(self, path: str) -> "X3DScene | None":
        if path in self.scenes:
            return self.scenes[path]
        self.scenes[path] = None
        if not os.path.isfile(path):
            return None
        with open(path, 'rb') as stream:
            data = stream.read()
        options = dict(self.options)
        options['extern_resolver'] = LocalPrototypes(self.options, self.depth + 1)
        self.scenes[path] = readers.read(data, name=path, **options)
        return self.scenes[path]


def load(path: "str | os.PathLike[str]", **options: Any) -> X3DScene:
    """The scene the document at `path` builds

    options -- passed to `SceneBuilder`: prototypes, strict, and
        extern_resolver, which replaces the local-file resolver
    """
    name = os.fspath(path)
    with open(name, 'rb') as stream:
        data = stream.read()
    if 'extern_resolver' not in options:
        resolver = LocalPrototypes(dict(options))
        resolver.scenes[os.path.normpath(name)] = None
        options['extern_resolver'] = resolver
    return readers.read(data, name=name, **options)


def loads(data: "bytes | str", name: str = '', **options: Any) -> X3DScene:
    """The scene a document in memory builds; `name` is its base for URLs"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    if name:
        options.setdefault('extern_resolver', LocalPrototypes(dict(options)))
    return readers.read(data, name=name, **options)



def dumps(
    scene: X3DScene,
    encoding: str = 'xml',
    version: "str | None" = None,
    canonical: bool = False,
) -> str:
    """Return the scene as document text; see `vrml.x3d.writers.write`"""
    return writers.write(scene, encoding, version=version, canonical=canonical)


def dump(
    scene: X3DScene,
    path: "str | os.PathLike[str]",
    encoding: "str | None" = None,
    version: "str | None" = None,
    canonical: bool = False,
) -> None:
    """Write the scene to `path`

    The encoding comes from the suffix where not given: .x3d, .x3dv, .json
    or .x3dj, and .wrl, which is VRML97. A suffix ending in z (.x3dz,
    .x3dvz, .wrz) is gzip-compressed. Nothing is written if the scene cannot
    be written; an existing file is replaced only when the new one is
    complete.
    """
    name = os.fspath(path)
    suffix = os.path.splitext(name.lower())[1]
    if encoding is None:
        encoding = readers.SUFFIXES.get(suffix)
        if encoding is None or encoding not in writers.WRITERS:
            raise ValueError('No writer for files named %r' % name)
    if version is None:
        if suffix in ('.wrl', '.wrz'):
            version = '2.0'
        elif scene.version == '2.0':
            version = x3d.X3D_VERSION
    data = dumps(scene, encoding, version=version, canonical=canonical).encode('utf-8')
    if suffix.endswith('z'):
        data = gzip.compress(data, mtime=0)
    staging = name + '.part'
    with open(staging, 'wb') as stream:
        stream.write(data)
    os.replace(staging, name)
