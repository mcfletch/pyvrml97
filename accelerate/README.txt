PyVRML97-accelerate
===================

Scenegraph acceleration code for PyVRML97

This set of C extensions provides acceleration of common operations
within the PyVRML97 and OpenGLContext rendering engine.

The extensions build as standard Python extensions. Cython is used to
regenerate the C sources from the ``.pyx`` files when it is available;
otherwise the prebuilt ``.c`` sources are compiled directly. The numpy
headers are required to build the ``frustcullaccel`` and ``tmatrixaccel``
modules.

This package is part of the PyVRML97 project and is distributed under the
BSD license (see license.txt for details).
