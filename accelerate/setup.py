#!/usr/bin/env python
"""Builds acceleration functions for the VRML97 scenegraph

All project metadata lives in pyproject.toml; this file only declares the
Cython extension modules, which cannot be expressed as static metadata.

Cython and numpy are declared as build dependencies in pyproject.toml, so the
C wrappers are regenerated from the .pyx sources at build time rather than
being committed or shipped in the source distribution.
"""
import numpy
from setuptools import setup, Extension
from Cython.Build import cythonize

SRC = "src"

include_dirs = [numpy.get_include()]

extensions = [
    Extension("vrml_accelerate.fieldaccel2", [f"{SRC}/fieldaccel2.pyx"]),
    Extension(
        "vrml_accelerate.frustcullaccel",
        [f"{SRC}/frustcullaccel.pyx"],
        include_dirs=include_dirs,
        define_macros=[("USE_NUMPY", "1")],
    ),
    Extension(
        "vrml_accelerate.tmatrixaccel",
        [f"{SRC}/tmatrixaccel.pyx"],
        include_dirs=include_dirs,
    ),
]

if __name__ == "__main__":
    # build_dir keeps the generated .c out of the source tree (and thus out of
    # the sdist), so only the .pyx sources are tracked and distributed.
    setup(ext_modules=cythonize(extensions, language_level="3", build_dir="build"))
