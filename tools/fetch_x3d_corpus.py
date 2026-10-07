#!/usr/bin/env python3
"""Fetch Web3D's X3D example archives, the corpus the readers are tested on

    tools/fetch_x3d_corpus.py                 ConformanceNist and Vrml2Sourcebook
    tools/fetch_x3d_corpus.py Basic Savage    others by name

Each archive publishes every scene in several encodings (.x3d, .x3dv, .wrl,
.json, .x3db). The archives are downloaded into the user's cache directory
and only the scene files and the licence are extracted, into
`<cache>/pyvrml97/x3d-corpus/<name>/`. `tests/test_x3d_corpus.py` reads
them from there, or from the directory `PYVRML97_X3D_CORPUS` names, and
skips where neither has them.

The examples are under the Web3D Consortium Open-Source License
(https://www.web3d.org/x3d/content/examples/license.html), which is
extracted beside them.
"""

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile
from collections.abc import Sequence

URL = 'https://www.web3d.org/x3d/content/examples/X3dExamples%s.zip'

#: The SHA-256 of each archive when this script was written. Web3D rebuilds
#: the archives as examples change, so a difference is reported, not refused.
DIGESTS = {
    'ConformanceNist': 'adcd5acecbcfa1c94c54e1d753308ebccaa2b19fdb40eb22f2f1e0cdad7b236b',
    'Vrml2Sourcebook': '2f41d8b64a40b142bafbc88ab7600313d92623bfa84deb8f30e1bc101a8e6ae0',
}
ARCHIVES = ('ConformanceNist', 'Vrml2Sourcebook', 'Basic', 'HumanoidAnimation', 'Savage',
            'X3dForWebAuthors', 'X3dForAdvancedModeling')
SCENE_SUFFIXES = ('.x3d', '.x3dv', '.wrl', '.json', '.x3db')


def corpus_directory() -> str:
    """Where the corpus is kept"""
    named = os.environ.get('PYVRML97_X3D_CORPUS')
    if named:
        return named
    base = os.environ.get('XDG_CACHE_HOME') or os.environ.get('LOCALAPPDATA')
    if not base:
        base = os.path.join(os.path.expanduser('~'), '.cache')
    return os.path.join(base, 'pyvrml97', 'x3d-corpus')


def download(name: str, directory: str) -> str:
    """The archive's path, downloading it if it is not there"""
    path = os.path.join(directory, 'X3dExamples%s.zip' % name)
    if not os.path.exists(path):
        staging = path + '.part'
        with urllib.request.urlopen(URL % name, timeout=600) as response, \
                open(staging, 'wb') as stream:  # noqa: S310 URL is the https constant above
            shutil.copyfileobj(response, stream)
        os.replace(staging, path)
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    if name in DIGESTS and digest.hexdigest() != DIGESTS[name]:
        print('%s: SHA-256 %s differs from %s; Web3D has rebuilt it'
              % (name, digest.hexdigest(), DIGESTS[name]))
    return path


def extract(archive: str, destination: str) -> int:
    """Extract the scene files and the licence; answers how many scenes"""
    count = 0
    root = os.path.realpath(destination)
    with zipfile.ZipFile(archive) as opened:
        for member in opened.infolist():
            name = member.filename
            wanted = name.lower().endswith(SCENE_SUFFIXES) or os.path.basename(name) == 'license.html'
            if member.is_dir() or not wanted:
                continue
            target = os.path.realpath(os.path.join(root, name))
            if not target.startswith(root + os.sep):
                raise ValueError('Archive member %r leaves %s' % (name, root))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            staging = target + '.part'
            with opened.open(member) as source, open(staging, 'wb') as stream:
                shutil.copyfileobj(source, stream)
            os.replace(staging, target)
            count += name.lower().endswith('.x3d')
    return count


def main(arguments: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('archives', nargs='*', choices=ARCHIVES)
    options = parser.parse_args(arguments)
    directory = corpus_directory()
    os.makedirs(directory, exist_ok=True)
    for name in options.archives or ['ConformanceNist', 'Vrml2Sourcebook']:
        archive = download(name, directory)
        destination = os.path.join(directory, name)
        print('%s: %d scenes in %s' % (name, extract(archive, destination), destination))
    return 0


if __name__ == '__main__':
    sys.exit(main())
