"""The array operations the scenegraph is built on

One place for them, so that a consumer writes ``from vrml.arrays import
dot`` rather than reaching for numpy itself, and so that the few
scenegraph-shaped helpers -- :func:`safeCompare`, :func:`contiguous` -- sit
beside the numpy names they wrap.
"""
from typing import Any

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
    """Whether two field values are the same, without a numpy truth test

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
        except Exception:
            pass                # ragged, or holding something numpy refuses
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
    """Force to a contiguous array"""
    return array(a, typeCode(a))


#: What `from vrml.arrays import *` provides.
#:
#: Declared rather than left to the star import. Without it a checker either
#: sees nothing here -- so every `arrays.dot` in a consumer is an error in
#: correct code -- or sees all 500 of numpy's names, which then shadow things
#: the consumer defines itself: numpy's `log` ufunc landing on a module's
#: `log = logging.getLogger(...)` is the one that bites.
#:
#: The list is what the packages that use this abstraction actually reach for,
#: read from their source. A name a consumer needs and this omits is a
#: NameError there, so the suites are what say this is complete; a checker
#: reading a consumer will name anything missing.
#: Deliberately absent: `log`, `tan` and `radians`. numpy's is a ufunc, and a consumer that does
#: `from vrml.arrays import *` and then `log = logging.getLogger(__name__)` --
#: which a dozen of them do -- has the two land on one name. Re-exporting it
#: makes that a shadowing error in every one of them, and nothing here wants
#: the logarithm badly enough to pay for it, and nothing in the workspace
#: imports it from here by name.
#:
#: `sin`, `cos`, `sqrt`, `radians` and `tan` are here despite the same clash,
#: because modules do ask for them by name and because the array versions are
#: the ones wanted: `utilities.normalise` answers float32, and `x *
#: math.sin(r)` keeps a float32 where `x * ar.sin(r)` widens to float64. A
#: module that means the scalar one should say `math.` and be read as meaning
#: it -- which is what `quaternion.py` now does.

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
