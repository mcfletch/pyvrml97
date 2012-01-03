"""Transformation Matrix implementation in Cython (requires Numpy)"""
from __future__ import division
import numpy as np
cimport numpy as np

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
    return np.array([
        [   t*x*x+c,    t*x*y+s*z,  t*x*z-s*y,  0.0],
        [   t*x*y-s*z,  t*y*y+c,    t*y*z+s*x,  0.0],
        [   t*x*z+s*y,  t*y*z-s*x,  t*z*z+c,    0.0], 
        [   0.0,         0.0,         0.0,        1.0],
    ], dtype=np.float32)

# def perspectiveMatrix( ):
# def frustumMatrix( ):
# def orthoMatrix( ):
# def nodePath( ):
