"""Field values as text, in the X3D XML encoding (ISO/IEC 19776-1, 5.3)

An XML attribute holds a field's value as text: numbers separated by
whitespace or commas, booleans as ``true``/``false``, an MFString as
double-quoted strings with ``\\"`` and ``\\\\`` escapes. `decode` reads such
text into a value the field of that type coerces without further parsing
(numbers arrive as flat NumPy arrays), and `encode` writes a field's value as
text that `decode` reads back to the same value.

The ClassicVRML encoding has its own tokens and is read by its grammar; the
JSON encoding carries typed values and needs no text codec.
"""

import math
import re
from collections.abc import Callable, Iterable
from typing import Any

import numpy as np

#: The NumPy type each numeric field type's text is read into.
FLOAT32_TYPES = frozenset((
    'SFVec2f', 'SFVec3f', 'SFVec4f', 'SFColor', 'SFColorRGBA', 'SFRotation',
    'SFMatrix3f', 'SFMatrix4f', 'SFQuaternion',
    'MFVec2f', 'MFVec3f', 'MFVec4f', 'MFColor', 'MFColorRGBA', 'MFRotation',
    'MFMatrix3f', 'MFMatrix4f', 'MFQuaternion',
))
FLOAT64_TYPES = frozenset((
    'MFFloat', 'MFDouble', 'MFTime',
    'SFVec2d', 'SFVec3d', 'SFVec4d', 'SFMatrix3d', 'SFMatrix4d',
    'MFVec2d', 'MFVec3d', 'MFVec4d', 'MFMatrix3d', 'MFMatrix4d',
))
INTEGER_LIST_TYPES = frozenset(('MFInt32', 'SFImage', 'MFImage'))
SCALAR_FLOAT_TYPES = frozenset(('SFFloat', 'SFDouble', 'SFTime'))

#: How many numbers make one value of each vector type; a list writes its
#: values separated by commas.
TUPLE_SIZE = {
    'SFVec2f': 2, 'SFVec2d': 2, 'MFVec2f': 2, 'MFVec2d': 2,
    'SFVec3f': 3, 'SFVec3d': 3, 'MFVec3f': 3, 'MFVec3d': 3,
    'SFColor': 3, 'MFColor': 3,
    'SFVec4f': 4, 'SFVec4d': 4, 'MFVec4f': 4, 'MFVec4d': 4,
    'SFColorRGBA': 4, 'MFColorRGBA': 4, 'SFRotation': 4, 'MFRotation': 4,
    'SFQuaternion': 4, 'MFQuaternion': 4,
    'SFMatrix3f': 9, 'SFMatrix3d': 9, 'MFMatrix3f': 9, 'MFMatrix3d': 9,
    'SFMatrix4f': 16, 'SFMatrix4d': 16, 'MFMatrix4f': 16, 'MFMatrix4d': 16,
}

_BOOLEANS = {'true': True, 'false': False}
#: One double-quoted string, with its escapes; or the separators between.
_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"|([\s,]+)', re.DOTALL)
_ESCAPE = re.compile(r'\\(.)', re.DOTALL)


def _tokens(text: str) -> "list[str]":
    """The whitespace- and comma-separated tokens of `text`"""
    return text.replace(',', ' ').split()


def _integer(token: str) -> int:
    """An integer written in decimal, hexadecimal or with an exponent"""
    try:
        return int(token)
    except ValueError:
        pass
    lowered = token.lower()
    if lowered.lstrip('+-').startswith('0x'):
        return int(lowered, 16)
    number = float(token)
    if not number.is_integer():
        raise ValueError('%r is not an integer' % (token,))
    return int(number)


def _integers(text: str) -> Any:
    tokens = _tokens(text)
    try:
        return np.array(tokens, dtype=np.int64)
    except (ValueError, OverflowError):
        return np.array([_integer(token) for token in tokens], dtype=np.int64)


def _floats(dtype: Any) -> "Callable[[str], Any]":
    def decode(text: str) -> Any:
        return np.array(_tokens(text), dtype=dtype)
    return decode


def _boolean(text: str) -> bool:
    try:
        return _BOOLEANS[text.strip().lower()]
    except KeyError:
        raise ValueError('%r is not true or false' % (text,)) from None


def _booleans(text: str) -> "list[bool]":
    return [_boolean(token) for token in _tokens(text)]


def _strings(text: str) -> "list[str]":
    """The strings of an MFString attribute

    Content often writes a single string without quotes (a `url` of one
    file); that is read as one string. `is_quoted` says which it was, for a
    reader that reports it.
    """
    stripped = text.strip()
    if not stripped:
        return []
    if not stripped.startswith('"'):
        return [stripped]
    result = []
    position = 0
    while position < len(text):
        match = _QUOTED.match(text, position)
        if match is None:
            raise ValueError('Malformed MFString value at %s: %r'
                             % (position, text[position:position + 30]))
        if match.group(1) is not None:
            result.append(_ESCAPE.sub(r'\1', match.group(1)))
        position = match.end()
    return result


def is_quoted(text: str) -> bool:
    """Whether MFString text is written as quoted strings, as it should be"""
    stripped = text.strip()
    return not stripped or stripped.startswith('"')


def _node(text: str) -> None:
    if text.strip() != 'NULL':
        raise ValueError('A node field has no text form but NULL: %r' % (text,))
    return None


def _scalar(converter: "Callable[[str], Any]") -> "Callable[[str], Any]":
    def decode(text: str) -> Any:
        return converter(text.strip())
    return decode


DECODERS: "dict[str, Callable[[str], Any]]" = {
    'SFBool': _boolean,
    'MFBool': _booleans,
    'SFInt32': _scalar(_integer),
    'SFString': str,
    'MFString': _strings,
    'SFNode': _node,
    'MFNode': _node,
}
DECODERS.update({name: _scalar(float) for name in SCALAR_FLOAT_TYPES})
DECODERS.update({name: _integers for name in INTEGER_LIST_TYPES})
DECODERS.update({name: _floats(np.float32) for name in FLOAT32_TYPES})
DECODERS.update({name: _floats(np.float64) for name in FLOAT64_TYPES})


def decode(type_name: str, text: str) -> Any:
    """The value `text` gives a field of type `type_name`

    Raises KeyError for a type with no text form, ValueError for text that
    is not a value of the type.
    """
    return DECODERS[type_name](text)


def number_text(value: Any) -> str:
    """The shortest text that reads back as `value` at its own precision"""
    if not math.isfinite(value):
        raise ValueError('X3D has no text form for %r' % (value,))
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return str(int(value))
    if not isinstance(value, np.floating):
        value = np.float64(value)
    # Positional below 1e16: the schema's patterns for ranged types allow an
    # exponent only on a mantissa in [0, 1].
    if abs(float(value)) < 1e16:
        return np.format_float_positional(value, unique=True, trim='-')
    return np.format_float_scientific(value, unique=True, trim='-')


def _numbers(values: Iterable[Any]) -> str:
    if isinstance(values, np.ndarray):
        values = values.ravel()
    return ' '.join([number_text(value) for value in values])


def _vectors(size: int) -> "Callable[[Any], str]":
    def encode(value: Any) -> str:
        flat = np.asarray(value).ravel()
        return ', '.join(
            _numbers(flat[start:start + size]) for start in range(0, len(flat), size)
        )
    return encode


def _quote(text: str) -> str:
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


def _image(value: Any) -> str:
    return ' '.join(str(int(item)) for item in value)


def _null(_value: Any) -> str:
    return 'NULL'


ENCODERS: "dict[str, Callable[[Any], str]]" = {
    'SFBool': lambda value: 'true' if value else 'false',
    'MFBool': lambda value: ' '.join('true' if item else 'false' for item in value),
    'SFInt32': lambda value: str(int(value)),
    'MFInt32': _numbers,
    'SFString': str,
    'MFString': lambda value: ' '.join(_quote(item) for item in value),
    'SFImage': _image,
    'MFImage': lambda value: ', '.join(_image(image) for image in value),
    'SFNode': _null,
    'MFNode': _null,
}
ENCODERS.update({name: number_text for name in SCALAR_FLOAT_TYPES})
ENCODERS.update({name: _numbers for name in ('MFFloat', 'MFDouble', 'MFTime')})
ENCODERS.update({
    name: _vectors(size) if name.startswith('MF') else _numbers
    for name, size in TUPLE_SIZE.items()
})


def encode(type_name: str, value: Any) -> str:
    """`value`, of a field of type `type_name`, as XML attribute text

    Raises KeyError for an unknown type and ValueError for a number X3D has
    no text form for (infinities and NaN).
    """
    return ENCODERS[type_name](value)


def same(a: Any, b: Any) -> bool:
    """True if two field values are exactly equal"""
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        a, b = np.asarray(a), np.asarray(b)
        return a.shape == b.shape and bool(np.array_equal(a, b))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    try:
        return bool(a == b)
    except ValueError:
        return False
