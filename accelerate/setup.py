#!/usr/bin/env python
"""Builds acceleration functions for the VRML97 scenegraph

All project metadata lives in pyproject.toml; this file only declares the
C/Cython extension modules, which cannot be expressed as static metadata.
"""
import os
import sys
from setuptools import setup, Extension

SRC = "src"

try:
    from Cython.Build import cythonize
except ImportError:
    cythonize = None


def source(name):
    """Return the .pyx source when Cython is available, else the prebuilt .c."""
    suffix = ".pyx" if cythonize else ".c"
    return os.path.join(SRC, name + suffix)


extensions = [
    Extension("vrml_accelerate.fieldaccel2", [source("fieldaccel2")]),
]

try:
    import numpy
except ImportError:
    sys.stderr.write(
        "Unable to import numpy, skipping numpy extension building\n"
    )
else:
    include_dirs = [numpy.get_include()]
    extensions.extend([
        Extension(
            "vrml_accelerate.frustcullaccel",
            [source("frustcullaccel")],
            include_dirs=include_dirs,
            define_macros=[("USE_NUMPY", "1")],
        ),
        Extension(
            "vrml_accelerate.tmatrixaccel",
            [source("tmatrixaccel")],
            include_dirs=include_dirs,
        ),
    ])

if cythonize:
    extensions = cythonize(extensions)

if __name__ == "__main__":
    setup(ext_modules=extensions)
