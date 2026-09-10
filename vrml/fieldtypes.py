"""Definitions of the standard VRML97 field-types

These are all of the "low-level" field-types
(i.e. not nodes) defined by VRML97.  Each has
a canonical in-memory storage format so that
code can rely on that format when dealing with
the field values.

We use Numeric Python arrays whereever possible.
"""

from typing import Any, Optional, TYPE_CHECKING, Tuple
import operator
from vrml import field, csscolors, arrays
import sys
from functools import reduce



if TYPE_CHECKING:
    class _FieldHost:
        """What the mix-ins below need from the `field.Field` beside them.

        Each `_SF*`/`_MF*` class here is one half of a field type: it holds the
        coercion and checking rules for one VRML97 value, and is combined with
        `field.Field`, which holds the name, the default and the descriptor
        protocol -- ``class SFInt32(_SFInt32, field.Field)``.  Declaring the
        half's side of that arrangement is what lets the coercion code be read
        on its own.

        Nothing at run time: the name is `object` there, so the mix-ins have
        the bases they always had.
        """

        name: str
        defaultobj: Any
        dimension: Tuple[int, ...]
        #: Whether `defaultobj` is a factory to call rather than a value to
        #: hand out.  An attribute on `BaseField`, not a method.
        call_default: bool

        def typeName(self) -> str: ...
        def coerce(self, value: Any) -> Any: ...
        def fset(self, client: Any, value: Any, notify: Any = True) -> Any: ...
        def fdel(self, client: Any, notify: Any = True) -> Any: ...
else:
    _FieldHost = object

MAX_INT = sys.maxsize

DOUBLE_TYPE = arrays.typeCode(arrays.array([0], 'd'))
FLOAT_TYPE = arrays.typeCode(arrays.array([0], 'f'))
INT_TYPE = arrays.typeCode(arrays.array([0], 'i'))
UINT_TYPE = arrays.typeCode(arrays.array([0], 'I'))


def _collapse(inlist: Any, isinstance: Any=isinstance, ltype: Any=list, maxint: int=MAX_INT) -> Any:
    '''
    Destructively flatten a list hierarchy to a single level.
    Non-recursive, and (as far as I can see, doesn't have any
    glaring loopholes).
    Further speedups and obfuscations by Tim Peters :)
    '''
    try:
        # for every possible index
        for ind in range(maxint):
            # while that index currently holds a list
            while isinstance(inlist[ind], ltype):
                # expand that list into the index (and subsequent indicies)
                inlist[ind : ind + 1] = inlist[ind]
            # ind = ind+1
    except IndexError:
        pass
    return inlist


def collapse(inlist: Any) -> Any:
    '''
    As _collapse, but works on a copy of the inlist
    '''
    return _collapse(list(inlist))


def _linvalues(lineariser: Any) -> Any:
    """Get the linearisation values for a lineariser"""
    if lineariser is None:
        from vrml.vrml97 import linearise

        return linearise.defaults
    else:
        return lineariser.linvalues


def SFString_vrmlstr(value: Any, lineariser: Any=None) -> str:
    """Convert the given value to a VRML97 representation"""
    return '"%s"' % ('\\"'.join('\\\\'.join(value.split('\\')).split('"')))


def MFString_vrmlstr(value: Any, lineariser: Any=None) -> str:
    """Convert the given value to a VRML97 representation"""
    if not value:
        return "[ ]"
    anyobject = [SFString_vrmlstr(v, lineariser) for v in value]
    linvalues = _linvalues(lineariser)
    length = reduce(operator.add, [len(obj) for obj in anyobject])
    if length > 60:
        sep = '%(subelspacer)s\n%(curindent)s%(indent)s' % linvalues
        if len(anyobject) > 1:
            result = ['[']
        else:
            result = []
        for element in anyobject:
            if result:
                result.append(sep)
            result.append(element)
        if len(anyobject) > 1:
            result.append('\n%(curindent)s]\n' % linvalues)
        return "".join(result)
    elif len(anyobject) > 1:
        return '[ %s ]' % linvalues['subelspacer'].join(anyobject)
    else:
        return linvalues['subelspacer'].join(anyobject)


def SFFloat_vrmlstr(value: Any, lineariser: Any=None) -> str:
    """Convert floats to (compact) VRML97 representation"""
    rpr = str(value)
    if rpr == '0.0':
        return '0'
    elif rpr[:2] == '0.':
        return rpr[1:]
    elif rpr[:3] == '-0.':
        return '-' + rpr[2:]
    elif rpr[-2:] == '.0':
        return rpr[:-2]
    else:
        return rpr


def MFSimple_vrmlstr(value: Any, lineariser: Any=None) -> str:
    """Convert value to a VRML97 representation"""
    linvalues = _linvalues(lineariser)
    stringreps = [str(obj) for obj in value]
    stringsets = []
    setLength = 100  # 100 is arbitrary
    while stringreps:
        stringsets.append(linvalues['numsep'].join(stringreps[:setLength]))
        del stringreps[:setLength]
    return '[ %s ]' % ('\n'.join(stringsets))


# `str is bytes` is the Python 2 test, and it is False on every
# interpreter this package supports, so only the branch below it ran.

class _SFString(_FieldHost):
    """SFString field/event type base-class"""

    defaultDefault = ""

    @classmethod
    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type
        Allowable types:
            simple string -> unchanged
            str -> utf-8 encoded

            sequence of length == 1 where first element is a string -> returns first element
            sequence of length > 1 where all elements are strings -> returns string.join( value, '')
        """
        if isinstance(value, bytes):
            return value.decode('utf-8')
        elif isinstance(value, field.UNPACK_TYPES):
            # A map, zip or range has no length; draw the values out before
            # measuring, as the multi-value types do.
            value = list(value)
        # `tuple, list` rather than `field.SEQUENCE_TYPES`: the lazy members of
        # that tuple have just been drawn out, and these two are what is left.
        if isinstance(value, (tuple, list)):
            if value and len(value) == 1:
                value = value[0]
            elif not value:
                value = u""
            else:
                value = u"".join(value)
        if not isinstance(value, str):
            value = str(value)
        return value

    @classmethod
    def check(self, value: Any) -> int:
        "Raise ValueError if isn't correct type"
        if not isinstance(value, str):
            return 0
        return 1

    vrmlstr = staticmethod(SFString_vrmlstr)


class _MFString(_FieldHost):
    """MFString field/event type base-class"""

    defaultDefault = list

    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type
        Allowable types:
            simple string -> wrapped in a list
            sequence of strings (of any length) -> equivalent list returned
        """
        if isinstance(value, str):
            value = [value]
        try:
            return [SFString.coerce(item) for item in value]
        except ValueError as error:
            raise ValueError(
                """Attempted to set value %r for an %s field which is not compatible: %s"""
                % (value, self.typeName(), error)
            ) from error

    def check(self, value: Any) -> int:
        "Whether the value is already a list of strings"
        if isinstance(value, list):
            return int(all(isinstance(item, str) for item in value))
        return 0

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return value[:]

    vrmlstr = staticmethod(MFString_vrmlstr)


class _SFBool(_FieldHost):
    """SFBool field/event type base-class"""

    defaultDefault = 0

    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type
        Allowable types:
            any object with true/false protocol
        """
        if isinstance(value, str):
            try:
                value = int(value)
            except (ValueError, TypeError):
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
        if value:
            return 1
        else:
            return 0

    def check(self, value: Any) -> int:
        """Check that the given value is of exactly expected type"""
        if value in (0, 1):
            return 1
        return 0

    def vrmlstr(self, value: Any, lineariser: Any=None) -> Any:
        """Convert the given value to a VRML97 representation"""
        if value:
            return 'TRUE'
        else:
            return 'FALSE'


class _SFInt32(_FieldHost):
    """SFInt32 field/event type base-class"""

    defaultDefault = 0

    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type
        Allowable types:
            any object with true/false protocol
        """
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                """Attempted to set value for an %s field which is not compatible: %s"""
                % (self.typeName(), repr(value))
            ) from None

    def check(self, value: Any) -> int:
        """Check that the given value is of exactly expected type"""
        if isinstance(value, int):
            return 1
        return 0

    def vrmlstr(self, value: Any, lineariser: Any=None) -> Any:
        """Convert the given value to a VRML97 representation"""
        try:
            return str(int(value))
        except OverflowError:
            base = str(value)
            if base and base[-1] in ('l', 'L'):
                base = base[:-1]
            return base + ' # Overly long number\n'


class _SFUInt32(_SFInt32):
    """SFUInt32 base-class"""

    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type
        Allowable types:
            any object with true/false protocol
        """
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                """Attempted to set value for an %s field which is not compatible: %s"""
                % (self.typeName(), repr(value))
            ) from None

    def check(self, value: Any) -> int:
        """Check that the given value is of exactly expected type"""
        if isinstance(value, int):
            return 1
        return 0

    def vrmlstr(self, value: Any, lineariser: Any=None) -> Any:
        """Convert the given value to a VRML97 representation"""
        base = str(int(value))
        if base[-1] in ('l', 'L'):
            base = base[:-1]
        return base


class _SFFloat(_FieldHost):
    """SFFloat field/event type base-class"""

    defaultDefault = 0.0

    def coerce(self, value: Any) -> Any:
        """Coerce the given value to our type
        Allowable types:
            any object with true/false protocol
        """
        try:
            return float(value)
        except ValueError:
            raise ValueError(
                """Attempted to set value for an %s field which is not compatible: %s"""
                % (self.typeName(), repr(value))
            ) from None

    def check(self, value: Any) -> int:
        """Check that value is of precisely the expected data type"""
        if isinstance(value, float):
            return 1
        return 0

    vrmlstr = staticmethod(SFFloat_vrmlstr)


class _SFTime(_SFFloat):
    """SFTime field/event type base-class"""

    defaultDefault = 0.0


class _MFInt32(_FieldHost):
    """MFInt32 field/event type base-class

    Stored as a flat Numeric-python array
    """

    defaultDefault = list
    arrayDataType = 'i'
    acceptedTypes = ('i', INT_TYPE)
    base_converter = int

    def coerce(self, value: Any) -> Any:
        """Base coercion mechanism for multiple-value integer fields"""
        if isinstance(value, str):
            value = [self.base_converter(x) for x in value.replace(',', ' ').split()]
        if isinstance(value, field.NUMERIC_TYPES):
            return arrays.array([int(value)], self.arrayDataType)
        elif isinstance(value, arrays.ArrayType):
            if arrays.typeCode(value) not in self.acceptedTypes:
                value = value.astype(self.arrayDataType)
            return arrays.contiguous(arrays.ravel(value))
        elif isinstance(value, field.SEQUENCE_TYPES):
            return arrays.array(
                [int(obj) for obj in value],
                self.arrayDataType,
            )
        elif not value:
            return arrays.array([], self.arrayDataType)
        raise ValueError(
            """Attempted to set value for an %s field which is not compatible: %s"""
            % (self.typeName(), repr(value))
        )

    vrmlstr = staticmethod(MFSimple_vrmlstr)

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return arrays.array(value, arrays.typeCode(value))


class _MFUInt32(_MFInt32):
    """Unsigned integer version of MFInt32 (mostly for indices)"""

    defaultDefault = list
    arrayDataType = 'I'
    base_converter = int
    acceptedTypes = ('I', UINT_TYPE)


class _SFImage(_MFInt32):
    """SFImage field/event type base-class

    SFImage = MFInt32, should do something more
    intelligent, such as auto-compiling those to
    mip-mapped images, or at least storing them
    efficiently.
    """

    defaultDefault = list
    arrayDataType = 'I'
    acceptedTypes = ('I', UINT_TYPE)


class _MFFloat(_FieldHost):
    """MFFloat field/event type base-class

    Stored as a flat Numeric-python array
    """

    defaultDefault = list
    acceptedTypes = ('d', DOUBLE_TYPE)
    targetType = DOUBLE_TYPE

    def coerce(self, value: Any) -> Any:
        """Base coercion mechanism for floating point field types"""
        if isinstance(value, str):
            value = [float(x) for x in value.replace(',', ' ').split()]
        if isinstance(value, field.NUMERIC_TYPES):
            return arrays.array([float(value)], self.targetType)
        elif isinstance(value, arrays.ArrayType):
            if arrays.typeCode(value) not in self.acceptedTypes:
                value = value.astype(self.targetType)
            return arrays.contiguous(arrays.ravel(value))
        elif isinstance(value, field.SEQUENCE_TYPES):
            return arrays.array(
                [float(x) for x in collapse(value)],
                self.targetType,
            )
        elif not value:
            return arrays.array([], self.targetType)
        raise ValueError(
            """Attempted to set value for an %s field which is not compatible: %s"""
            % (self.typeName(), repr(value))
        )

    vrmlstr = staticmethod(MFSimple_vrmlstr)

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return arrays.array(value, arrays.typeCode(value))


class _MFFloat32(_MFFloat):
    """32-BIT floating-point type"""

    acceptedTypes = ('f', FLOAT_TYPE)
    targetType = FLOAT_TYPE
    fieldType = 'MFFloat32'


class _MFTime(_MFFloat):
    """MFTime field/event type base-class

    Stored as a flat Numeric-python array
    """


class _SFVec(_FieldHost):
    """SFVecXX field/event type base-class

    Stored as a Numeric-python double array of self.length
    """

    acceptedTypes = ('d', DOUBLE_TYPE)
    targetType = DOUBLE_TYPE
    #: The shape a value of this field has. Each field type gives its own
    #: -- (4,) for a rotation, (4,4) for a matrix -- so this says "some
    #: number of ints" rather than fixing the length at the base.
    dimension: Tuple[int, ...] = (3,)  # our dimension...

    #: `length` memoised; None until it is first asked for.  The dimension of
    #: a field type does not change, so it is worked out once per field.
    _length: "Optional[int]" = None

    @property
    def length(self) -> int:
        """How many numbers one value of this field holds

        The product of :attr:`dimension`: three for an SFVec3f, four for an
        SFRotation.  An MFVec divides its printed output into rows of this
        many, so writing a scene out reads it.
        """
        if self._length is None:
            self._length = reduce(operator.mul, self.dimension)
        return self._length

    def defaultDefault(self) -> Any:
        """Default default value for vectors/colours"""
        return arrays.zeros(self.dimension, self.targetType)

    def coerce(self, value: Any) -> Any:
        """Base coercion mechanism for vector-like field types"""
        if isinstance(value, str):
            value = [float(x) for x in value.replace(',', ' ').split()]
        if isinstance(value, (int, float)):
            value = arrays.zeros(self.dimension, self.targetType)
            value[:] = float(value)
        elif isinstance(value, arrays.ArrayType):
            if arrays.typeCode(value) not in self.acceptedTypes:
                value = value.astype(self.targetType)
            value = value.reshape(self.dimension)
        elif isinstance(value, field.SEQUENCE_TYPES):
            value = arrays.asarray([float(x) for x in collapse(value)], self.targetType)
            value.reshape(self.dimension)
        else:
            try:
                value = arrays.asarray(value, self.targetType)
            except Exception:
                raise ValueError(
                    """Attempted to set value for an %s field which is not compatible: %s"""
                    % (self.typeName(), repr(value))
                ) from None
            else:
                value.reshape(self.dimension)
        if value.shape != self.dimension:
            raise ValueError(
                """%s value of incorrect shape (is %s, should be %s)"""
                % (
                    self.__class__.__name__,
                    value.shape,
                    self.dimension,
                )
            )
        value = arrays.contiguous(value)
        return value

    def vrmlstr(self, value: Any, lineariser: Any=None) -> Any:
        """Convert the given value to a VRML97 representation"""
        return _linvalues(lineariser)['numsep'].join(
            [SFFloat_vrmlstr(obj, lineariser) for obj in value]
        )

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return arrays.array(value, arrays.typeCode(value))


class _Color(_FieldHost):
    """Mix-in for colour-value clamping and string coercion"""

    def coerce(self, value: Any) -> Any:
        """Adds clipping of values to 0.0 through 1.0 range"""
        value = super(_Color, self).coerce(value)
        value = arrays.clip(value, 0.0, 1.0)
        return value

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return arrays.array(value, arrays.typeCode(value))


class _SFArray(_FieldHost):
    """Base class which holds a single array-type value (can be arbitrarily spec'd numpy array)"""

    defaultDefault = list
    #: The array type codes a value may already be in. Subclasses give
    #: their own and there are not always three, so the length is open.
    acceptedTypes: Tuple[Any, ...] = ('d', DOUBLE_TYPE, 'V')
    targetType = DOUBLE_TYPE

    def reshape(self, value: Any) -> Any:
        """Do reshape of value to our target dimensions"""
        return value

    def coerce(self, value: Any) -> Any:
        if isinstance(value, str):
            value = [
                float(x)
                for x in (value.replace(',', ' ').replace('[', ' ')
                          .replace(']', ' ').split())
            ]
        if field.UNPACK_TYPES and isinstance(value, field.UNPACK_TYPES):
            value = list(value)
        if isinstance(value, arrays.ArrayType):
            if arrays.typeCode(value) not in self.acceptedTypes:
                value = value.astype(self.targetType)
        elif isinstance(value, field.SEQUENCE_TYPES):
            try:
                value = arrays.array(value, self.targetType)
            except ValueError:
                value = arrays.array(
                    [float(obj) for obj in value],
                    self.targetType,
                )
        elif isinstance(value, (int, float)):
            value = arrays.array([value], self.targetType)
        else:
            try:
                value = arrays.asarray(value, self.targetType)
            except Exception:
                raise ValueError(
                    """Attempted to set value for an %s field which is not compatible: %s"""
                    % (self.typeName(), repr(value))
                ) from None
        # special casing, again, for explicitly structured arrays
        if not arrays.typeCode(value) == 'V':
            value = arrays.contiguous(self.reshape(value))
        return value

    def check(self, value: Any) -> int:
        """Check that the given value is of exactly the expected type"""
        if isinstance(value, arrays.ArrayType):
            typeCode = arrays.typeCode(value)
            if typeCode in self.acceptedTypes:
                if typeCode == 'V':
                    # special vector type
                    return 1
                else:
                    s = arrays.shape(value)
                    if len(s) == len(self.dimension) + 1 and s[1:] == self.dimension:
                        return 1
        return 0

    def vrmlstr(self, value: Any, lineariser: Any=None) -> Any:
        """Convert the given value to a VRML97 representation"""
        return str(value)

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return arrays.array(value, arrays.typeCode(value))


class _SFArray32(_SFArray):
    """32-bit version of SFArrays"""

    acceptedTypes = ('f', FLOAT_TYPE, 'V')
    targetType = FLOAT_TYPE


class _MFVec(_SFArray):
    """MFVecXX field/event type base-class

    Stored as x * self.length Numeric Python double array
    """

    defaultDefault = list
    acceptedTypes = ('d', DOUBLE_TYPE)
    targetType = DOUBLE_TYPE
    #: As `_SFVec.dimension`: each field type gives its own shape.
    dimension: Tuple[int, ...] = (3,)  # our dimension...

    #: `length` memoised; None until it is first asked for.  The dimension of
    #: a field type does not change, so it is worked out once per field.
    _length: "Optional[int]" = None

    @property
    def length(self) -> int:
        """How many numbers one value of this field holds

        The product of :attr:`dimension`: three for an SFVec3f, four for an
        SFRotation.  An MFVec divides its printed output into rows of this
        many, so writing a scene out reads it.
        """
        if self._length is None:
            self._length = reduce(operator.mul, self.dimension)
        return self._length

    def reshape(self, value: Any) -> Any:
        return arrays.reshape(value, (-1,) + self.dimension)

    def check(self, value: Any) -> int:
        """Check that the given value is of exactly the expected type"""
        if isinstance(value, arrays.ArrayType):
            if arrays.typeCode(value) in self.acceptedTypes:
                s = arrays.shape(value)
                if len(s) == len(self.dimension) + 1 and s[1:] == self.dimension:
                    return 1
        return 0

    def vrmlstr(self, value: Any, lineariser: Any=None) -> Any:
        """Convert the given value to a VRML97 representation"""
        try:
            if not len(value):
                return '[ ]'
        except ValueError:
            # numpy arrays can't be tested for null-ity, should be a typeerror, but whatever
            pass
        linvalues = _linvalues(lineariser)
        sets = [
            linvalues['numsep'].join([str(obj) for obj in vector.ravel()])
            for vector in value
        ]
        setLength = int(100 / self.length)  # 100 is arbitrary

        # now process the string chunk representations
        if len(sets) < setLength:  # again, arbitrary
            return '[%s]' % (linvalues['subelspacer'].join(sets))
        else:  # greater than setLength elements...
            stringsets2 = []
            while sets:
                stringsets2.append(linvalues['subelspacer'].join(sets[:setLength]))
                del sets[:setLength]
            return '[%s]' % ('\n'.join(stringsets2))

    def copyValue(self, value: Any, copier: Any=None) -> Any:
        """Copy a value for copier"""
        return arrays.array(value, arrays.typeCode(value))


class _SFVec32(_SFVec):
    acceptedTypes = ('f', FLOAT_TYPE)
    targetType = FLOAT_TYPE


class _MFVec32(_MFVec):
    acceptedTypes = ('f', FLOAT_TYPE)
    targetType = FLOAT_TYPE


class _SFVec2f(_SFVec32):
    """SFVec2f field/event type base-class"""

    dimension = (2,)


class _SFVec3f(_SFVec32):
    """SFVec3f field/event type base-class"""

    dimension = (3,)


class _SFVec4f(_SFVec32):
    """SFVec4f field/event type base-class"""

    dimension = (4,)


class _SFRotation(_SFVec32):
    """SFRotation field/event type base-class"""

    dimension = (4,)


class _SFMatrix3f(_SFVec32):
    """3x3 matrix field/event type base-class"""

    dimension = (3, 3)

    def defaultDefault(self) -> Any:
        """Default default value for vectors/colours"""
        return arrays.identity(self.dimension[0], self.targetType)


class _SFMatrix4f(_SFVec32):
    """4x4 matrix field/event type base-class"""

    dimension = (4, 4)

    def defaultDefault(self) -> Any:
        """Default default value for vectors/colours"""
        return arrays.identity(self.dimension[0], self.targetType)


class _SFVec2d(_SFVec):
    """SFVec2f field/event type base-class"""

    dimension = (2,)


class _SFVec3d(_SFVec):
    """SFVec3f field/event type base-class"""

    dimension = (3,)


class _SFVec4d(_SFVec):
    """SFVec4f field/event type base-class"""

    dimension = (4,)


class _SFMatrix3d(_SFVec):
    """3x3 matrix field/event type base-class"""

    dimension = (3, 3)


class _SFMatrix4d(_SFVec):
    """4x4 matrix field/event type base-class"""

    dimension = (4, 4)


class _SFColor(_Color, _SFVec3f):
    """SFColor field/event type base-class"""

    def coerce(self, value: Any) -> Any:
        """Adds string-coercion for color data types"""
        if isinstance(value, str):
            value = csscolors.stringToColor(value)
        return super(_SFColor, self).coerce(value)

    # can't use classmethod because then super's get class instead of instance
    # coerce = classmethod( coerce )


_SFCOLOR_TOOL = _SFColor()


class _MFVec2f(_MFVec32):
    """MFVec2f field/event type base-class"""

    dimension = (2,)


class _MFVec3f(_MFVec32):
    """MFVec3f field/event type base-class"""

    dimension = (3,)


class _MFVec4f(_MFVec32):
    """MFVec4f field/event type base-class"""

    dimension = (4,)


class _MFVec2d(_MFVec):
    """MFVec2d field/event type base-class"""

    dimension = (2,)


class _MFVec3d(_MFVec):
    """MFVec3d field/event type base-class"""

    dimension = (3,)


class _MFVec4d(_MFVec):
    """MFVec4d field/event type base-class"""

    dimension = (4,)


class _MFColor(_Color, _MFVec3f):
    """MFColor field/event type base-class"""

    def coerce(self, value: Any) -> Any:
        """Adds string coercion for color data types"""
        try:
            return super(_MFColor, self).coerce(value)
        except (ValueError, TypeError) as err:
            # allow for string-based specifications...
            result: list = []
            current: list = []
            for item in value:
                if isinstance(item, str):
                    if current:
                        raise ValueError(
                            """Incorrect number of float values %r before string value %r for color number %s"""
                            % (
                                current,
                                item,
                                len(result),
                            )
                        ) from err
                    result.append(_SFCOLOR_TOOL.coerce(item))
                else:
                    current.append(item)
                    if len(current) == 3:
                        result.append(_SFCOLOR_TOOL.coerce(current))
                        current = []
            if current:
                raise ValueError(
                    """Incorrect number of float values at end of MFColor: %(current)r"""
                    % locals()
                ) from err
            return super(_MFColor, self).coerce(result)


class _MFRotation(_MFVec):
    """MFRotation field/event type base-class"""

    dimension = (4,)


class _MFMatrix3f(_MFVec32):
    """3x3 matrix-set field/event type base-class"""

    dimension = (3, 3)


class _MFMatrix4f(_MFVec32):
    """4x4 matrix-set field/event type base-class"""

    dimension = (4, 4)


class _MFMatrix3d(_MFVec):
    """3x3 matrix-set field/event type base-class"""

    dimension = (3, 3)


class _MFMatrix4d(_MFVec):
    """4x4 matrix-set field/event type base-class"""

    dimension = (4, 4)


### The concrete field and event classes (auto-generated).
class MFColor(_MFColor, field.Field):
    """MFColor Field class"""


class MFColorEvt(
    _MFColor,
    field.Event,
):
    """MFColor Event class"""

    fieldType = 'MFColor'


class SFArray(_SFArray, field.Field):
    """SFArray Field class"""


class SFArrayEvt(_SFArray, field.Event):
    """SFArray Event class"""

    fieldType = 'SFArray'


class SFArray32(_SFArray32, field.Field):
    """SFArray32 Field class"""


class SFArray32Evt(_SFArray32, field.Event):
    """SFArray32 Event class"""

    fieldType = 'SFArray32'


class MFFloat(_MFFloat, field.Field):
    """MFFloat Field class"""


class MFFloatEvt(
    _MFFloat,
    field.Event,
):
    """MFFloat Event class"""

    fieldType = 'MFFloat'


class MFFloat32(_MFFloat32, field.Field):
    """MFFloat32 Field class"""


class MFFloat32Evt(
    _MFFloat32,
    field.Event,
):
    """MFFloat32 Event class"""

    fieldType = 'MFFloat32'


class MFInt32(_MFInt32, field.Field):
    """MFInt32 Field class"""


class MFInt32Evt(
    _MFInt32,
    field.Event,
):
    """MFInt32 Event class"""

    fieldType = 'MFInt32'


class MFUInt32(_MFUInt32, field.Field):
    """MFUInt32 Field class"""


class MFUInt32Evt(
    _MFUInt32,
    field.Event,
):
    """MFUInt32 Event class"""

    fieldType = 'MFUInt32'


class MFRotation(_MFRotation, field.Field):
    """MFRotation Field class"""


class MFRotationEvt(
    _MFRotation,
    field.Event,
):
    """MFRotation Event class"""

    fieldType = 'MFRotation'


class MFString(_MFString, field.Field):
    """MFString Field class"""


class MFStringEvt(
    _MFString,
    field.Event,
):
    """MFString Event class"""

    fieldType = 'MFString'


class MFTime(_MFTime, field.Field):
    """MFTime Field class"""


class MFTimeEvt(
    _MFTime,
    field.Event,
):
    """MFTime Event class"""

    fieldType = 'MFTime'


class MFVec2f(_MFVec2f, field.Field):
    """MFVec2f Field class"""


class MFVec2fEvt(
    _MFVec2f,
    field.Event,
):
    """MFVec2f Event class"""

    fieldType = 'MFVec2f'


class MFVec2d(_MFVec2f, field.Field):
    """MFVec2d Field class"""


class MFVec2dEvt(
    _MFVec2d,
    field.Event,
):
    """MFVec2d Event class"""

    fieldType = 'MFVec2d'


class MFVec3f(_MFVec3f, field.Field):
    """MFVec3f Field class"""


class MFVec3fEvt(
    _MFVec3f,
    field.Event,
):
    """MFVec3f Event class"""

    fieldType = 'MFVec3f'


class MFVec3d(_MFVec3d, field.Field):
    """MFVec3d Field class"""


class MFVec3dEvt(
    _MFVec3d,
    field.Event,
):
    """MFVec3d Event class"""

    fieldType = 'MFVec3d'


class MFVec4f(_MFVec4f, field.Field):
    """MFVec4f Field class"""


class MFVec4fEvt(
    _MFVec4f,
    field.Event,
):
    """MFVec4f Event class"""

    fieldType = 'MFVec4f'


class MFVec4d(_MFVec4d, field.Field):
    """MFVec4d Field class"""


class MFVec4dEvt(
    _MFVec4d,
    field.Event,
):
    """MFVec4d Event class"""

    fieldType = 'MFVec4d'


class MFMatrix3f(_MFMatrix3f, field.Field):
    """MFMatrix3f Field class"""


class MFMatrix3fEvt(_MFMatrix3f, field.Event):
    """MFMatrix3f Field class"""

    fieldType = 'MFMatrix3f'


class MFMatrix3d(_MFMatrix3d, field.Field):
    """MFMatrix3d Field class"""


class MFMatrix3dEvt(_MFMatrix3d, field.Event):
    """MFMatrix3d Field class"""

    fieldType = 'MFMatrix3d'


class MFMatrix4f(_MFMatrix4f, field.Field):
    """MFMatrix4f Field class"""


class MFMatrix4fEvt(_MFMatrix4f, field.Event):
    """MFMatrix4f Field class"""

    fieldType = 'MFMatrix4f'


class MFMatrix4d(_MFMatrix4d, field.Field):
    """MFMatrix4d Field class"""


class MFMatrix4dEvt(_MFMatrix4d, field.Event):
    """MFMatrix3d Field class"""

    fieldType = 'MFMatrix4d'


class SFBool(_SFBool, field.Field):
    """SFBool Field class"""


class SFBoolEvt(
    _SFBool,
    field.Event,
):
    """SFBool Event class"""

    fieldType = 'SFBool'


class SFColor(_SFColor, field.Field):
    """SFColor Field class"""


class SFColorEvt(
    _SFColor,
    field.Event,
):
    """SFColor Event class"""

    fieldType = 'SFColor'


class SFFloat(_SFFloat, field.Field):
    """SFFloat Field class"""


class SFFloatEvt(
    _SFFloat,
    field.Event,
):
    """SFFloat Event class"""

    fieldType = 'SFFloat'


class SFImage(_SFImage, field.Field):
    """SFImage Field class"""


class SFImageEvt(
    _SFImage,
    field.Event,
):
    """SFImage Event class"""

    fieldType = 'SFImage'


class SFInt32(_SFInt32, field.Field):
    """SFInt32 Field class"""


class SFInt32Evt(
    _SFInt32,
    field.Event,
):
    """SFInt32 Event class"""

    fieldType = 'SFInt32'


class SFUInt32(_SFUInt32, field.Field):
    """SFInt32 Field class"""


class SFUInt32Evt(
    _SFUInt32,
    field.Event,
):
    """SFInt32 Event class"""

    fieldType = 'SFUInt32'


class SFRotation(_SFRotation, field.Field):
    """SFRotation Field class"""


class SFRotationEvt(
    _SFRotation,
    field.Event,
):
    """SFRotation Event class"""

    fieldType = 'SFRotation'


class SFString(_SFString, field.Field):
    """SFString Field class"""


class SFStringEvt(
    _SFString,
    field.Event,
):
    """SFString Event class"""

    fieldType = 'SFString'


class SFTime(_SFTime, field.Field):
    """SFTime Field class"""


class SFTimeEvt(
    _SFTime,
    field.Event,
):
    """SFTime Event class"""

    fieldType = 'SFTime'


class SFVec2f(_SFVec2f, field.Field):
    """SFVec2f Field class"""


class SFVec2fEvt(
    _SFVec2f,
    field.Event,
):
    """SFVec2f Event class"""

    fieldType = 'SFVec2f'


class SFVec2d(_SFVec2d, field.Field):
    """SFVec2d Field class"""


class SFVec2dEvt(
    _SFVec2d,
    field.Event,
):
    """SFVec2d Event class"""

    fieldType = 'SFVec2d'


class SFVec3f(_SFVec3f, field.Field):
    """SFVec3f Field class"""


class SFVec3fEvt(
    _SFVec3f,
    field.Event,
):
    """SFVec3f Event class"""

    fieldType = 'SFVec3f'


class SFVec3d(_SFVec3d, field.Field):
    """SFVec3f Field class"""


class SFVec3dEvt(
    _SFVec3d,
    field.Event,
):
    """SFVec3d Event class"""

    fieldType = 'SFVec3d'


class SFVec4f(_SFVec4f, field.Field):
    """SFVec4f Field class"""


class SFVec4fEvt(
    _SFVec4f,
    field.Event,
):
    """SFVec4f Event class"""

    fieldType = 'SFVec4f'


class SFVec4d(_SFVec4d, field.Field):
    """SFVec4d Field class"""


class SFVec4dEvt(
    _SFVec4d,
    field.Event,
):
    """SFVec4f Event class"""

    fieldType = 'SFVec4d'


class SFMatrix3f(_SFMatrix3f, field.Field):
    """SFMatrix3f Field class"""


class SFMatrix3fEvt(_SFMatrix3f, field.Event):
    """SFMatrix3f Field class"""

    fieldType = 'SFMatrix3f'


class SFMatrix3d(_SFMatrix3d, field.Field):
    """SFMatrix3d Field class"""


class SFMatrix3dEvt(_SFMatrix3d, field.Event):
    """SFMatrix3d Field class"""

    fieldType = 'SFMatrix3d'


class SFMatrix4f(_SFMatrix4f, field.Field):
    """SFMatrix4f Field class"""


class SFMatrix4fEvt(_SFMatrix4f, field.Event):
    """SFMatrix4f Field class"""

    fieldType = 'SFMatrix4f'


class SFMatrix4d(_SFMatrix4d, field.Field):
    """SFMatrix4d Field class"""


class SFMatrix4dEvt(_SFMatrix4d, field.Event):
    """SFMatrix3d Field class"""

    fieldType = 'SFMatrix4d'


### Now register everything
field.register(MFFloat)
field.register(MFFloat32)
field.register(SFBool)
field.register(MFColor)
field.register(MFRotation)
field.register(SFRotation)
field.register(MFInt32)
field.register(MFUInt32)
field.register(MFString)
field.register(SFImage)
field.register(SFFloat)
field.register(SFTime)
field.register(MFTime)
field.register(SFColor)
field.register(SFString)
field.register(SFInt32)
field.register(SFUInt32)
field.register(SFVec2f)
field.register(SFVec3f)
field.register(SFVec4f)
field.register(SFArray)
field.register(SFArray32)
field.register(MFVec2f)
field.register(MFVec3f)
field.register(MFVec4f)
field.register(MFMatrix3f)
field.register(MFMatrix4f)
field.register(SFVec2d)
field.register(SFVec3d)
field.register(SFVec4d)
field.register(MFVec2d)
field.register(MFVec3d)
field.register(MFVec4d)
field.register(MFMatrix3d)
field.register(MFMatrix4d)

## event classes...
field.register(MFFloatEvt)
field.register(MFFloat32Evt)
field.register(SFBoolEvt)
field.register(MFColorEvt)
field.register(MFRotationEvt)
field.register(SFRotationEvt)
field.register(MFInt32Evt)
field.register(MFUInt32Evt)
field.register(MFStringEvt)
field.register(SFImageEvt)
field.register(SFFloatEvt)
field.register(SFTimeEvt)
field.register(MFTimeEvt)
field.register(SFColorEvt)
field.register(SFStringEvt)
field.register(SFInt32Evt)
field.register(SFUInt32Evt)
field.register(SFVec2fEvt)
field.register(SFVec3fEvt)
field.register(SFVec4fEvt)
field.register(SFArrayEvt)
field.register(SFArray32Evt)
field.register(MFVec2fEvt)
field.register(MFVec3fEvt)
field.register(MFVec4fEvt)
field.register(MFMatrix3fEvt)
field.register(MFMatrix4fEvt)
field.register(SFVec2dEvt)
field.register(SFVec3dEvt)
field.register(SFVec4dEvt)
field.register(MFVec2dEvt)
field.register(MFVec3dEvt)
field.register(MFVec4dEvt)
field.register(MFMatrix3dEvt)
field.register(MFMatrix4dEvt)

if __name__ == "__main__":
    import unittest

    class ColorTest(unittest.TestCase):
        """Test simple color coercion"""

        def testMFColorString(self) -> None:
            color = MFColor("test", 1, list)
            result = color.coerce([0.2, 0.3, 0.4, 'red'])
            assert arrays.allclose(result, ((0.2, 0.3, 0.4), (1, 0, 0)))

        def testSFColorString(self) -> None:
            color = SFColor("test", 1, list)
            for value, expected in [
                ((0.2, 0.3, 0.4), (0.2, 0.3, 0.4)),
                ('red', (1, 0, 0)),
                ('#ff0000', (1, 0, 0)),
            ]:
                result = color.coerce(value)
                assert arrays.allclose(result, expected), (
                    """FAIL: color conversion for %(value)r\nExpected: %(expected)s\nGot:%(result)s"""
                    % (locals())
                )

    unittest.main()
