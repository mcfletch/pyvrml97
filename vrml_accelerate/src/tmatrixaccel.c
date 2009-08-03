#include "Python.h"

#if PY_VERSION_HEX < 0x02050000
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

#ifdef USE_NUMPY
#include "numpy/arrayobject.h"
#define NEW_ARRAY_FUNC PyArray_SimpleNew
#else
#include "Numeric/arrayobject.h"
#define NEW_ARRAY_FUNC PyArray_FromDims
#endif

#ifdef __cplusplus
extern "C" {
#endif

#ifndef M_PI
#define       M_PI   3.1415926535898
#endif
#define PI M_PI

PyObject * new_transMatrix( double x, double y, double z ) {
	/* Create new matrix with given values

		returns a new reference or NULL on failure
	*/
	PyObject * result = NULL;
	PyArrayObject * resultArray = NULL;
	Py_ssize_t dims[2] = {4,4};
	double resultTemp[4][4] = {{1.0,0.0,0.0,0.0}, {0.0,1.0,0.0,0.0}, {0.0,0.0,1.0,0.0}, {x,y,z,1.0}};
	result = NEW_ARRAY_FUNC( 2, dims, PyArray_DOUBLE);
	if (!result) {
		PyErr_Format(
			PyExc_MemoryError,
			"Could not create new matrix object"
		);
		return NULL;
	}
	resultArray = (PyArrayObject *) result;
	memcpy( resultArray->data, & resultTemp, sizeof(double)*4*4);
	return result;
}
PyObject * new_scaleMatrix( double x, double y, double z ) {
	/* Create new matrix with given values

		returns a new reference or NULL on failure
	*/
	PyObject * result = NULL;
	PyArrayObject * resultArray = NULL;
	Py_ssize_t dims[2] = {4,4};
	double resultTemp[4][4] = {{x,0.0,0.0,0.0}, {0.0,y,0.0,0.0}, {0.0,0.0,z,0.0}, {0.0,0.0,0.0,1.0}};
	resultTemp[0][0] = x;
	resultTemp[1][1] = y;
	resultTemp[2][2] = z;
	result = NEW_ARRAY_FUNC( 2, dims, PyArray_DOUBLE);
	if (!result) {
		PyErr_Format(
			PyExc_MemoryError,
			"Could not create new matrix object"
		);
		return NULL;
	}
	resultArray = (PyArrayObject *) result;
	memcpy( resultArray->data, & resultTemp, sizeof(double)*4*4);
	return result;
}
PyObject * new_rotMatrix( double x, double y, double z, double a ) {
	/* Create new matrix with given values

		returns a new reference or NULL on failure
	*/

	PyObject * result = NULL;
	PyArrayObject * resultArray = NULL;
	Py_ssize_t dims[2] = {4,4};
	double resultTemp[4][4] = {{1.0,0.0,0.0,0.0}, {0.0,1.0,0.0,0.0}, {0.0,0.0,1.0,0.0}, {0.0,0.0,0.0,1.0}};
	double c,s,t;
	c = cos( a );
	s = sin( a );
	t = 1-c;

	resultTemp[0][0] = t*x*x+c; resultTemp[0][1] = t*x*y+s*z; resultTemp[0][2] = t*x*z-s*y;
	resultTemp[1][0] = t*x*y-s*z; resultTemp[1][1] = t*y*y+c; resultTemp[1][2] = t*y*z+s*x;
	resultTemp[2][0] = t*x*z+s*y; resultTemp[2][1] = t*y*z-s*x; resultTemp[2][2] = t*z*z+c;
	result = NEW_ARRAY_FUNC( 2, dims, PyArray_DOUBLE);
	if (!result) {
		PyErr_Format(
			PyExc_MemoryError,
			"Could not create new matrix object"
		);
		return NULL;
	}
	resultArray = (PyArrayObject *) result;
	memcpy( resultArray->data, & resultTemp, sizeof(double)*4*4);
	return result;
}

static PyObject * transMatrix( PyObject * self, PyObject * args ) {
	/* Return forward and backward translation matrices for an x,y,z tuple/list/array
	
	([ [1,0,0,0], [0,1,0,0], [0,0,1,0], [x,y,z,1] ],[ [1,0,0,0], [0,1,0,0], [0,0,1,0], [-x,-y,-z,1] ])
	*/
	PyObject * source = NULL;
	PyArrayObject * sourceArray = NULL;

	double * sourceData = NULL;
	double x = 0.0;
	double y = 0.0;
	double z = 0.0;

	if (!PyArg_ParseTuple( args, "O", &source )) {
		return NULL;
	}
	if (source == Py_None) {
		return Py_BuildValue( "(OO)", Py_None, Py_None );
	}
	if (source != NULL) {
		sourceArray = (PyArrayObject *) PyArray_ContiguousFromObject(source, PyArray_DOUBLE, 0, 1);
		if (!sourceArray) {
			return NULL;
		}
		if (sourceArray->nd != 0) {
			sourceData = (double *) sourceArray->data;
			if (sourceArray->dimensions[0] > 0) {
				x = sourceData[0];
			}
			if (sourceArray->dimensions[0] > 1) {
				y = sourceData[1];
			}
			if (sourceArray->dimensions[0] > 2) {
				z = sourceData[2];
			}
		}
	}
	if ((x==0.0) & (y==0.0) & (z==0.0)) {
		return Py_BuildValue( "(OO)", Py_None, Py_None );
	} else {
		PyObject * backward = NULL;
		PyObject * forward = NULL;

		forward = new_transMatrix( x,y,z );
		if (forward != NULL) {
			backward = new_transMatrix( -x,-y,-z );
			if (backward != NULL) {
				return Py_BuildValue( "(OO)", forward, backward );
			}
		}
	}
	return NULL;
}

static PyObject * scaleMatrix( PyObject * self, PyObject * args ) {
	/* Return forward and backward scale matrices for an x,y,z tuple/list/array
	
	([ [x,0,0,0], [0,y,0,0], [0,0,z,0], [0,0,0,1] ],[ [1/x,0,0,0], [0,1/y,0,0], [0,0,1/z,0], [0,0,0,1] ])
	*/
	PyObject * source = NULL;
	PyArrayObject * sourceArray = NULL;

	double * sourceData = NULL;
	double x = 1.0;
	double y = 1.0;
	double z = 1.0;

	if (!PyArg_ParseTuple( args, "O", &source )) {
		return NULL;
	}
	if (source == Py_None) {
		return Py_BuildValue( "(OO)", Py_None, Py_None );
	}
	if (source != NULL) {
		sourceArray = (PyArrayObject *) PyArray_ContiguousFromObject(source, PyArray_DOUBLE, 0, 1);
		if (!sourceArray) {
			return NULL;
		}
		if (sourceArray->nd != 0) {
			sourceData = (double *) sourceArray->data;
			if (sourceArray->dimensions[0] > 0) {
				x = sourceData[0];
			}
			if (sourceArray->dimensions[0] > 1) {
				y = sourceData[1];
			}
			if (sourceArray->dimensions[0] > 2) {
				z = sourceData[2];
			}
		}
	}
	if ((x==1.0) & (y==1.0) & (z==1.0)) {
		return Py_BuildValue( "(OO)", Py_None, Py_None );
	} else {
		PyObject * backward = NULL;
		PyObject * forward = NULL;

		forward = new_scaleMatrix( x,y,z );
		if (forward != NULL) {
			if (x==0.0) {
				x = 1e-300;
			}
			if (y==0.0) {
				y = 1e-300;
			}
			if (z==0.0) {
				z = 1e-300;
			}
			backward = new_scaleMatrix( 1.0/x,1.0/y,1.0/z );
			if (backward != NULL) {
				return Py_BuildValue( "(OO)", forward, backward );
			}
		}
	}
	return NULL;
}

static PyObject * rotMatrix( PyObject * self, PyObject * args ) {
	/* Return forward and backward scale matrices for an x,y,z tuple/list/array
	
	[
			[ t*x*x+c, t*x*y+s*z, t*x*z-s*y, 0],
			[ t*x*y-s*z, t*y*y+c, t*y*z+s*x, 0],
			[ t*x*z+s*y, t*y*z-s*x, t*z*z+c, 0],
			[ 0,        0,        0,         1]
	], inverse
	*/
	PyObject * source = NULL;
	PyArrayObject * sourceArray = NULL;

	double * sourceData = NULL;
	double x = 0.0;
	double y = 1.0;
	double z = 0.0;
	double a = 0.0;

	if (!PyArg_ParseTuple( args, "O", &source )) {
		return NULL;
	}
	if (source == Py_None) {
		/* printf( "rotMatrix got source None" ); */
		return Py_BuildValue( "(OO)", Py_None, Py_None );
	}
	if (source != NULL) {
		sourceArray = (PyArrayObject *) PyArray_ContiguousFromObject(source, PyArray_DOUBLE, 0, 1);
		if (!sourceArray) {
			return NULL;
		}
		if (sourceArray->nd != 0) {
			sourceData = (double *) sourceArray->data;
			if (sourceArray->dimensions[0] > 0) {
				x = sourceData[0];
			}
			if (sourceArray->dimensions[0] > 1) {
				y = sourceData[1];
			}
			if (sourceArray->dimensions[0] > 2) {
				z = sourceData[2];
			}
			if (sourceArray->dimensions[0] > 3) {
				a = sourceData[3];
			} /*else {
				printf( "rotMatrix source didn't include angle" );
			}*/

		}
	}
	if (fabs(fmod(a, PI*2)) < 1e-300) {
		/*printf( "rotMatrix angle is 360 degrees: %e\n", fabs(fmod(a, PI*2)) );*/
		return Py_BuildValue( "(OO)", Py_None, Py_None );
	} else {
		PyObject * backward = NULL;
		PyObject * forward = NULL;

		/* normalise rotation vector */
		double total;
		total = sqrt(x*x+y*y+z*z);
		if (total != 0.0) {
			x /= total;
			y /= total;
			z /= total;
		} else {
			PyErr_Format(
				PyExc_ValueError,
				"Rotation around 0-length vector impossible"
			);
			return NULL;
		}


		forward = new_rotMatrix( x,y,z,a );
		if (forward != NULL) {
			backward = new_rotMatrix( x,y,z,-a );
			if (backward != NULL) {
				return Py_BuildValue( "(OO)", forward, backward );
			}
		}
	}
	return NULL;
}

static PyMethodDef tmatrixaccel_methods[] = {
	{"transMatrix", transMatrix, 1, "transMatrix( [x,y,z] )\n"\
								"C accellerator for vrml.vrml97.transformmatrix.transMatrix\n"\
								"x,y,z -- Python object compatible with Numeric double array\n\n"\
								"returns a 4x4 translation matrix for the given translation and\n"\
								"the inverse of the translation."},
	{"scaleMatrix", scaleMatrix, 1, "scaleMatrix( [x,y,z] )\n"\
								"C accellerator for vrml.vrml97.transformmatrix.scaleMatrix\n"\
								"x,y,z -- Python object compatible with Numeric double array\n\n"\
								"returns a 4x4 translation matrix for the given scale and\n"\
								"the inverse of the scale."},
	{"rotMatrix", rotMatrix, 1, "rotMatrix( [x,y,z,a] )\n"\
								"C accellerator for vrml.vrml97.transformmatrix.rotMatrix\n"\
								"x,y,z,a -- Python object compatible with Numeric double array\n"\
								"\ta is expressed in radians, as normal for Python and VRML97\n\n"\
								"returns a 4x4 rotation matrix for the given scale and\n"\
								"the inverse of the rotation."},
								
	{NULL, NULL}
};

#ifdef USE_NUMPY
void
inittmatrixaccelnumpy(void)
{
	Py_InitModule("tmatrixaccelnumpy", tmatrixaccel_methods);
	import_array();
}
#else
void
inittmatrixaccelnumeric(void)
{
	Py_InitModule("tmatrixaccelnumeric", tmatrixaccel_methods);
	import_array();
}
#endif

#ifdef __cplusplus
}
#endif
