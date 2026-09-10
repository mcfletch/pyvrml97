"""Abstraction point allowing use with numpy or Numeric

Chooses numpy if available because when it's installed
Numeric tends to be a bit flaky...
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
# Now deal with differing numpy APIs...
a = array([1, 2, 3], 'i')
ArrayType = ndarray  # alias removed in later versions
# Take's API changed from Numeric, we've updated to
# always provide axis now...
if hasattr(a, '__array_typestr__'):

    def typeCode(a: Any) -> str:
        """Retrieve the typecode for the given array

        Depending on whether you access the classic or new API
        you have different access methods, so we have to use
        the typecode() method if __array_typestr__ isn't there.
        """
        try:
            return a.__array_typestr__
        except AttributeError:
            return a.typecode()

else:

    def typeCode(a: Any) -> str:
        """Retrieve the typecode for the given array

        Depending on whether you access the classic or new API
        you have different access methods, so we have to use
        the typecode() method if .dtype.char isn't there.
        """
        try:
            return a.dtype.char
        except AttributeError:
            return a.typecode()


del a
implementation_name = 'numpy'
try:
    # PyVRML97 is from before numpy printed errors, we explicitly do not care
    # about the divide-by-zero, which commonly happens in mesh data processing
    # TODO: likely should rework the mesh processing to check manually and remove
    # this sledge-hammer approach
    seterr(all='ignore')
except Exception as err:
    pass


def safeCompare(first: Any, second: Any) -> bool:
    """Watch out for pointless numpy truth-value checks"""
    if first is None:
        if second is None:
            return True
        else:
            return False
    elif second is None:
        return False
    if isinstance(first, (int, float, str)):
        return first == second
    if isinstance(first, ArrayType) and isinstance(second, ArrayType):
        return bool(any(first == second))
    elif type(first) is not type(second):
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
