"""Web3D's X3D example archives: fetched, extracted and found

Each archive publishes every scene in several encodings (.x3d, .x3dv, .wrl,
.json, .x3db). `fetch` downloads archives into the corpus directory
(`directory`) and extracts the scene files and the licence into one tree
laid out as Web3D publishes the examples, each archive's in
`examples(name)`, so a scene naming a file of another archive reaches it;
`with_references` adds the archives the named ones' scenes reach into. With
`resources`, the images the scenes name and the render Web3D publishes of each
scene from each of its viewpoints (`viewpoint_renders`) are extracted too,
which is what a scene needs to be drawn and compared.

The examples are under the Web3D Consortium Open-Source License
(https://www.web3d.org/x3d/content/examples/license.html), which is
extracted beside them.
"""

import hashlib
import os
import re
import shutil
import urllib.request
import warnings
import zipfile
from collections.abc import Sequence

from vrml.x3d.files import staged

__all__ = ['ARCHIVES', 'directory', 'download', 'examples', 'extract', 'fetch', 'render_name',
           'viewpoint_renders', 'with_references']

URL = 'https://www.web3d.org/x3d/content/examples/X3dExamples%s.zip'

#: The SHA-256 of each archive when this module was written. Web3D rebuilds
#: the archives as examples change, so a difference is reported, not refused.
DIGESTS = {
    'ConformanceNist': 'adcd5acecbcfa1c94c54e1d753308ebccaa2b19fdb40eb22f2f1e0cdad7b236b',
    'Vrml2Sourcebook': '2f41d8b64a40b142bafbc88ab7600313d92623bfa84deb8f30e1bc101a8e6ae0',
}
ARCHIVES = ('ConformanceNist', 'Vrml2Sourcebook', 'Basic', 'HumanoidAnimation', 'Savage',
            'X3dForWebAuthors', 'X3dForAdvancedModeling')
#: The archives fetched where none are named.
DEFAULT_ARCHIVES = ('ConformanceNist', 'Vrml2Sourcebook')
#: The archives whose files each archive's scenes name (an Inline, an image).
REFERENCES = {
    'ConformanceNist': ('X3dForWebAuthors',),
    'Vrml2Sourcebook': ('X3dForWebAuthors',),
}
#: Where in the corpus directory the examples are, each archive in a folder of its name.
EXAMPLES = ('www.web3d.org', 'x3d', 'content', 'examples')

SCENE_SUFFIXES = ('.x3d', '.x3dv', '.wrl', '.json', '.x3db')
#: The images a scene's textures and backgrounds may name.
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
#: The directories of an archive that hold no scene and nothing one names.
SKIPPED_DIRECTORIES = ('_thumbnails', 'javadoc', 'classes')
#: What separates a scene's file name from a viewpoint's in Web3D's renders.
VIEWPOINT_MARK = '._VP_'


def directory() -> str:
    """Where the corpus is kept: `PYVRML97_X3D_CORPUS`, else the user's cache"""
    named = os.environ.get('PYVRML97_X3D_CORPUS')
    if named:
        return named
    base = os.environ.get('XDG_CACHE_HOME') or os.environ.get('LOCALAPPDATA')
    if not base:
        base = os.path.join(os.path.expanduser('~'), '.cache')
    return os.path.join(base, 'pyvrml97', 'x3d-corpus')


def examples(archive: str, where: "str | None" = None) -> str:
    """The folder of an archive's examples in the corpus at `where` (default
    `directory()`)"""
    return os.path.join(where or directory(), *EXAMPLES, archive)


def with_references(names: Sequence[str]) -> "list[str]":
    """`names`, and after them the archives their scenes name files of"""
    found = list(names)
    for name in names:
        found.extend(other for other in REFERENCES.get(name, ()) if other not in found)
    return found


def download(name: str, where: str) -> str:
    """The archive's path in `where`, downloading it if it is not there"""
    path = os.path.join(where, 'X3dExamples%s.zip' % name)
    if not os.path.exists(path):
        with urllib.request.urlopen(URL % name, timeout=600) as response, \
                staged(path) as stream:  # noqa: S310 URL is the https constant above
            shutil.copyfileobj(response, stream)
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    if name in DIGESTS and digest.hexdigest() != DIGESTS[name]:
        warnings.warn('%s has SHA-256 %s, not the %s recorded for it'
                      % (path, digest.hexdigest(), DIGESTS[name]), stacklevel=2)
    return path


def _wanted(name: str, resources: bool) -> bool:
    lowered = name.lower()
    if os.path.basename(name) == 'license.html':
        return True
    if any(part in SKIPPED_DIRECTORIES for part in name.split('/')[:-1]):
        return False
    if lowered.endswith(SCENE_SUFFIXES):
        return True
    return resources and lowered.endswith(IMAGE_SUFFIXES)


def extract(archive: str, destination: str, resources: bool = False) -> int:
    """Extract the scene files and the licence, and with `resources` the images;
    the number of .x3d scenes"""
    count = 0
    root = os.path.realpath(destination)
    with zipfile.ZipFile(archive) as opened:
        for member in opened.infolist():
            name = member.filename
            if member.is_dir() or not _wanted(name, resources):
                continue
            target = os.path.realpath(os.path.join(root, name))
            if not target.startswith(root + os.sep):
                raise ValueError('Archive member %r leaves %s' % (name, root))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with opened.open(member) as source, staged(target) as stream:
                shutil.copyfileobj(source, stream)
            count += name.lower().endswith('.x3d')
    return count


def fetch(names: Sequence[str] = DEFAULT_ARCHIVES, where: "str | None" = None,
          resources: bool = False) -> "dict[str, int]":
    """Download and extract each archive named into `where` (default
    `directory()`); its number of .x3d scenes by name"""
    where = where or directory()
    os.makedirs(where, exist_ok=True)
    counts = {}
    for name in names:
        counts[name] = extract(download(name, where), where, resources)
    return counts


def render_name(description: str) -> str:
    """The name Web3D's renders give a viewpoint of this description: each
    character other than a letter, digit, ``_`` or ``.`` as ``_``"""
    return re.sub(r'[^A-Za-z0-9_.]', '_', description)


def viewpoint_renders(scene: str) -> "dict[str, str]":
    """Web3D's render of `scene` from each of its viewpoints, by viewpoint name

    Published beside the scene as ``_viewpoints/<file>._VP_<viewpoint>.png``,
    the viewpoint named by its description (`render_name`); the name of the
    view a scene opens on with no viewpoint of its own is
    ``Default_viewpoint``. Empty where none was extracted.
    """
    folder = os.path.join(os.path.dirname(scene), '_viewpoints')
    prefix = os.path.basename(scene) + VIEWPOINT_MARK
    try:
        names = os.listdir(folder)
    except OSError:
        return {}
    return {name[len(prefix):-len('.png')]: os.path.join(folder, name)
            for name in sorted(names) if name.startswith(prefix) and name.endswith('.png')}
