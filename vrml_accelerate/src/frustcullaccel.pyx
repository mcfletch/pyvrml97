"""Transformation Matrix implementation in Cython (requires Numpy)"""
import numpy as np
cimport numpy as np

ctypedef np.float32_t DTYPE_T

def planeCull( np.ndarray[DTYPE_T,ndim=2] planes, np.ndarray[DTYPE_T,ndim=2] points, float minDistance = 0.0 ):
    """Find first plane in planes which entirely excludes points
    
    planes[][4] -- frustum.Frustum.planes (plane equations of the frustum)
    points[][3] or points[][4] -- point array (from bounding boxes) for culling
    minDistance -- minimum distance in behind plane that box must be to exclude
    
    returns (culled,plane) where plane is the culling plane array
    """
    cdef int foundInFront,planeCount,pointCount,planeIndex,pointIndex
    cdef float distance,plane0,plane1,plane2,plane3,point0,point1,point2
    cdef np.ndarray plane,point
    
    planeCount = planes.shape[0]
    pointCount = points.shape[0]
    if planes.shape[1] != 4:
        raise TypeError( "Need an Nx4 array of plane equation floats" )
    elif points.shape[1] not in (3,4):
        raise TypeError( "Need an Nx3 or Nx4 array of points" )
    minDistance = -minDistance
    for planeIndex in range( planeCount ):
        foundInFront = 0
        plane0,plane1,plane2,plane3 = planes[planeIndex,0],planes[planeIndex,1],planes[planeIndex,2],planes[planeIndex,3]
        for pointIndex in range(pointCount):
            point0,point1,point2 = points[pointIndex,0],points[pointIndex,1],points[pointIndex,2]
            distance = plane0 * point0 + plane1*point1 + plane2*point2 + plane3
            if distance >= minDistance:
                foundInFront = 1 
        if not foundInFront:
            # nothing was found in front, so this plane has entirely excluded the volume...
            return True, plane 
    return False,None 
