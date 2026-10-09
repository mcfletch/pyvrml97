"""Transformation Matrix implementation in Cython (requires Numpy)"""
from __future__ import division
import numpy as np
cimport numpy as np

cdef double VERY_SMALL = 1e-6
cdef double TWOPI = np.pi * 2.0

# Transforms are double precision, so a geocentric offset keeps its millimetres
# until the camera's is taken from it; projections are single precision.

def transMatrix( double x=0.0, double y=0.0, double z=0.0 ):
    """Produce a translation matrix moving (x,y,z)"""
    return np.array([
        [1.0,0.0,0.0,0.0],
        [0.0,1.0,0.0,0.0],
        [0.0,0.0,1.0,0.0], 
        [x,y,z,1.0],
    ], dtype=np.float64 )

def scaleMatrix( double x=1.0, double y=1.0, double z=1.0 ):
    """Produce a scaling matrix scaling factor (x,y,z)"""
    return np.array([
        [x,0.0,0.0,0.0],
        [0.0,y,0.0,0.0],
        [0.0,0.0,z,0.0], 
        [0.0,0.0,0.0,1.0],
    ], dtype=np.float64 )

def rotMatrix( double x=0.0, double y=1.0, double z=0.0, double a=0.0 ):
    """Produce a rotation matrix around vector x,y,z of angle a (radians)"""
    cdef double c,s,t
    c = np.cos( a )
    s = np.sin( a )
    t = 1-c
    if x == y == z == 0.0:
        y = 1.0
    # x,y,z must be a *normalized* vector for the rotation matrix...
    x2 = x*x
    y2 = y*y
    z2 = z*z
    h2 = x2+y2+z2
    if h2 != 1.0:
        h = h2 ** .5 
        x = x/h 
        y = y/h
        z = z/h
        x2 = x*x 
        y2 = y*y 
        z2 = z*z
    if a % TWOPI:
        return np.array([
            [   (x2*t)+c,    y*x*t+z*s,  x*z*t-y*s,  0.0],
            [   x*y*t-z*s,  y2*t +c,    y*z*t+x*s,  0.0],
            [   x*z*t+y*s,  y*z*t-x*s,  z2*t+c,    0.0], 
            [   0.0,         0.0,         0.0,        1.0],
        ], dtype=np.float64)
    else:
        return None

def perspectiveMatrix( float fovy=np.pi/2.0, float aspect=1.0, float zNear=0.1, float zFar=10000.0, inverse=False ):
    """Create a perspective (frustum) matrix from given parameters
    
    Note that this is the same matrix as for gluPerspective,
    save that we are using radians...
    """
    cdef float f,zDelta
    f = 1.0/np.tan( (fovy/2.0) ) # cotangent( fovy/2.0 )
    zDelta = zNear-zFar
    if inverse:
        return np.array([
            [aspect/f,0,0,0],
            [0,1/(f or VERY_SMALL),0,0],
            [0,0,0,zDelta/(2*zFar*zNear)],
            [0,0,-1,(zFar+zNear)/(2*zFar*zNear)],
        ],dtype=np.float32)
    else:
        return np.array([
            [f/aspect,0,0,0],
            [0,f,0,0],
            [0,0,(zFar+zNear)/zDelta,-1],
            [0,0,(2*zFar*zNear)/zDelta,0]
        ],dtype=np.float32)
    
def orthoMatrix( float left=-1.0, float right=1.0, float bottom=-1.0, float top=1.0, float zNear=-1.0, float zFar=1.0 ):
    """Calculate an orthographic projection matrix

    The same matrix as glOrtho, transposed: the offset is in the last row, as
    it is in every other matrix here, so that a point goes through it as
    ``dot( point, matrix )`` like the rest of the module's.
    """
    rl = (right-left) or VERY_SMALL
    tb = (top-bottom) or VERY_SMALL
    fn = (zFar-zNear) or VERY_SMALL
    return np.array([
        [2/rl,	0,	0,	0],
        [0,	 2/tb,	0,	0],
        [0,	0,	 -2/fn,	0],
        [- ( right + left ) / rl,	- ( top + bottom ) / tb,	- ( zFar + zNear ) / fn,	1],
    ], dtype=np.float32)
