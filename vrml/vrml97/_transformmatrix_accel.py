"""transformmatrix forward/backward calculation with accelerate support"""
from vrml_accelerate import tmatrixaccel
from math import pi
# used to determine whether angles are non-null
TWOPI = pi * 2.0
VERY_SMALL = 1e-300

def rotMatrix( source = None ):
    """Convert a VRML rotation to rotation matrices

    Returns (R, R') (R and the inverse of R), with both
    being 4x4 transformation matrices.
        or
    None,None if the angle is an exact multiple of 2pi

    x,y,z -- (normalised) rotational vector
    a -- angle in radians
    """
    if source is None:
        return None,None
    else:
        (x,y,z, a) = source
    if a % TWOPI:
        return tmatrixaccel.rotMatrix( x,y,z,a ),tmatrixaccel.rotMatrix( x,y,z,-a )
    return None,None
def scaleMatrix( source=None ):
    """Convert a VRML scale to scale matrices

    Returns (S, S') (S and the inverse of S), with both
    being 4x4 transformation matrices.
        or
    None,None if x == y == z == 1.0

    x,y,z -- scale vector
    """
    if source is None:
        return None,None
    else:
        (x,y,z) = source[:3]
    if x == y == z == 1.0:
        return None, None
    forward = tmatrixaccel.scaleMatrix( x,y,z )
    backward = tmatrixaccel.scaleMatrix( 1.0/(x or VERY_SMALL),1.0/(y or VERY_SMALL), 1.0/(z or VERY_SMALL) )
    return forward, backward
def transMatrix( source=None ):
    """Convert a VRML translation to translation matrices

    Returns (T, T') (T and the inverse of T), with both
    being 4x4 transformation matrices.
        or
    None,None if x == y == z == 0.0

    x,y,z -- scale vector
    """
    if source is None:
        return None,None
    else:
        (x,y,z) = source[:3]
    if x == y == z == 0.0:
        return None, None 
    return tmatrixaccel.transMatrix( x,y,z ),tmatrixaccel.transMatrix( -x, -y, -z )
perspectiveMatrix = tmatrixaccel.perspectiveMatrix
orthoMatrix = tmatrixaccel.orthoMatrix
