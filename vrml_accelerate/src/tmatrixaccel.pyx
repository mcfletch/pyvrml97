"""Transformation Matrix implementation in Cython (requires Numpy)"""
from __future__ import division
import numpy as np
cimport numpy as np

cdef float VERY_SMALL = 1e-300

def transMatrix( float x=0.0, float y=0.0, float z=0.0 ):
    """Produce a translation matrix moving (x,y,z)"""
    return np.array([
        [1.0,0.0,0.0,0.0],
        [0.0,1.0,0.0,0.0],
        [0.0,0.0,1.0,0.0], 
        [x,y,z,1.0],
    ], dtype=np.float32 )

def scaleMatrix( float x=1.0, float y=1.0, float z=1.0 ):
    """Produce a scaling matrix scaling factor (x,y,z)"""
    return np.array([
        [x,0.0,0.0,0.0],
        [0.0,y,0.0,0.0],
        [0.0,0.0,z,0.0], 
        [0.0,0.0,0.0,1.0],
    ], dtype=np.float32 )

def rotMatrix( float x=0.0, float y=1.0, float z=0.0, float a=0.0 ):
    """Produce a rotation matrix around vector x,y,z of angle a (radians)"""
    cdef float c,s,t
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
    
    return np.array([
        [   (x2*t)+c,    y*x*t+z*s,  x*z*t-y*s,  0.0],
        [   x*y*t-z*s,  y2*t +c,    y*z*t+x*s,  0.0],
        [   x*z*t+y*s,  y*z*t-x*s,  z2*t+c,    0.0], 
        [   0.0,         0.0,         0.0,        1.0],
    ], dtype=np.float32)

def perspectiveMatrix( float fovy=np.pi/2.0, float aspect=1.0, float zNear=0.1, float zFar=10000.0 ):
    """Create a perspective (frustum) matrix from given parameters
    
    Note that this is the same matrix as for gluPerspective,
    save that we are using radians...
    """
    cdef float f,zDelta
    f = 1.0/np.tan( (fovy/2.0) ) # cotangent( fovy/2.0 )
    zDelta = zNear-zFar
    return np.array([
        [f/aspect,0,0,0],
        [0,f,0,0],
        [0,0,(zFar+zNear)/zDelta,-1],
        [0,0,(2*zFar*zNear)/zDelta,0]
    ],dtype=np.float32)
def orthoMatrix( float left=-1.0, float right=1.0, float bottom=-1.0, float top=1.0, float zNear=-1.0, float zFar=1.0 ):
    tx = - ( right + left ) / ( (right-left) or VERY_SMALL )
    ty = - ( top + bottom ) / ( (top-bottom) or VERY_SMALL )
    tz = - ( zFar + zNear ) / ( (zFar-zNear) or VERY_SMALL )
    return np.array([
        [2/(right-left),	0,	0,	 tx],
        [0,	 2/(top-bottom),	0,	 ty],
        [0,	0,	 -2/(zFar-zNear),	 tz],
        [0,	0,	0,	1],
    ], dtype=np.float32)
