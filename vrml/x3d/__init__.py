"""X3D support for pyvrml97

`vrml.x3d.nodes` declares every X3D 4.1 node, generated from Web3D's X3D
Unified Object Model. VRML97 and earlier X3D versions are dialects of that
vocabulary (`vrml.x3d.dialects`). `load`/`loads` read any encoding,
`dump`/`dumps` write one, and `validate` checks a scene against the model.
"""

from vrml.x3d.files import dump, dumps, load, loads
from vrml.x3d.validate import validate
from vrml.x3d.writers import X3DWriteError

__all__ = ['X3DWriteError', 'dump', 'dumps', 'load', 'loads', 'validate']
