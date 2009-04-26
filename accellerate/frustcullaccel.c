#include "Python.h"
#ifdef USE_NUMPY
#include "numpy/arrayobject.h"
#else
#include "Numeric/arrayobject.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

static PyObject * planeCull( PyObject * self, PyObject * args ) {
	/* Cull set of points with a set of plane-equations
	*/

	PyObject * frustObject = NULL;
	PyObject * pointObject = NULL;

	PyArrayObject * frustArray = NULL;
	PyArrayObject * pointArray = NULL;

	double * frustum = NULL;
	double * points = NULL;

	double minDistance = 0.0;
	
	int pi, fi, foundInFront;

	if (!PyArg_ParseTuple( args, "OO:d", &frustObject, &pointObject, &minDistance )) {
		return NULL;
	}
	frustArray = (PyArrayObject *) PyArray_ContiguousFromObject(frustObject, PyArray_DOUBLE, 2, 2);
	pointArray = (PyArrayObject *) PyArray_ContiguousFromObject(pointObject, PyArray_DOUBLE, 2, 2);
	if ((!frustArray) | (!pointArray)) {
		return NULL;
	}
	/* okay, have the two 2-dim matrices */
	if (frustArray->dimensions[1] != 4) {
		PyErr_Format(
			PyExc_TypeError,
			"Frustum must be an x*4 array, second dimension was %ld",
			(long)(frustArray->dimensions[1])
		);
	}
	if ((pointArray->dimensions[1] > 4) | (pointArray->dimensions[1] < 3)) {
		PyErr_Format(
			PyExc_TypeError,
			"Points must be an x*3 or x*4 array, second dimension was %ld",
			(long)(pointArray->dimensions[1])
		);
	}
	minDistance = -minDistance;
	frustum = (double *) frustArray->data;
	points = (double *) pointArray->data;
	for (fi=0;fi<frustArray->dimensions[0]*frustArray->dimensions[1];fi+=frustArray->dimensions[1]) {
		/* for plane in planes */
		foundInFront = 0;
		for (pi=0;pi<pointArray->dimensions[0]*pointArray->dimensions[1];pi+=pointArray->dimensions[1]) {
			/* for point in points */
			if (
				frustum[fi+0]*points[pi+0]+
				frustum[fi+1]*points[pi+1]+
				frustum[fi+2]*points[pi+2]+
				frustum[fi+3] >= minDistance
			) {
				foundInFront = 1;
				break;
			}
		}
		if (!foundInFront) {
			return Py_BuildValue( "(ii)", 1, fi/frustArray->dimensions[1] );
		}
	}
	return Py_BuildValue( "(iO)", 0, Py_None );
}

static PyMethodDef frustcullaccel_methods[] = {
	{"planeCull", planeCull, 1, "planeCull( planes[][4], points[][4] )\n"\
								"Do frustum-culling for plane and points\n"\
								"planes -- Frustum plane equations\n"\
								"points -- bounding-box points\n\n"\
								"returns (1, cullingPlaneIndex) if culled\n"\
								"\t(0,None) if not culled"},
								
	{NULL, NULL}
};

#ifdef USE_NUMPY
void
initfrustcullaccelnumpy(void)
{
	Py_InitModule("frustcullaccelnumpy", frustcullaccel_methods);
	import_array();
}
#else
void
initfrustcullaccelnumeric(void)
{
	Py_InitModule("frustcullaccelnumeric", frustcullaccel_methods);
	import_array();
}
#endif

#ifdef __cplusplus
}
#endif
