#include "Python.h"

#ifdef __cplusplus
extern "C" {
#endif

static PyObject * PyObject_GetDictKey( PyObject * obj, char * name ) {
	/* low-level retrieval of attr name from self.__dict__ 
	
	Returns a new reference to the object, or NULL
	with the proper AttributeError set.
	*/
	PyObject ** dictptr;
	PyObject * res;
	dictptr = _PyObject_GetDictPtr(obj);
	if (dictptr != NULL) {
		PyObject * dict = *dictptr;
		if (dict != NULL) {
			res = PyDict_GetItemString(dict, name);
			if (res != NULL) {
				Py_INCREF(res);
			} else {
				PyErr_Format(
					PyExc_AttributeError,
					"'%.50s' object has no attribute '%.50s'",
					obj->ob_type->tp_name, name
				);
			}
		} else {
			res = NULL;
			PyErr_Format(
				PyExc_AttributeError,
                "'%.50s' object '__dict__' attribute appears to be NULL, likely has no attributes (searching for %.50s)",
				obj->ob_type->tp_name,
				name
			);
		}
	} else {
		res = NULL;
		PyErr_Format(
			PyExc_AttributeError,
			"'%.50s' object has no '__dict__'",
			obj->ob_type->tp_name
		);
	}
	return res;
}

static PyObject * simpleGet( PyObject * self, PyObject * args ) {
	/* A simple get-from-object-dict accellerator for vrml fields */
	char * name = NULL;
	PyObject * obj = NULL;
	PyObject * prop = NULL;
	PyObject * nameObj = NULL;
	PyObject * result = NULL;

	if (!PyArg_ParseTuple( args, "OO", &prop, &obj )) {
		return NULL;
	}
	/* XXX klass should produce property if not None
	if (klass & (klass != Py_None)) {
		/ Asking the class for the property /
		Py_INCREF(prop);
		return prop;
	}
	*/
	nameObj = PyObject_GetDictKey( prop, "name" );
	if (nameObj == NULL) {
		return NULL;
	}
	if (!PyString_Check( nameObj )) {
		PyErr_Format(
			PyExc_TypeError,
			"'%.50s' object 'name' attribute is of type %.50s, require str type.",
			prop->ob_type->tp_name,
			nameObj->ob_type->tp_name
		);
		/*Py_DECREF(nameObj);*/
		return NULL;
	}
	name = PyString_AsString( nameObj );
	/*Py_DECREF(nameObj);*/
	result = PyObject_GetDictKey( obj, name );
	if (!result) {
		/* need to call getDefault */
		PyErr_Clear();
		return PyObject_CallMethod( prop, "getDefault", "O", obj );
	} else {
		/* got a new reference to the value, return it */
		return result;
	}
}


static PyMethodDef fieldaccel_methods[] = {
	{"simpleGet", simpleGet, 1, "simpleGet( property, client )\n"\
								"C accellerator for vrml.field.fget\n"\
								"property -- vrml.field.Field object, must have \n"\
								"\t'name' attribute and getDefault method\n"\
								"client -- must have '__dict__'"},
	{NULL, NULL}
};

void
initfieldaccel(void)
{
	Py_InitModule("fieldaccel", fieldaccel_methods);
}
#ifdef __cplusplus
}
#endif
