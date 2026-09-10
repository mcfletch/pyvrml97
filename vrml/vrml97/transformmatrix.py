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
    return ar.dot( p, matrix)

That is, you use the homogenous coordinate, and
make it the first item in the dot'ing.
"""
from typing import Any
# `from math import *` stood here too and supplied nothing: every free name in
# this module -- array, dot, identity, pi -- comes from the array
# implementation. Having both meant a checker saw numpy's `cos` land on
# `math.cos` and so on, for names nothing here even uses.
from vrml import arrays as ar
try:
    from vrml.vrml97._transformmatrix_accel import (
        rotMatrix,
        scaleMatrix,
        transMatrix,
        perspectiveMatrix,
        orthoMatrix,
    )
except ImportError:
    from vrml.vrml97._transformmatrix import (
        rotMatrix,
        scaleMatrix,
        transMatrix,
        perspectiveMatrix,
        orthoMatrix,
    )

assert perspectiveMatrix
assert orthoMatrix

# used to determine whether angles are non-null
TWOPI = ar.pi * 2.0
RADTODEG = 360./TWOPI
DEGTORAD = TWOPI/360.
# used to determine the center point of a transform
ORIGINPOINT = ar.array([0,0,0,1],'f')
VERY_SMALL = 1e-300

def transformMatrix(
        translation: Any = (0,0,0),
        center: Any = (0,0,0),
        rotation: Any = (0,1,0,0),
        scale: Any = (1,1,1),
        scaleOrientation: Any = (0,1,0,0),
        parentMatrix: Any = None,
    ) -> Any:
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
    return compressMatrices( parentMatrix, T,C,R,SO,S,SO1,C1 )

def itransformMatrix(
        translation: Any = (0,0,0),
        center: Any = (0,0,0),
        rotation: Any = (0,1,0,0),
        scale: Any = (1,1,1),
        scaleOrientation: Any = (0,1,0,0),
        parentMatrix: Any = None,
    ) -> Any:
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
    return compressMatrices( parentMatrix, C,SO, S1, SO1, R1, C1, T1)

def transformMatrices(
        translation: Any = (0,0,0),
        center: Any = (0,0,0),
        rotation: Any = (0,1,0,0),
        scale: Any = (1,1,1),
        scaleOrientation: Any = (0,1,0,0),
        parentMatrix: Any = None,
    ) -> Any:
    """Calculate both forward and backward matrices for these parameters"""
    T,T1 = transMatrix( translation )
    C,C1 = transMatrix( center )
    R,R1 = rotMatrix( rotation )
    SO,SO1 = rotMatrix( scaleOrientation )
    S,S1 = scaleMatrix( scale )
    return (
        compressMatrices( parentMatrix, T,C,R,SO,S,SO1,C1 ),
        compressMatrices( parentMatrix, C,SO, S1, SO1, R1, C1, T1)
    )

def localMatrices(
        translation: Any = (0,0,0),
        center: Any = (0,0,0),
        rotation: Any = (0,1,0,0),
        scale: Any = (1,1,1),
        scaleOrientation: Any = (0,1,0,0),
        parentMatrix: Any = None,
    ) -> Any:
    """Calculate (forward,inverse) matrices for this transform element"""
    T,T1 = transMatrix( translation )
    C,C1 = transMatrix( center )
    R,R1 = rotMatrix( rotation )
    SO,SO1 = rotMatrix( scaleOrientation )
    S,S1 = scaleMatrix( scale )
    return (
        compressMatrices( T,C,R,SO,S,SO1,C1 ),
        compressMatrices( C,SO, S1, SO1, R1, C1, T1)
    )

def compressMatrices( *matrices: Any ) -> Any:
    """Compress a set of matrices

    Any (or all) of the matrices may be None,
    if *all* are None, then the result will be None,
    otherwise will be the dot product of all of the
    matrices...
    """
    if not matrices:
        return None
    else:
        first = matrices[0]
        matrices = matrices[1:]
    for item in matrices:
        if item is not None:
            if first is None:
                first = item
            else:
                first = ar.dot( item, first )
    return first


def center(
    translation: Any = (0,0,0),
    center: Any = (0,0,0),
    parentMatrix: Any = None,
) -> Any:
    """Determine the center of rotation for a transform node

    Returns the parent-space coordinate of the
    node's center of rotation.
    """
    if parentMatrix is None:
        parentMatrix = ar.identity(4)
    T,T1 = transMatrix( translation )
    C,C1 = transMatrix( center )
    for x in (T,C):
        if x:
            parentMatrix = ar.dot( x, parentMatrix)
    return ar.dot( ORIGINPOINT, parentMatrix )
