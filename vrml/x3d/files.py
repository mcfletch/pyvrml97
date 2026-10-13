"""Reading and writing X3D and VRML documents as files and strings

`load(path)` and `loads(data)` read any encoding. An EXTERNPROTO naming a
file under the document's folder is read from there (`LocalPrototypes`); an
application reads prototypes from anywhere else by passing an
`extern_resolver`, for which `ExternPrototypes` is the base class.
`dump(scene, path)` and `dumps(scene)` write a scene.
"""

import contextlib
import copy
import gzip
import os
from collections.abc import Mapping, Sequence, Generator
from typing import BinaryIO
from urllib.parse import unquote, urlsplit

from vrml import node, protofunctions
from vrml.x3d import nodes as x3d
from vrml.x3d import readers, writers
from vrml.x3d.builder import ExternResolver
from vrml.x3d.scene import X3DScene

@contextlib.contextmanager
def staged(path: str) -> "Generator[BinaryIO]":
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

#: The largest file `LocalPrototypes` reads, in bytes.
MAX_PROTOTYPE_BYTES = 64 * 1024 * 1024


def contained_path(
    reference: str,
    base: str,
    root: "str | os.PathLike[str] | None" = None,
) -> "str | None":
    """The real path of the file `reference` names beside the document at
    `base`; None for a reference that leads anywhere else

    The file is under the document's folder, or under `root` where one is
    given, after symbolic links are followed. A reference with a URL scheme
    or a host, an absolute path, and a document with no location name no
    file. Percent-escapes are decoded.
    """
    if not base:
        return None
    parts = urlsplit(reference)
    relative = unquote(parts.path)
    if parts.scheme or parts.netloc or not relative or '\0' in relative:
        return None
    if os.path.isabs(relative) or os.path.splitdrive(relative)[0]:
        return None
    folder = os.path.realpath(os.path.dirname(base))
    bound = folder if root is None else os.path.realpath(root)
    path = os.path.realpath(os.path.join(folder, relative))
    if path != bound and not path.startswith(os.path.join(bound, '')):
        return None
    return path


def first_prototype(scene: X3DScene) -> "type | None":
    """The first prototype `scene` declares, external prototypes passed over;
    None for none

    An EXTERNPROTO URL with no ``#name`` names it (19775-1 4.9.3), whatever
    its name.
    """
    for prototype in scene.protoTypes.values():
        if not protofunctions.getExternalURL(prototype):
            found: type = prototype
            return found
    return None


class ExternPrototypes:
    """Resolves EXTERNPROTO URLs to the prototypes the files they name declare

    A subclass says where a reference leads (`locate`) and reads it (`read`);
    an instance is the `extern_resolver` of a load. A URL's ``#name`` says
    which of the file's prototypes it is, and with none it is the file's
    first. Each file is read once per load, by its location: one still being
    read is in `scenes` with no scene, so a file naming it does not read it
    again. A file naming prototypes in other files is read the same way, to
    `MAX_PROTOTYPE_DEPTH` files deep.

    prototypes, strict -- as `SceneBuilder` takes them, for each file read
    """

    def __init__(
        self,
        prototypes: "Mapping[str, type] | None" = None,
        strict: bool = False,
    ) -> None:
        self.prototypes = prototypes
        self.strict = strict
        self.depth = 0
        #: The scene each file read gave, by location.
        self.scenes: "dict[str, X3DScene | None]" = {}

    def locate(self, reference: str, base: str) -> "str | None":
        """Where `reference` leads from the document at `base`, as the name
        its file is known by; None for a reference that is not to be read

        reference -- an EXTERNPROTO URL without its ``#name``
        """
        raise NotImplementedError

    def read(self, reference: str, base: str) -> "bytes | None":
        """The document `reference` leads to, which `locate` gave a location
        for; None where it cannot be read"""
        raise NotImplementedError

    def __call__(self, urls: Sequence[str], base: str, name: str) -> "type | None":  # noqa: ARG002 ExternResolver's signature; the file, not this name, says which prototype
        if self.depth >= MAX_PROTOTYPE_DEPTH:
            return None
        for url in urls:
            reference, _, fragment = str(url).partition('#')
            if not reference:
                continue
            scene = self._scene(reference, base)
            if scene is None:
                continue
            found = scene.getProto(fragment) if fragment else first_prototype(scene)
            if found is not None and found not in node.PENDING_PROTOTYPES:
                return found
        return None

    def _scene(self, reference: str, base: str) -> "X3DScene | None":
        location = self.locate(reference, base)
        if location is None:
            return None
        if location not in self.scenes:
            self.scenes[location] = None
            data = self.read(reference, base)
            if data is None:
                return None
            # The files this one names are read by a resolver one file deeper,
            # sharing this one's table
            deeper = copy.copy(self)
            deeper.depth = self.depth + 1
            self.scenes[location] = readers.read(
                data, name=location, prototypes=self.prototypes, strict=self.strict,
                extern_resolver=deeper)
        return self.scenes[location]


class LocalPrototypes(ExternPrototypes):
    """Reads the files EXTERNPROTO URLs name beside the document

    A URL is read where it is a relative path to a file under the folder of
    the document naming it, of `MAX_PROTOTYPE_BYTES` at most
    (`contained_path`). Nothing is fetched over a network.

    root -- a folder whose files any document under it may name, in place of
        each document's own folder: a tree of worlds beside the prototype
        library they share
    """

    def __init__(
        self,
        prototypes: "Mapping[str, type] | None" = None,
        strict: bool = False,
        root: "str | os.PathLike[str] | None" = None,
    ) -> None:
        super().__init__(prototypes, strict)
        self.root = root

    def locate(self, reference: str, base: str) -> "str | None":
        return contained_path(reference, base, self.root)

    def read(self, reference: str, base: str) -> "bytes | None":
        path = contained_path(reference, base, self.root)
        if path is None or not os.path.isfile(path):
            return None
        with open(path, 'rb') as stream:
            data = stream.read(MAX_PROTOTYPE_BYTES + 1)
        return data if len(data) <= MAX_PROTOTYPE_BYTES else None


def load(
    path: "str | os.PathLike[str]",
    *,
    prototypes: "Mapping[str, type] | None" = None,
    strict: bool = False,
    extern_resolver: "ExternResolver | None" = None,
) -> X3DScene:
    """The scene the document at `path` builds

    prototypes, strict -- as `SceneBuilder` takes them
    extern_resolver -- as `SceneBuilder` takes it, in place of a
        `LocalPrototypes`
    """
    name = os.fspath(path)
    with open(name, 'rb') as stream:
        data = stream.read()
    if extern_resolver is None:
        resolver = LocalPrototypes(prototypes, strict)
        resolver.scenes[os.path.realpath(name)] = None
        extern_resolver = resolver
    return readers.read(data, name=name, prototypes=prototypes, strict=strict,
                        extern_resolver=extern_resolver)


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
    declaration in it names. The keywords are `load`'s; a `LocalPrototypes`
    is used where there is a `name` to resolve against.
    """
    if extern_resolver is None and name:
        extern_resolver = LocalPrototypes(prototypes, strict)
    if isinstance(data, str):
        return readers.read(data.removeprefix('\ufeff').encode('utf-8'), name=name,
                            charset='utf-8', prototypes=prototypes, strict=strict,
                            extern_resolver=extern_resolver)
    return readers.read(data, name=name, prototypes=prototypes, strict=strict,
                        extern_resolver=extern_resolver)



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
