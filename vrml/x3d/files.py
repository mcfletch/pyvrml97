"""Reading X3D and VRML documents from files and strings

`load(path)` and `loads(data)` read any encoding. An EXTERNPROTO naming a
file beside the document is read from there; nothing is fetched over a
network, which is the application's to do through `extern_resolver`.
"""

import os
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from vrml import node
from vrml.x3d import readers
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

