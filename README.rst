PyVRML97 Scenegraph Model
==========================

PyVRML97 is the scenegraph model from `OpenGLContext`_ but can be used separately
in VRML97 processing tools. It relies on `SimpleParse`_, `PyDispatcher`_ and `Numpy`_
to provide the basic modelling functionality.

Properties (fields) in PyVRML97 follow the "Observer" pattern, and PyVRML97 
provides a cache mechanism that allows you to do cache invalidation when 
setting properties (fields). OpenGLContext uses that extensively to 
optimize the rendering process.

.. _`OpenGLContext`: https://pypi.python.org/pypi/OpenGLContext
.. _`SimpleParse`: https://pypi.python.org/pypi/SimpleParse
.. _`PyDispatcher`: https://pypi.python.org/pypi/PyDispatcher
.. _`Numpy`: https://pypi.python.org/pypi/numpy

`RELEASE-NOTES-2.3.5.md`_ says what changed for a program using this release,
including the two behaviour changes a caller may need to act on:
``transformmatrix.orthoMatrix`` is transposed, and ``Node.copy()`` copies the
whole subtree.

.. _`RELEASE-NOTES-2.3.5.md`: RELEASE-NOTES-2.3.5.md

Installation
-------------

It isn't common to directly install PyVRML97 itself (normally you want to 
install it as part of installing OpenGLContext), but should you wish to, you
can install via::

    $ pip install PyVRML97 PyVRML97_accelerate

The PyVRML97_accelerate module requires that you have a working compiler
(or, if you are on Windows, prebuilt wheels likely are available).

.. image:: https://ci.appveyor.com/api/projects/status/MikeCFletcher/pyvrml97/branch/master
    :target: https://ci.appveyor.com/project/MikeCFletcher/pyvrml97
    :alt: Appveyor Build

.. image:: https://img.shields.io/pypi/v/pyvrml97.svg
    :target: https://pypi.python.org/pypi/pyvrml97
    :alt: Latest PyPI Version

.. image:: https://img.shields.io/pypi/dm/pyvrml97.svg
    :target: https://pypi.python.org/pypi/pyvrml97
    :alt: Monthly download counter

Build/Release Process 
----------------------

* Push an annotated tag with `version` prefix (github workflow `build_and_publish.yml`)
