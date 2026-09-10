#!/usr/bin/env python
"""Builds acceleration functions for the VRML97 scenegraph

All project metadata lives in pyproject.toml; this file only declares the
Cython extension modules, which cannot be expressed as static metadata.

Cython and numpy are declared as build dependencies in pyproject.toml, so the
C wrappers are regenerated from the .pyx sources at build time rather than
being committed or shipped in the source distribution.
"""
import glob
import os

import numpy
from setuptools import setup, Extension
from Cython.Build import cythonize

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "src"
#: Where the generated C is written, and so kept out of the source tree and
#: out of the sdist: only the .pyx sources are tracked and distributed.
BUILD_DIR = "build"
#: Where the toolchain the generated C was written against is recorded.
TOOLCHAIN_STAMP = os.path.join(HERE, BUILD_DIR, '.cython-toolchain')

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


def _toolchain():
    """Cython and numpy as the generated C sees them: version strings.

    numpy is in here because these modules ``cimport numpy``, and what that
    expands to is numpy's own declarations rather than anything in this
    package.
    """
    from Cython import __version__ as cython_version

    return 'cython %s\nnumpy %s\n' % (cython_version, numpy.__version__)


def drop_c_from_another_toolchain():
    """Delete generated C that a different Cython or numpy wrote.

    ``cythonize`` decides whether to rewrite a ``.c`` by comparing it against
    the ``.pyx`` and the ``.pxd`` files that ``.pyx`` cimports. A
    wheel-installed numpy carries the timestamps recorded in the wheel, so its
    declarations can be years older than a ``.c`` generated from a *previous*
    numpy last week -- and the stale C is then compiled against headers that
    no longer match it. What that reports is a compile error inside a numpy
    internal, naming nothing in this package.

    The generated C is not tracked by git and every ``.pyx`` beside it is
    shipped, so it can always be written again.
    """
    wanted = _toolchain()
    try:
        with open(TOOLCHAIN_STAMP, encoding='utf-8') as handle:
            if handle.read() == wanted:
                return
    except OSError:
        pass
    for path in glob.glob(os.path.join(HERE, BUILD_DIR, SRC, '*.c')):
        os.unlink(path)
    os.makedirs(os.path.dirname(TOOLCHAIN_STAMP), exist_ok=True)
    with open(TOOLCHAIN_STAMP, 'w', encoding='utf-8') as handle:
        handle.write(wanted)


if __name__ == "__main__":
    # Only under the guard: importing this file must not delete anything.
    drop_c_from_another_toolchain()
    setup(ext_modules=cythonize(extensions, language_level="3",
                                build_dir=BUILD_DIR))
