#!/usr/bin/env python
"""Installs vrml scenegraph modelling engine using setuptools (eggs)
"""
import os, sys
from setuptools import setup, find_packages, Extension
extensions = [
	Extension("vrml.fieldaccel", [
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
		Extension("vrml.tmatrixaccelnumpy", [
				os.path.join( 'accellerate', "tmatrixaccel.c")
			],
			include_dirs = includeDirectories,
			define_macros = definitions,
		),
		Extension("vrml.frustcullaccelnumpy", [
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
		Extension("vrml.tmatrixaccelnumeric", [
				os.path.join( 'accellerate', "tmatrixaccel.c")
			],
			undefine_macros = definitions,
		),
		Extension("vrml.frustcullaccelnumeric", [
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
		'keywords': 'VRML,VRML97,scenegraph',
		'long_description' : """VRML97 Scenegraph modelling objects for Python 

This project provides a core semantic model for VRML97 objects which
is close to (but not identical to) that specified in the VRML97 spec.
It is primarily used for the OpenGLContext project's VRML97 rendering
engine, but can also be used for generating, parsing or processing VRML97 
scenegraphs.
""",
		'platforms': ['Win32','Linux','OS-X','Posix'],
	}
	### Now the actual set up call

	setup (
		name = "PyVRML97",
		version = "2.2.0a1",
		description = "VRML97 Scenegraph model for Python",
		author = "Mike C. Fletcher",
		author_email = "mcfletch@vrplumber.com",
		url = "http://pyopengl.sourceforge.net/context/",
		license = "BSD-style, see license.txt for details",
		packages = [
			'vrml',
			'vrml.vrml97',
			'vrml.vrml200x',
		],

		package_dir = {
			'vrml':'vrml',
		},
		# non python files of examples      
		include_package_data = True,
		zip_safe = False,
		ext_modules=extensions,
		install_requires = [ 
			'PyDispatcher',
			'numpy',
		],
		dependency_links = [
			# SimpleParse
			"http://sourceforge.net/project/showfiles.php?group_id=55673",
			# PyDispatcher
			"http://sourceforge.net/project/showfiles.php?group_id=79755",
			# Numpy/Numeric
			"http://sourceforge.net/project/showfiles.php?group_id=1369",
		],
		extras_require = {
			#'numpy':  ["numpy"],
			'numeric':  ["Numeric"],
			'parsing': ["simpleparse"],
		},
		**extraArguments
	)
