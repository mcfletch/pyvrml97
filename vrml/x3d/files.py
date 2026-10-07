"""Reading and writing X3D and VRML documents as files and strings

`load(path)` and `loads(data)` read any encoding. An EXTERNPROTO naming a
local file is read from there, relative to the document; nothing is fetched
over a network unless the application passes an `extern_resolver` that does.
`dump(scene, path)` and `dumps(scene)` write a scene.
"""

import contextlib
import gzip
import os
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, BinaryIO
from urllib.parse import urlsplit

from vrml import node
from vrml.x3d import nodes as x3d
from vrml.x3d import readers, writers
from vrml.x3d.builder import ExternResolver
from vrml.x3d.scene import X3DScene

@contextlib.contextmanager
def staged(path: str) -> "Iterator[BinaryIO]":
    """A file to write `path` through: written beside it, moved over it when
    the block ends, and removed where the block raises"""
    staging = path + '.part'
    try:
        with open(staging, 'wb') as stream:
            yield stream
        os.replace(staging, path)
    except BaseException:
        if os.path.exists(staging):
            os.remove(staging)
        raise


#: How deep EXTERNPROTO files may name further EXTERNPROTO files.
MAX_PROTOTYPE_DEPTH = 8


class LocalPrototypes:
    """Resolves EXTERNPROTO URLs that name local files, relative to the document

    Each file is read once per load: the resolvers a load makes for the files
    it reads share one table of them, by path. A file still being read is in
    the table with no scene, so a file naming it does not read it again.
    """

    def __init__(
        self,
        options: "dict[str, Any]",
        depth: int = 0,
        scenes: "dict[str, X3DScene | None] | None" = None,
    ) -> None:
        self.options = options
        self.depth = depth
        self.scenes: "dict[str, X3DScene | None]" = {} if scenes is None else scenes

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
        options['extern_resolver'] = LocalPrototypes(self.options, self.depth + 1, self.scenes)
        self.scenes[path] = readers.read(data, name=path, **options)
        return self.scenes[path]


def load(
    path: "str | os.PathLike[str]",
    *,
    prototypes: "Mapping[str, type] | None" = None,
    strict: bool = False,
    extern_resolver: "ExternResolver | None" = None,
) -> X3DScene:
    """The scene the document at `path` builds

    prototypes, strict -- as `SceneBuilder` takes them
    extern_resolver -- as `SceneBuilder` takes it, in place of the
        local-file resolver
    """
    name = os.fspath(path)
    with open(name, 'rb') as stream:
        data = stream.read()
    options: "dict[str, Any]" = {'prototypes': prototypes, 'strict': strict}
    if extern_resolver is None:
        resolver = LocalPrototypes(options)
        resolver.scenes[os.path.normpath(name)] = None
        extern_resolver = resolver
    return readers.read(data, name=name, extern_resolver=extern_resolver, **options)


def loads(
    data: "bytes | str",
    name: str = '',
    *,
    prototypes: "Mapping[str, type] | None" = None,
    strict: bool = False,
    extern_resolver: "ExternResolver | None" = None,
) -> X3DScene:
    """The scene a document in memory builds; `name` is its base for URLs

    Text is read as the characters it is, whatever encoding an XML
    declaration in it names. The keywords are `load`'s; the local-file
    resolver is used where there is a `name` to resolve against.
    """
    options: "dict[str, Any]" = {'prototypes': prototypes, 'strict': strict}
    if extern_resolver is None and name:
        extern_resolver = LocalPrototypes(options)
    if isinstance(data, str):
        return readers.read(data.removeprefix('\ufeff').encode('utf-8'), name=name,
                            charset='utf-8', extern_resolver=extern_resolver, **options)
    return readers.read(data, name=name, extern_resolver=extern_resolver, **options)



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
    with staged(name) as stream:
        stream.write(data)
