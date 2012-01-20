"""VRML Directed Acyclic Graph library and VRML97 tools

This package is a partial representation of VRML97
node and prototype semantics based loosely on the
original mcf.vrml processing engine by the author.
It is strongly dependent on the Python 2.2.2 property
class, and as such will not likely be portable to
earlier python versions.

The package includes a full VRML97 parser and
lineariser based on the SimpleParse 2.0 parsing engine
(also by the author).

The vrml.vrml97 sub-package contains classes and
functions specifically relating to the VRML97 ISO
standard.  For instance, the vrml.vrml97.basenodes
file contains the "prototypes" for most of the
built-in nodes in the official specification.
"""
__version__ = "2.3.0a1"
__author__ = "Michael Colin Fletcher"
__license__ = "BSD-style, see license.txt for details"
