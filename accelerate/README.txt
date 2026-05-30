PyVRML97-accelerate
===================

Scenegraph acceleration code for PyVRML97

This set of C extensions provides acceleration of common operations
within the PyVRML97 and OpenGLContext rendering engine.

The extensions build as standard Python extensions. The C wrappers are
regenerated from the ``.pyx`` sources by Cython at build time; the generated
``.c`` files are not committed or shipped. Cython and numpy are declared as
build dependencies in ``pyproject.toml``, so a PEP 517 build (e.g. ``pip
install`` or ``python -m build``) installs them automatically. The numpy
headers are required to build the ``frustcullaccel`` and ``tmatrixaccel``
modules.

This package is part of the PyVRML97 project and is distributed under the
BSD license (see license.txt for details).
