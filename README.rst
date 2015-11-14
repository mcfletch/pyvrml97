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

Installation
-------------

It isn't common to directly install PyVRML97 itself (normally you want to 
install it as part of installing OpenGLContext), but should you wish to, you
can install via::

    $ pip install numpy PyDispatcher SimpleParse PyVRML97

The PyVRML97_accelerate module requires that you have a working compiler
(or, if you are on Windows, prebuilt wheels likely are available).
