#!/usr/bin/env python
"""Builds accelleration functions for the VRML97 scenegraph
"""
from distutils.core import setup,Extension
import sys, os
sys.path.insert(0, '.' )

def is_package( path ):
	return os.path.isfile( os.path.join( path, '__init__.py' ))
def find_packages( root ):
	"""Find all packages under this directory"""
	for path, directories, files in os.walk( root ):
		if is_package( path ):
			yield path.replace( '/','.' )

extensions = [
	Extension("vrml_accellerate.fieldaccel", [
			os.path.join( 'accellerate', "fieldaccel.c")
			# is just a Python-API function...
		],
	),
]

try:
	import numpy
except ImportError, err:
	sys.stderr.write(
		"""Unable to import numpy, skipping numpy extension building\n"""
	)
else:
	if hasattr( numpy, 'get_include' ):
		includeDirectories = [
			numpy.get_include(),
		]
	else:
		includeDirectories = [
			os.path.join(
				os.path.dirname( numpy.__file__ ),
				'core',
				'include',
			),
		]
	definitions = [
		('USE_NUMPY', True ),
	]
	extensions.extend( [
		Extension("vrml_accellerate.tmatrixaccelnumpy", [
				os.path.join( 'accellerate', "tmatrixaccel.c")
			],
			include_dirs = includeDirectories,
			define_macros = definitions,
		),
		Extension("vrml_accellerate.frustcullaccelnumpy", [
				os.path.join( 'accellerate', "frustcullaccel.c")
			],
			include_dirs = includeDirectories,
			define_macros = definitions,
		),
	])
try:
	import Numeric
except ImportError, err:
	sys.stderr.write(
		"""Unable to import Numeric, skipping Numeric extension building\n"""
	)
else:
	definitions = [
		('USE_NUMPY', False ),
	]
	extensions.extend( [
		Extension("vrml_accellerate.tmatrixaccelnumeric", [
				os.path.join( 'accellerate', "tmatrixaccel.c")
			],
			undefine_macros = definitions,
		),
		Extension("vrml_accellerate.frustcullaccelnumeric", [
				os.path.join( 'accellerate', "frustcullaccel.c")
			],
			undefine_macros = definitions,
		),
	])
	

if __name__ == "__main__":
	extraArguments = {
		'classifiers': [
			"""License :: OSI Approved :: BSD License""",
			"""Programming Language :: Python""",
			"""Programming Language :: C""",
			"""Topic :: Software Development :: Libraries :: Python Modules""",
			"""Topic :: Multimedia :: Graphics :: 3D Rendering""",
			"""Intended Audience :: Developers""",
		],
		'download_url': "https://sourceforge.net/project/showfiles.php?group_id=19262",
		'keywords': 'VRML,VRML97,scenegraph,accellerate,fields',
		'long_description' : """Scenegraph accelleration code for PyVRML97

This set of C extensions provides accelleration of common operations
within the PyVRML97 and OpenGLContext rendering engine.
""",
		'platforms': ['Win32','Linux','OS-X','Posix'],
	}
	### Now the actual set up call

	setup (
		name = "PyVRML97-accellerate",
		version = "2.2.0a1",
		description = "Scenegraph accelleration code for PyVRML97",
		author = "Mike C. Fletcher",
		author_email = "mcfletch@vrplumber.com",
		url = "http://pyopengl.sourceforge.net/context/",
		license = "BSD-style, see license.txt for details",
		packages = list(find_packages( 'vrml_accellerate')),
		# non python files of examples      
		ext_modules=extensions,
		**extraArguments
	)