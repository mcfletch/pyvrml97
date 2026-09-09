"""8-bit string definitions for Python 2/3 compatibility

Defines the following which allow for dealing with Python 3 breakages:

    STR_IS_BYTES
    STR_IS_UNICODE

        Easily checked booleans for type identities

    _NULL_8_BYTE

        An 8-bit byte with NULL (0) value

    as_8_bit( x, encoding='utf-8')

        Returns the value as the 8-bit version

    unicode -- always pointing to the unicode type
    bytes -- always pointing to the 8-bit bytes type
"""
from typing import Tuple
import sys

_NULL_8_BYTE = b'\000'
# The Python 2 branch that stood here referenced `unicode` and `long`,
# which raise NameError on every interpreter this package supports, so
# only what followed the `except` ever ran.
STR_IS_BYTES = False
STR_IS_UNICODE = True
unicode = str
bytes = bytes
long = int
integer_types: Tuple[type, ...] = (int,)
def as_8_bit( x, encoding='utf-8' ):
    if isinstance( x,unicode ):
        return x.encode(encoding)
    elif isinstance( x, bytes ):
        # Note: this can create an 8-bit string that is *not* in encoding,
        # but that is potentially exactly what we wanted, as these can
        # be arbitrary byte-streams being passed to C functions
        return x
    return str(x).encode( encoding )
def as_str( x, encoding='utf-8'):
    """Produce a native string (i.e. different on python 2 and 3)"""
    if isinstance(x,unicode):
        return x
    elif isinstance(x,bytes):
        return x.decode(encoding)
    else:
        return str(x)

maxsize = sys.maxsize

def as_unicode(x,encoding='utf-8'):
    """Ensure is a unicode object given default encoding"""
    if isinstance(x,unicode):
        return x
    elif isinstance(x,bytes):
        try:
            return x.decode(encoding)
        except UnicodeDecodeError as err:
            return x.decode('latin-1')
    else:
        return unicode(x)

