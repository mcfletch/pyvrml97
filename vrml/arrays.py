"""Abstraction point allowing use with numpy or Numeric

Chooses numpy if available because when it's installed
Numeric tends to be a bit flaky...
"""
from numpy import *
try:
    from vrml_accelerate import tmatrixaccel
    from vrml_accelerate import frustcullaccel
except ImportError, err:
    tmatrixaccel = frustcullaccel = None
# why did this get taken out?  Is divide now safe?
amin = amin 
amax = amax
divide_safe = divide 
# Now deal with differing numpy APIs...
a = array([1,2,3],'i')
ArrayType = ndarray # alias removed in later versions
# Take's API changed from Numeric, we've updated to 
# always provide axis now...
if hasattr( a, '__array_typestr__' ):
    def typeCode( a ):
        """Retrieve the typecode for the given array
        
        Depending on whether you access the classic or new API
        you have different access methods, so we have to use
        the typecode() method if __array_typestr__ isn't there.
        """
        try:
            return a.__array_typestr__
        except AttributeError, err:
            return a.typecode()
else:
    def typeCode( a ):
        """Retrieve the typecode for the given array
        
        Depending on whether you access the classic or new API
        you have different access methods, so we have to use
        the typecode() method if .dtype.char isn't there.
        """
        try:
            return a.dtype.char
        except AttributeError, err:
            return a.typecode()
del a
implementation_name = 'numpy'
try:
    # PyVRML97 is from before numpy printed errors, we explicitly do not care 
    # about the divide-by-zero, which commonly happens in mesh data processing
    # TODO: likely should rework the mesh processing to check manually and remove 
    # this sledge-hammer approach
    seterr(all='ignore')
except Exception, err:
    pass
    
def safeCompare( first, second ):
    """Watch out for pointless numpy truth-value checks"""
    try:
        return bool(first == second )
    except ValueError, err:
        return bool( any( first == second ) )

def contiguous( a ):
    """Force to a contiguous array"""
    return array( a, typeCode(a) )
