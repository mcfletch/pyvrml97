"""transformmatrix forward/backward calculation without accelerate support"""
from math import pi
from vrml.arrays import array, cos, sin, tan
# used to determine whether angles are non-null
TWOPI = pi * 2.0
# used to determine the center point of a transform
VERY_SMALL = 1e-300

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
        # normalize the rotation vector!
        squared = x*x + y*y + z*z
        if squared != 1.0:
            length = squared ** .5
            x /= length 
            y /= length 
            z /= length
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
    S = array( [ [x,0,0,0], [0,y,0,0], [0,0,z,0], [0,0,0,1] ], 'f' )
    S1 = array( [ 
        [1./(x or VERY_SMALL),0,0,0], 
        [0,1./(y or VERY_SMALL),0,0], 
        [0,0,1./(z or VERY_SMALL),0], 
        [0,0,0,1] ], 'f' 
    )
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
    T = array( [ [1,0,0,0], [0,1,0,0], [0,0,1,0], [x,y,z,1] ], 'f' )
    T1 = array( [ [1,0,0,0], [0,1,0,0], [0,0,1,0], [-x,-y,-z,1] ], 'f' )
    return T, T1

def perspectiveMatrix( fovy, aspect, zNear, zFar, inverse=False ):
    """Create a perspective matrix from given parameters
    
    Note that this is the same matrix as for gluPerspective,
    save that we are using radians...
    """
    f = 1.0/tan( (fovy/2.0) ) # cotangent( fovy/2.0 )
    zDelta = zNear-zFar
    if inverse:
        return array([
            [aspect/f,0,0,0],
            [0,1/(f or VERY_SMALL),0,0],
            [0,0,0,zDelta/(2*zFar*zNear)],
            [0,0,-1,(zFar+zNear)/(2*zFar*zNear)],
        ],'f')
    else:
        return array([
            [f/aspect,0,0,0],
            [0,f,0,0],
            [0,0,(zFar+zNear)/zDelta,-1],
            [0,0,(2*zFar*zNear)/zDelta,0]
        ],'f')
def orthoMatrix( left=-1.0, right=1.0, bottom=-1.0, top=1.0, zNear=-1.0, zFar=1.0 ):
    """Calculate an orthographic projection matrix
    
    Similar to glOrtho 
    """
    tx = - ( right + left ) / float( right-left )
    ty = - ( top + bottom ) / float( top-bottom )
    tz = - ( zFar + zNear ) / float( zFar-zNear )
    return array([
        [2/(right-left),	0,	0,	 tx],
        [0,	 2/(top-bottom),	0,	 ty],
        [0,	0,	 -2/(zFar-zNear),	 tz],
        [0,	0,	0,	1],
    ], dtype='f')    
