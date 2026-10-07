"""X3D for pyvrml97: the X3D 4.1 vocabulary, its encodings and its run time

`vrml.x3d.nodes` declares every X3D node, generated from Web3D's X3D Unified
Object Model. VRML97 and earlier X3D versions are dialects of that one
vocabulary (`vrml.x3d.dialects`).
"""

from vrml.x3d.files import load, loads

__all__ = ['load', 'loads']
