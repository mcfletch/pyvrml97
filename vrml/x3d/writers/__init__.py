"""Writers for the X3D encodings and VRML97

`write(scene, encoding)` returns a scene as XML ('xml'), ClassicVRML or
VRML97 ('classic') or JSON ('json') text, in the scene's own version or the
one named. A version's field names and defaults apply on the way out; a node
type, field or field type the version lacks raises `X3DWriteError`.
"""

from typing import Protocol

from vrml.x3d.scene import X3DScene
from vrml.x3d.writers import classic, json, xml
from vrml.x3d.writers.base import X3DWriteError

__all__ = ['WRITERS', 'Writer', 'X3DWriteError', 'write']


class Writer(Protocol):
    """One encoding's writer: the scene's text"""

    def __call__(self, scene: X3DScene, version: "str | None" = None,
                 canonical: bool = False) -> str: ...


#: The writer of each encoding.
WRITERS: "dict[str, Writer]" = {
    'xml': xml.write,
    'classic': classic.write,
    'json': json.write,
}


def write(
    scene: X3DScene,
    encoding: str = 'xml',
    version: "str | None" = None,
    canonical: bool = False,
) -> str:
    """Return the scene as a document in `encoding`

    version -- '2.0' for VRML97 (ClassicVRML encoding only), '3.0' to '4.1'
        for X3D; the scene's own version if not given
    canonical -- write the encoding's canonical form; the XML encoding adds
        the DTD and schema attributes of X3D canonical form
    """
    if encoding not in WRITERS:
        raise ValueError('No writer for the %r encoding; known: %s'
                         % (encoding, ', '.join(sorted(WRITERS))))
    return WRITERS[encoding](scene, version=version, canonical=canonical)
