"""Readers for the X3D encodings, all building through one `SceneBuilder`

`read(data)` reads a document of any encoding: XML (`.x3d`), ClassicVRML or
VRML97 (`.x3dv`, `.wrl`), JSON (`.x3dj`, `.json`) or Fast Infoset
(`.x3db`), each possibly gzip-compressed (`.x3dz`, `.x3dvz`, `.wrz`). The
encoding is recognised from the content, or named.
"""

import os
import zlib
from collections.abc import Callable
from typing import Any

from vrml.x3d.builder import SceneBuilder
from vrml.x3d.readers import json, xml
from vrml.x3d.scene import X3DScene

#: The largest document, compressed or not, a read will hold: 2 GiB.
MAX_DOCUMENT_BYTES = 2 ** 31

GZIP_MAGIC = b'\x1f\x8b'
FAST_INFOSET_MAGIC = b'\xe0\x00\x00\x01'

#: The encoding each file suffix names.
SUFFIXES = {
    '.x3d': 'xml', '.x3dz': 'xml', '.xml': 'xml',
    '.x3dv': 'classic', '.x3dvz': 'classic', '.wrl': 'classic', '.wrz': 'classic',
    '.x3dj': 'json', '.json': 'json',
    '.x3db': 'fastinfoset',
}


class UnknownEncoding(ValueError):
    """A document whose encoding is neither recognisable nor named"""


def decompress(data: bytes) -> bytes:
    """`data` without its gzip wrapping, refusing more than MAX_DOCUMENT_BYTES"""
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    result = inflater.decompress(data, MAX_DOCUMENT_BYTES)
    if inflater.unconsumed_tail:
        raise ValueError('Compressed document expands past %d bytes' % MAX_DOCUMENT_BYTES)
    return result


def encoding_of(data: bytes, name: str = '') -> str:
    """The encoding `data` is in: from its content, else from `name`'s suffix"""
    if data.startswith(FAST_INFOSET_MAGIC):
        return 'fastinfoset'
    start = data[:256].lstrip(b'\xef\xbb\xbf \t\r\n')
    if start.startswith(b'<'):
        return 'xml'
    if start.startswith(b'{'):
        return 'json'
    if start.startswith((b'#VRML', b'#X3D')):
        return 'classic'
    suffix = os.path.splitext(name.lower())[1]
    if suffix in SUFFIXES:
        return SUFFIXES[suffix]
    raise UnknownEncoding('Cannot tell the encoding of %r' % (name or data[:32],))


#: The reader of each encoding.
READERS: "dict[str, Callable[[bytes, SceneBuilder], X3DScene]]" = {
    'xml': xml.read,
    'json': json.read,
}


def read(
    data: bytes,
    encoding: "str | None" = None,
    name: str = '',
    **options: Any,
) -> X3DScene:
    """The scene a document builds

    data -- the document's bytes, gzip-compressed or not
    encoding -- 'xml', 'classic', 'json' or 'fastinfoset'; recognised from
        the content where not given
    name -- the document's file name or URL, the base for its relative URLs
    options -- passed to `SceneBuilder`: prototypes, strict, extern_resolver
    """
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError('Document is larger than %d bytes' % MAX_DOCUMENT_BYTES)
    if data.startswith(GZIP_MAGIC):
        data = decompress(data)
    if encoding is None:
        encoding = encoding_of(data, name)
    if encoding not in READERS:
        raise UnknownEncoding('No reader for the %s encoding' % encoding)
    options.setdefault('baseURI', name)
    return READERS[encoding](data, SceneBuilder(**options))
