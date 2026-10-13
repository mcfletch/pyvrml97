"""The array operations the scenegraph is built on

One place for them, so that a consumer writes ``from vrml.arrays import
dot`` rather than reaching for numpy itself, and so that the few
scenegraph-shaped helpers -- :func:`safeCompare`, :func:`contiguous` -- sit
beside the numpy names they wrap.
"""
from collections.abc import Sequence
from typing import Any, TypeAlias

# Named rather than starred. `from numpy import *` puts 500 names in this
# module so that consumers can reach about sixty of them, and every one of
# those is then a name a consumer's own `from vrml.arrays import *` can shadow
# -- numpy's `log` ufunc landing on a module's `log = logging.getLogger(...)`
# is the one that bites. What is imported here is what `__all__` at the foot of
# this module offers, plus what the module needs to build them.
from numpy import (
    abs, acos, allclose, angle, any,
    append, arange, arccos, argmax, argmin, argsort, array,
    asarray, ascontiguousarray, astype, char, character, clip,
    compress, concatenate, copy, cos, cross, diff, divide,
    dot, dtype, e, flatnonzero, flip, frombuffer, half,
    identity, indices, less, less_equal, matrix, max, min,
    ndarray, negative, nonzero, ones, pi, put, radians,
    ravel, record, repeat, reshape, resize, seterr, shape,
    sin, size, spacing, sqrt, sum, swapaxes, take,
    tan, test, tile, transpose, where, zeros,
)
from numpy import float64
from numpy.typing import NDArray

try:
    # TODO: don't import this here, as it's not
    # actually *used* in pyvrml97, it's just used
    # in OpenGLContext...
    from vrml_accelerate import frustcullaccel
except ImportError as err:
    frustcullaccel = None
# why did this get taken out?  Is divide now safe?
divide_safe = divide
#: numpy dropped the name; a field type asks for it by this one.
ArrayType = ndarray
#: A 4x4 transformation matrix of doubles. The annotation carries the element
#: type; numpy's own functions return arrays of unknown shape, so a 4x4 shape
#: written here would be a cast at every place one is made.
Matrix4: TypeAlias = NDArray[float64]
#: A matrix and its inverse, or two Nones where both are the identity.
MatrixPair: TypeAlias = 'tuple[Matrix4, Matrix4] | tuple[None, None]'
#: The components of a vector or rotation: a sequence or an array.
Components: TypeAlias = 'Sequence[int] | Sequence[float] | NDArray[Any]'


def typeCode(a: Any) -> str:
    """The array's element type, as the one-character code a field names"""
    return a.dtype.char


implementation_name = 'numpy'
# A divide by zero is ordinary in mesh processing here -- a degenerate face,
# a zero-length normal -- and each place that can produce one answers for the
# result it wants. Printing a warning per occurrence would say nothing a
# caller can act on.
# TODO: check for these where they arise and take the setting off again.
seterr(all='ignore')


def safeCompare(first: Any, second: Any) -> bool:
    """Check for equality with array-aware handling

    Comparing two arrays answers an array, and `bool()` of that raises rather
    than answering -- which is what makes a plain `==` unusable here.

    A sequence is read as an array first, because the two sides are often the
    same value in two shapes: a node declares its default as a list of numbers
    and stores its value as an array, and the lineariser asks this to decide
    whether a field is still at its default and so need not be written.
    """
    if first is None or second is None:
        return first is None and second is None
    if isinstance(first, (int, float, str)):
        return bool(first == second)
    if isinstance(first, (ArrayType, list, tuple)) and isinstance(
        second, (ArrayType, list, tuple)
    ):
        try:
            first, second = asarray(first), asarray(second)
        except ValueError:
            pass                # ragged: compared as sequences below
        else:
            if first.shape != second.shape:
                return False
            # `all`, because every element has to match: a translation of
            # (1,0,0) shares two of three with the (0,0,0) it defaults to.
            return bool((first == second).all())
    if type(first) is not type(second):
        return False
    return bool(first == second)


def contiguous(a: Any) -> Any:
    """Force the array a to be a contiguous array of the same type"""
    return array(a, typeCode(a))


#: What `from vrml.arrays import *` provides.
#:
#: `sin`, `cos`, `sqrt`, `radians` and `tan` are here despite having
#: name clashes, `log` is explicitly left out because it produces too
#: many conflicts

__all__ = [
    'ArrayType', 'abs', 'acos', 'allclose', 'angle', 'any',
    'append', 'arange', 'arccos', 'argmax', 'argmin', 'argsort',
    'array', 'asarray', 'ascontiguousarray', 'astype', 'char',
    'character', 'clip', 'compress', 'concatenate', 'contiguous', 'copy',
    'cos', 'cross', 'diff', 'divide', 'divide_safe', 'dot',
    'dtype', 'e', 'flatnonzero', 'flip', 'frombuffer', 'frustcullaccel',
    'half', 'identity', 'implementation_name', 'indices', 'less', 'less_equal',
    'matrix', 'max', 'min', 'negative', 'nonzero', 'ones',
    'pi', 'put', 'radians', 'ravel', 'record', 'repeat',
    'reshape', 'resize', 'safeCompare', 'shape', 'sin', 'size',
    'spacing', 'sqrt', 'sum', 'swapaxes', 'take', 'tan',
    'test', 'tile', 'transpose', 'typeCode', 'where', 'zeros',
]
