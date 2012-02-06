#!/usr/bin/env python
"""Builds accelleration functions for the VRML97 scenegraph
"""
from distutils.core import setup,Extension
import sys, os
sys.path.insert(0, '.' )
try:
    from Cython.Distutils import build_ext
except ImportError, err:
    have_cython = False 
else:
    have_cython = True

def find_version( ):
    for line in open( '__init__.py'):
        if line.strip().startswith( '__version__' ):
            return eval(line.strip().split('=')[1].strip())
    raise RuntimeError( """No __version__ = 'string' in __init__.py""" )
version = find_version()

extensions = [
    Extension("vrml_accelerate.fieldaccel2", [
            os.path.join( 'src', ["fieldaccel2.c","fieldaccel2.pyx"][have_cython])
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
        Extension("vrml_accelerate.frustcullaccel", [
                os.path.join( 'src', ["frustcullaccel.c","frustcullaccel.pyx"][have_cython])
            ],
            include_dirs = includeDirectories,
            define_macros = definitions,
        ),
        Extension("vrml_accelerate.tmatrixaccel", [
                os.path.join( 'src', ["tmatrixaccel.c","tmatrixaccel.pyx"][have_cython])
            ],
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
        #'download_url': "https://sourceforge.net/projects/pyvrml97/files/PyVRML97/",
        'keywords': 'VRML,VRML97,scenegraph,accelerate,fields',
        'long_description' : """Scenegraph accelleration code for PyVRML97

This set of C extensions provides accelleration of common operations
within the PyVRML97 and OpenGLContext rendering engine.
""",
        'platforms': ['Win32','Linux','OS-X','Posix'],
    }
    ### Now the actual set up call
    if have_cython:
        extraArguments['cmdclass'] = {
            'build_ext': build_ext,
        }

    setup (
        name = "PyVRML97-accelerate",
        version = version,
        description = "Scenegraph acceleration code for PyVRML97",
        author = "Mike C. Fletcher",
        author_email = "mcfletch@vrplumber.com",
        url = "http://pyopengl.sourceforge.net/context/",
        license = "BSD-style, see license.txt for details",
        packages = ['vrml_accelerate'],
        # non python files of examples      
        ext_modules=extensions,
        options = {
            'sdist': {
                'formats': ['gztar','zip'],
            },
        },
        package_dir = {
            'vrml_accelerate':'.',
        },
        **extraArguments
    )
