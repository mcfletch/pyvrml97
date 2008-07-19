"""Abstraction point allowing use with numpy or Numeric

Chooses numpy if available because when it's installed
Numeric tends to be a bit flaky...
"""
try:
	from numpy import *
except ImportError, err:
	from Numeric import *
	def typeCode( a ):
		"""Retrieve the typecode for the given array"""
		return a.typecode()
	def any( a ):
		for x in a:
			if x:
				return True 
		return False
	try:
		from vrml import tmatrixaccelnumeric as tmatrixaccel
	except ImportError, err:
		tmatrixaccel = None
	try:
		from vrml import frustcullaccelnumeric as frustcullaccel
	except ImportError, err:
		frustcullaccel = None
else:
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
	try:
		from vrml import tmatrixaccelnumpy as tmatrixaccel
	except ImportError, err:
		tmatrixaccel = None
	try:
		from vrml import frustcullaccelnumpy as frustcullaccel
	except ImportError, err:
		frustcullaccel = None
	del a
	
def safeCompare( first, second ):
	"""Watch out for pointless numpy truth-value checks"""
	try:
		return bool(first == second )
	except ValueError, err:
		return bool( any( first == second ) )

	
def contiguous( a ):
	"""Force to a contiguous array"""
	return array( a, typeCode(a) )
	