"""Utility module for creating transformation matrices

Basically this gives you the ability to construct
transformation matrices without needing OpenGL
or similar run-time engines.  The result is that
design-time utilities can process files without
trading dependencies on a particular run-time.

This code is originally from the mcf.vrml processing
engine, and has only been cosmetically altered to
fit the new organizational pattern.

Note: to apply these matrices to a particular coordinate,
you would do the following:

    p = ones( 4 )
    p[:3] = coordinate
    return dot( p, matrix)

That is, you use the homogenous coordinate, and
make it the first item in the dot'ing.
"""
from math import *
from vrml.arrays import *

# used to determine whether angles are non-null
TWOPI = pi * 2.0
RADTODEG = 360./TWOPI
DEGTORAD = TWOPI/360.
# used to determine the center point of a transform
ORIGINPOINT = array([0,0,0,1],'d')

def transformMatrix(
        translation = (0,0,0),
        center = (0,0,0),
        rotation = (0,1,0,0),
        scale = (1,1,1),
        scaleOrientation = (0,1,0,0),
        parentMatrix = None,
    ):
    """Convert VRML transform values to an overall matrix

    Returns 4x4 transformation matrix
    Note that this uses VRML standard for rotations
    (angle last, and in radians).

    This should return matrices which, when applied to
    local-space coordinates, give you parent-space
    coordinates.

    parentMatrix if provided, should be the parent's
    transformation matrix, a 4x4 matrix of such as
    returned by this function.
    """
    T,T1 = transMatrix( translation )
    C,C1 = transMatrix( center )
    R,R1 = rotMatrix( rotation )
    SO,SO1 = rotMatrix( scaleOrientation )
    S,S1 = scaleMatrix( scale )
    if parentMatrix is None:
        parentMatrix = identity(4)
    for x in ( T,C,R,SO,S,SO1,C1 ):
        if x is not None:
            parentMatrix = dot( x, parentMatrix )
    return parentMatrix
    
def itransformMatrix(
        translation = (0,0,0),
        center = (0,0,0),
        rotation = (0,1,0,0),
        scale = (1,1,1),
        scaleOrientation = (0,1,0,0),
        parentMatrix = None,
    ):
    """Convert VRML transform values to an inverse transform matrix

    Returns 4x4 transformation matrix
    Note that this uses VRML standard for rotations
    (angle last, and in radians).

    This should return matrices which, when applied to
    parent-space coordinates, give you local-space
    coordinates for the corresponding transform.

    Note: this is a substantially un-tested algorithm
    though it seems to be properly constructed as far
    as I can see.  Whether to use dot(x, parentMatrix)
    or the reverse is not immediately clear to me.
    
    parentMatrix if provided, should be the child's
    transformation matrix, a 4x4 matrix of such as
    returned by this function.
    """
    T,T1 = transMatrix( translation )
    C,C1 = transMatrix( center )
    R,R1 = rotMatrix( rotation )
    SO,SO1 = rotMatrix( scaleOrientation )
    S,S1 = scaleMatrix( scale )
    if parentMatrix is None:
        parentMatrix = identity(4)
    for x in ( C,SO, S1, SO1, R1, C1, T1):
        if x is not None:
            parentMatrix = dot( x, parentMatrix )
    return parentMatrix


def center(
    translation = (0,0,0),
    center = (0,0,0),
    parentMatrix = None,
):
    """Determine the center of rotation for a transform node

    Returns the parent-space coordinate of the
    node's center of rotation.
    """
    if parentMatrix is None:
        parentMatrix = identity(4)
    T,T1 = transMatrix( translation )
    C,C1 = transMatrix( center )
    for x in (T,C):
        if x:
            parentMatrix = dot( x, parentMatrix)
    return dot( ORIGINPOINT, parentMatrix )

if tmatrixaccel:
    rotMatrix = tmatrixaccel.rotMatrix
    scaleMatrix = tmatrixaccel.scaleMatrix
    transMatrix = tmatrixaccel.transMatrix
else:
    def rotMatrix( source=None ):
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
            c = cos( a )
            c1 = cos( -a )
            s = sin( a )
            s1 = sin( -a )
            t = 1-c
            R = array( [
                [ t*x*x+c, t*x*y+s*z, t*x*z-s*y, 0],
                [ t*x*y-s*z, t*y*y+c, t*y*z+s*x, 0],
                [ t*x*z+s*y, t*y*z-s*x, t*z*z+c, 0],
                [ 0,        0,        0,         1]
            ] )
            R1 = array( [
                [ t*x*x+c1, t*x*y+s1*z, t*x*z-s1*y, 0],
                [ t*x*y-s1*z, t*y*y+c1, t*y*z+s1*x, 0],
                [ t*x*z+s1*y, t*y*z-s1*x, t*z*z+c1, 0],
                [ 0,         0,         0,          1]
            ] )
            return R, R1
        else:
            return None, None

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
        S = array( [ [x,0,0,0], [0,y,0,0], [0,0,z,0], [0,0,0,1] ], 'd' )
        try:
            S1 = array( [ [1./x,0,0,0], [0,1./y,0,0], [0,0,1./z,0], [0,0,0,1] ], 'd' )
        except ZeroDivisionError:
            if x == 0:
                x = 1e-300 # arbitrary, small value...
            if y == 0:
                y = 1e-300 # arbitrary, small value...
            if z == 0:
                z = 1e-300 # arbitrary, small value...
            S1 = array( [ [1./x,0,0,0], [0,1./y,0,0], [0,0,1./z,0], [0,0,0,1] ], 'd' )
        return S, S1

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
        T = array( [ [1,0,0,0], [0,1,0,0], [0,0,1,0], [x,y,z,1] ], 'd' )
        T1 = array( [ [1,0,0,0], [0,1,0,0], [0,0,1,0], [-x,-y,-z,1] ], 'd' )
        return T, T1

def perspectiveMatrix( fovy, aspect, zNear, zFar ):
    """Create a perspective matrix from given parameters
    
    Note that this is the same matrix as for gluPerspective,
    save that we are using radians...
    """
    f = 1.0/tan( (fovy/2.0) ) # cotangent( fovy/2.0 )
    zDelta = zNear-zFar
    return array([
        [f/aspect,0,0,0],
        [0,f,0,0],
        [0,0,(zFar+zNear)/zDelta,-1],
        [0,0,(2*zFar*zNear)/zDelta,0]
    ],'d')