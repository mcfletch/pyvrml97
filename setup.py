#!/usr/bin/env python
"""Installs vrml scenegraph modelling engine using setuptools (eggs)
"""
from distutils.core import setup
import sys, os
sys.path.insert(0, '.' )

def find_version( ):
    for line in open( os.path.join(
        'vrml','__init__.py',
    )):
        if line.strip().startswith( '__version__' ):
            return eval(line.strip().split('=')[1].strip())
    raise RuntimeError( """No __version__ = 'string' in __init__.py""" )
version = find_version()


def is_package( path ):
    return os.path.isfile( os.path.join( path, '__init__.py' ))
def find_packages( root ):
    """Find all packages under this directory"""
    for path, directories, files in os.walk( root ):
        if is_package( path ):
            yield path.replace( '/','.' )

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
        'download_url': "https://sourceforge.net/projects/pyvrml97/files/PyVRML97/",
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
        version = version,
        description = "VRML97 Scenegraph model for Python",
        author = "Mike C. Fletcher",
        author_email = "mcfletch@vrplumber.com",
        options = {
            'sdist': {
                'formats':['gztar','zip'],
            },
        },
        url = "http://pyopengl.sourceforge.net/context/",
        license = "BSD",
        packages = list(find_packages( 'vrml' )),
        zip_safe = False,
        **extraArguments
    )
