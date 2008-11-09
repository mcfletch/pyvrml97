"""Definitions of the standard VRML97 field-types

These are all of the "low-level" field-types
(i.e. not nodes) defined by VRML97.  Each has
a canonical in-memory storage format so that
code can rely on that format when dealing with
the field values.

We use Numeric Python arrays whereever possible.
"""
import operator
from vrml import protonamespace, field, csscolors, arrays

import types, sys
from types import ListType, TupleType

DOUBLE_TYPE = arrays.typeCode( arrays.array( [0],'d') )
FLOAT_TYPE = arrays.typeCode( arrays.array( [0],'f') )
INT_TYPE = arrays.typeCode( arrays.array( [0],'i') )
UINT_TYPE = arrays.typeCode( arrays.array( [0],'I') )

def _collapse(inlist, isinstance=isinstance, ltype=types.ListType, maxint= sys.maxint):
	'''
	Destructively flatten a list hierarchy to a single level. 
	Non-recursive, and (as far as I can see, doesn't have any
	glaring loopholes).
	Further speedups and obfuscations by Tim Peters :)
	'''
	try:
		# for every possible index
		for ind in xrange( maxint):
			# while that index currently holds a list
			while isinstance( inlist[ind], ltype):
				# expand that list into the index (and subsequent indicies)
				inlist[ind:ind+1] = inlist[ind]
			#ind = ind+1
	except IndexError:
		pass
	return inlist

def collapse(inlist):
	'''
	As _collapse, but works on a copy of the inlist
	'''
	return _collapse( list(inlist) )



def _linvalues( lineariser ):
	"""Get the linearisation values for a lineariser"""
	if lineariser is None:
		from vrml.vrml97 import linearise
		return linearise.defaults
	else:
		return lineariser.linvalues

def SFString_vrmlstr( value, lineariser=None):
	"""Convert the given value to a VRML97 representation"""
	return '"%s"'%(
		'\\"'.join(
			'\\\\'.join(
				value.split('\\')
			).split('"')
		)
	)
def MFString_vrmlstr( value, lineariser=None):
	"""Convert the given value to a VRML97 representation"""
	if not value:
		return "[ ]"
	anyobject = [ SFString_vrmlstr( v, lineariser) for v in value ]
	linvalues = _linvalues( lineariser)
	length = reduce( operator.add, map(len, anyobject))
	if length > 60:
		sep = '%(subelspacer)s\n%(curindent)s%(indent)s'%linvalues
		if len(anyobject) > 1:
			result = ['[']
		else:
			result = []
		for element in anyobject:
			if result:
				result.append( sep )
			result.append( element )
		if len(anyobject) > 1:
			result.append('\n%(curindent)s]\n'%linvalues )
		return "".join( result)
	elif len(anyobject) > 1:
		return '[ %s ]'%linvalues['subelspacer'].join( anyobject)
	else:
		return linvalues['subelspacer'].join( anyobject )
def SFFloat_vrmlstr( value, lineariser=None):
	"""Convert floats to (compact) VRML97 representation"""
	rpr = str( value )
	if rpr == '0.0':
		return '0'
	elif rpr[:2] == '0.':
		return rpr[1:]
	elif rpr[:3] == '-0.':
		return '-'+rpr[2:]
	elif rpr[-2:] == '.0':
		return rpr[:-2]
	else:
		return rpr
def MFSimple_vrmlstr( value, lineariser=None):
	"""Convert value to a VRML97 representation"""
	linvalues = _linvalues( lineariser)
	stringreps = map(str, value)
	stringsets = []
	setLength = 100 # 100 is arbitrary
	while stringreps:
		stringsets.append(
			linvalues['numsep'].join(stringreps[:setLength])
		)
		del stringreps[:setLength]
	return '[ %s ]'%('\n'.join(stringsets))


class _SFString( object):
	"""SFString field/event type base-class"""
	defaultDefault = ""
	def coerce( self, value ):
		"""Coerce the given value to our type
		Allowable types:
			simple string -> unchanged
			unicode string -> utf-8 encoded
			
			sequence of length == 1 where first element is a string -> returns first element
			sequence of length > 1 where all elements are strings -> returns string.join( value, '')
		"""
		if isinstance( value, unicode ):
			return value.encode( 'utf-8')
		elif isinstance( value, field.SEQUENCE_TYPES):
			if value and len(value) == 1:
				value = value[0]
			elif not value:
				value = ""
			else:
				value = "".join( value )
		if not isinstance( value, str ):
			value = str(value)
		return value
	def check( self, value ):
		"Raise ValueError if isn't correct type"
		if not isinstance( value, str):
			return 0
		return 1
	coerce = classmethod( coerce )
	check = classmethod( check )
	vrmlstr = staticmethod( SFString_vrmlstr )

class _MFString( object ):
	"""MFString field/event type base-class"""
	defaultDefault = list
	def coerce( self, value ):
		"""Coerce the given value to our type
		Allowable types:
			simple string -> wrapped in a list
			sequence of strings (of any length) -> equivalent list returned
		"""
		if isinstance( value, (str,unicode)):
			value = [value]
		try:
			return [ SFString.coerce( item ) for item in value]
		except ValueError, error:
			raise ValueError( """Attempted to set value %r for an %s field which is not compatible: %s"""%( value, self.typeName(),  error))
	def check( self, value ):
		"Raise ValueError if isn't correct type"
		if isinstance( value, list):
			if not filter( None, [isinstance(item,(str,unicode)) for item in value]):
				return 1
		return 0
	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return value[:]
	vrmlstr = staticmethod( MFString_vrmlstr )

class _SFBool( object ):
	"""SFBool field/event type base-class"""
	defaultDefault = 0
	def coerce( self, value ):
		"""Coerce the given value to our type
		Allowable types:
			any object with true/false protocol
		"""
		if value:
			return 1
		else:
			return 0
	def check( self, value ):
		"""Check that the given value is of exactly expected type"""
		if value in (0,1):
			return 1
		return 0
	def vrmlstr( self, value, lineariser=None):
		"""Convert the given value to a VRML97 representation"""
		if value:
			return 'TRUE'
		else:
			return 'FALSE'


class _SFInt32( object ):
	"""SFInt32 field/event type base-class"""
	defaultDefault = 0
	def coerce( self, value ):
		"""Coerce the given value to our type
		Allowable types:
			any object with true/false protocol
		"""
		try:
			return int( value )
		except ValueError:
			raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.typeName(), repr(value) ))
	def check( self, value ):
		"""Check that the given value is of exactly expected type"""
		if isinstance( value, int):
			return 1
		return 0

	def vrmlstr( self, value, lineariser=None):
		"""Convert the given value to a VRML97 representation"""
		try:
			return str( int(value) )
		except OverflowError:
			base = str( value )
			if base and base[-1] in ('l','L'):
				base = base[:-1]
			return base + ' # Overly long number\n'



class _SFFloat( object ):
	"""SFFloat field/event type base-class"""
	defaultDefault = 0.0
	def coerce( self, value ):
		"""Coerce the given value to our type
		Allowable types:
			any object with true/false protocol
		"""
		try:
			return float( value )
		except ValueError:
			raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.typeName(), repr(value) ))
	def check( self, value ):
		"""Check that value is of precisely the expected data type"""
		if isinstance( value, float):
			return 1
		return 0
	vrmlstr = staticmethod( SFFloat_vrmlstr )


class _SFTime( _SFFloat ):
	"""SFTime field/event type base-class"""
	defaultDefault = 0.0

	
class _MFInt32 ( object ):
	"""MFInt32 field/event type base-class

	Stored as a flat Numeric-python array
	"""
	defaultDefault = list
	arrayDataType = 'i'
	acceptedTypes = ('i',INT_TYPE)
	def coerce( self, value ):
		"""Base coercion mechanism for multiple-value integer fields"""
		if isinstance(value, field.NUMERIC_TYPES):
			return arrays.array([int(value)],self.arrayDataType)
		elif isinstance( value, arrays.ArrayType ):
			if arrays.typeCode(value) not in self.acceptedTypes:
				value = value.astype( self.arrayDataType )
			return arrays.contiguous( arrays.ravel(value) )
		elif isinstance( value, field.SEQUENCE_TYPES):
			return arrays.array(
				map( int, collapse( value) ),
				self.arrayDataType,
			)
		elif not value:
			return arrays.array([],self.arrayDataType)
		raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.typeName(), repr(value) ))
	vrmlstr = staticmethod(MFSimple_vrmlstr)
	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return arrays.array(value, arrays.typeCode(value) )

class _MFUInt32( _MFInt32 ):
	"""Unsigned integer version of MFInt32 (mostly for indices)"""
	defaultDefault = list
	arrayDataType = 'I'
	acceptedTypes = ('I',UINT_TYPE)

class _SFImage( _MFInt32 ):
	"""SFImage field/event type base-class

	SFImage = MFInt32, should do something more
	intelligent, such as auto-compiling those to
	mip-mapped images, or at least storing them
	efficiently.
	"""
	defaultDefault = list
	arrayDataType = 'I'
	acceptedTypes = ('I',UINT_TYPE)
	
class _MFFloat( object ):
	"""MFFloat field/event type base-class

	Stored as a flat Numeric-python array
	"""
	defaultDefault = list
	def coerce( self, value ):
		"""Base coercion mechanism for floating point field types"""
		if isinstance(value, field.NUMERIC_TYPES):
			return arrays.array([float(value)],'d')
		elif isinstance( value, arrays.ArrayType ):
			if arrays.typeCode(value) not in ('d',FLOAT_TYPE):
				value = value.astype( 'd')
			return arrays.contiguous( arrays.ravel(value) )
		elif isinstance( value, field.SEQUENCE_TYPES):
			return arrays.array(
				map( float, collapse( value) ),
				'd',
			)
		elif not value:
			return arrays.array([],'d')
		raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.typeName(), repr(value) ))
	vrmlstr = staticmethod(MFSimple_vrmlstr)
	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return arrays.array(value, arrays.typeCode(value) )

class _MFTime( _MFFloat ):
	"""MFTime field/event type base-class

	Stored as a flat Numeric-python array
	"""

class _SFVec( object ):
	"""SFVecXX field/event type base-class
	
	Stored as a Numeric-python double array of self.length
	"""
	length = 3
	def defaultDefault( self ):
		"""Default default value for vectors/colours"""
		return [0]*self.length
	def coerce( self, value ):
		"""Base coercion mechanism for vector-like field types"""
		if isinstance(value, (int,long,float)):
			value = arrays.array([float(value)]*self.length,'d')
		elif isinstance( value, arrays.ArrayType ):
			if arrays.typeCode(value) not in ( 'd', DOUBLE_TYPE ):
				value = value.astype( 'd')
			value = arrays.ravel(value)
		elif isinstance( value, field.SEQUENCE_TYPES):
			value = arrays.array(
				map( float, collapse( value) ),
				'd',
			)
		else:
			try:
				value = arrays.asarray( value, 'd' )
			except Exception:
				raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.typeName(), repr(value) ))
		if len(value) != self.length:
			raise ValueError(
				"""%s value of incorrect length (is %s, should be %s)"""%(
					self.__class__.__name__,
					len(value),
					self.length,
				)
			)
		value = arrays.contiguous( value )
		return value
	def vrmlstr( self, value, lineariser=None):
		"""Convert the given value to a VRML97 representation"""
		return _linvalues(lineariser)['numsep'].join(
			[ SFFloat_vrmlstr( obj, lineariser) for obj in value]
		)
	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return arrays.array(value, arrays.typeCode(value) )

class _Color( object ):
	"""Mix-in for colour-value clamping and string coercion"""
	def coerce(self,  value):
		"""Adds clipping of values to 0.0 through 1.0 range"""
		value = super( _Color, self ).coerce( value )
		value = arrays.clip( value, 0.0, 1.0 )
		return value
	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return arrays.array(value, arrays.typeCode(value) )

class _MFVec( object ):
	"""MFVecXX field/event type base-class

	Stored as x * self.length Numeric Python double array
	"""
	defaultDefault = list
	def coerce( self, value ):
		"""Base coercion mechanism for vector-like fields"""
		if isinstance( value, arrays.ArrayType ):
			if arrays.typeCode(value) not in ('d',DOUBLE_TYPE):
				value = value.astype( 'd')
			value = arrays.reshape(value, (-1,self.length))
		elif isinstance( value, field.SEQUENCE_TYPES):
			try:
				value = arrays.reshape(arrays.array( value, 'd'), (-1,self.length))
			except ValueError:
				value = arrays.reshape(
					arrays.array(
						map( float, collapse( value) ),
						'd',
					),
					(-1,self.length)
				)
		else:
			try:
				value = arrays.reshape(arrays.asarray( value, 'd' ), (-1,self.length))
			except Exception:
				raise ValueError( """Attempted to set value for an %s field which is not compatible: %s"""%( self.typeName(), repr(value) ))
		value = arrays.contiguous( value )
		return value
	def check( self, value ):
		"""Check that the given value is of exactly the expected type"""
		if isinstance( value, arrays.ArrayType ):
			if arrays.typeCode(value) not in ( 'd', DOUBLE_TYPE ):
				s = arrays.shape(value)
				if len(s) ==2 and s[-1] == self.length:
					return 1
		return 0
	def vrmlstr( self, value, lineariser=None):
		"""Convert the given value to a VRML97 representation"""
		try:
			if not value:
				return '[ ]'
		except ValueError, err:
			# numpy arrays can't be tested for null-ity, should be a typeerror, but whatever
			pass
		linvalues = _linvalues( lineariser )
		sets = [
			linvalues['numsep'].join(
				map(str, vector)
			)
			for vector in value
		]
		setLength = 100/self.length # 100 is arbitrary
		
		# now process the string chunk representations
		if len(sets) < setLength: # again, arbitrary
			return '[%s]'%(linvalues['subelspacer'].join(sets))
		else: # greater than setLength elements...
			stringsets2 = []
			while sets:
				stringsets2.append(linvalues['subelspacer'].join(sets[:setLength]))
				del sets[:setLength]
			return '[%s]'%('\n'.join(stringsets2))
	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return arrays.array(value, arrays.typeCode(value) )


class _SFVec2f( _SFVec ):
	"""SFVec2f field/event type base-class"""
	length = 2
class _SFVec3f( _SFVec ):
	"""SFVec3f field/event type base-class"""
	length = 3
class _SFVec4f( _SFVec ):
	"""SFVec4f field/event type base-class"""
	length = 4
class _SFRotation( _SFVec ):
	"""SFRotation field/event type base-class"""
	length = 4

class _SFColor( _Color, _SFVec3f ):
	"""SFColor field/event type base-class"""
	def coerce(self,  value):
		"""Adds string-coercion for color data types"""
		if isinstance( value, (str,unicode)):
			value = csscolors.stringToColor( value )
		return super(_SFColor,self).coerce(value)
	# can't use classmethod because then super's get class instead of instance
	#coerce = classmethod( coerce )
_SFCOLOR_TOOL = _SFColor()
class _MFVec2f( _MFVec ):
	"""MFVec2f field/event type base-class"""
	length = 2
class _MFVec3f( _MFVec ):
	"""MFVec3f field/event type base-class"""
	length = 3
class _MFVec4f( _MFVec ):
	"""MFVec4f field/event type base-class"""
	length = 4
class _MFColor( _Color, _MFVec3f ):
	"""MFColor field/event type base-class"""
	def coerce( self, value ):
		"""Adds string coercion for color data types"""
		try:
			return super(_MFColor,self).coerce( value )
		except (ValueError, TypeError), err:
			# allow for string-based specifications...
			result = []
			current = []
			for item in value:
				if isinstance( item, (str,unicode)):
					if current:
						raise ValueError( """Incorrect number of float values %r before string value %r for color number %s"""%(
							current, item,len(result),
						))
					result.append( _SFCOLOR_TOOL.coerce( item ))
				else:
					current.append( item )
					if len(current) == 3:
						result.append( _SFCOLOR_TOOL.coerce( current ))
						current = []
			if current:
				raise ValueError( """Incorrect number of float values at end of MFColor: %(current)r"""%locals())
			return super(_MFColor,self).coerce( result )
		
class _MFRotation( _MFVec ):
	"""MFRotation field/event type base-class"""
	length = 4

### The concrete field and event classes (auto-generated).
class MFColor( _MFColor, field.Field ):
	"""MFColor Field class"""
class MFColorEvt( _MFColor, field.Event, ):
	"""MFColor Event class"""
	fieldType = 'MFColor'

class MFFloat( _MFFloat, field.Field ):
	"""MFFloat Field class"""
class MFFloatEvt( _MFFloat, field.Event, ):
	"""MFFloat Event class"""
	fieldType = 'MFFloat'

class MFInt32( _MFInt32, field.Field ):
	"""MFInt32 Field class"""
class MFInt32Evt( _MFInt32, field.Event, ):
	"""MFInt32 Event class"""
	fieldType = 'MFInt32'

class MFUInt32( _MFUInt32, field.Field ):
	"""MFUInt32 Field class"""
class MFUInt32Evt( _MFUInt32, field.Event, ):
	"""MFUInt32 Event class"""
	fieldType = 'MFUInt32'

class MFRotation( _MFRotation, field.Field ):
	"""MFRotation Field class"""
class MFRotationEvt( _MFRotation, field.Event, ):
	"""MFRotation Event class"""
	fieldType = 'MFRotation'

class MFString( _MFString, field.Field ):
	"""MFString Field class"""
class MFStringEvt( _MFString, field.Event, ):
	"""MFString Event class"""
	fieldType = 'MFString'

class MFTime( _MFTime, field.Field ):
	"""MFTime Field class"""
class MFTimeEvt( _MFTime, field.Event, ):
	"""MFTime Event class"""
	fieldType = 'MFTime'

class MFVec2f( _MFVec2f, field.Field ):
	"""MFVec2f Field class"""
class MFVec2fEvt( _MFVec2f, field.Event, ):
	"""MFVec2f Event class"""
	fieldType = 'MFVec2f'

class MFVec3f( _MFVec3f, field.Field ):
	"""MFVec3f Field class"""
class MFVec3fEvt( _MFVec3f, field.Event, ):
	"""MFVec3f Event class"""
	fieldType = 'MFVec3f'

class MFVec4f( _MFVec4f, field.Field ):
	"""MFVec4f Field class"""
class MFVec4fEvt( _MFVec4f, field.Event, ):
	"""MFVec4f Event class"""
	fieldType = 'MFVec4f'

class SFBool( _SFBool, field.Field ):
	"""SFBool Field class"""
class SFBoolEvt( _SFBool, field.Event, ):
	"""SFBool Event class"""
	fieldType = 'SFBool'

class SFColor( _SFColor, field.Field ):
	"""SFColor Field class"""
class SFColorEvt( _SFColor, field.Event, ):
	"""SFColor Event class"""
	fieldType = 'SFColor'

class SFFloat( _SFFloat, field.Field ):
	"""SFFloat Field class"""
class SFFloatEvt( _SFFloat, field.Event, ):
	"""SFFloat Event class"""
	fieldType = 'SFFloat'

class SFImage( _SFImage, field.Field ):
	"""SFImage Field class"""
class SFImageEvt( _SFImage, field.Event, ):
	"""SFImage Event class"""
	fieldType = 'SFImage'

class SFInt32( _SFInt32, field.Field ):
	"""SFInt32 Field class"""
class SFInt32Evt( _SFInt32, field.Event, ):
	"""SFInt32 Event class"""
	fieldType = 'SFInt32'

class SFRotation( _SFRotation, field.Field ):
	"""SFRotation Field class"""
class SFRotationEvt( _SFRotation, field.Event, ):
	"""SFRotation Event class"""
	fieldType = 'SFRotation'

class SFString( _SFString, field.Field ):
	"""SFString Field class"""
class SFStringEvt( _SFString, field.Event, ):
	"""SFString Event class"""
	fieldType = 'SFString'

class SFTime( _SFTime, field.Field ):
	"""SFTime Field class"""
class SFTimeEvt( _SFTime, field.Event, ):
	"""SFTime Event class"""
	fieldType = 'SFTime'

class SFVec2f( _SFVec2f, field.Field ):
	"""SFVec2f Field class"""
class SFVec2fEvt( _SFVec2f, field.Event, ):
	"""SFVec2f Event class"""
	fieldType = 'SFVec2f'

class SFVec3f( _SFVec3f, field.Field ):
	"""SFVec3f Field class"""
class SFVec3fEvt( _SFVec3f, field.Event, ):
	"""SFVec3f Event class"""
	fieldType = 'SFVec3f'

class SFVec4f( _SFVec4f, field.Field ):
	"""SFVec4f Field class"""
class SFVec4fEvt( _SFVec4f, field.Event, ):
	"""SFVec4f Event class"""
	fieldType = 'SFVec4f'

### Now register everything
field.register( MFFloat )
field.register( SFBool )
field.register( MFColor )
field.register( MFRotation )
field.register( SFRotation )
field.register( MFInt32 )
field.register( MFUInt32 )
field.register( MFString )
field.register( SFImage )
field.register( SFFloat )
field.register( SFTime )
field.register( MFTime )
field.register( SFColor )
field.register( SFString )
field.register( SFInt32 )
field.register( SFVec2f )
field.register( SFVec3f )
field.register( SFVec4f )
field.register( MFVec2f )
field.register( MFVec3f )
field.register( MFVec4f )

## event classes...
field.register( MFFloatEvt )
field.register( SFBoolEvt )
field.register( MFColorEvt )
field.register( MFRotationEvt )
field.register( SFRotationEvt )
field.register( MFInt32Evt )
field.register( MFUInt32Evt )
field.register( MFStringEvt )
field.register( SFImageEvt )
field.register( SFFloatEvt )
field.register( SFTimeEvt )
field.register( MFTimeEvt )
field.register( SFColorEvt )
field.register( SFStringEvt )
field.register( SFInt32Evt )
field.register( SFVec2fEvt )
field.register( SFVec3fEvt )
field.register( SFVec4fEvt )
field.register( MFVec2fEvt )
field.register( MFVec3fEvt )
field.register( MFVec4fEvt )

if __name__ == "__main__":
	import unittest
	class ColorTest (unittest.TestCase):
		"""Test simple color coercion"""
		def testMFColorString (self):
			color = MFColor( "test", 1, list)
			result = color.coerce( [.2,.3,.4,'red'] )
			assert arrays.allclose( result, ((.2,.3,.4),(1,0,0)))
		def testSFColorString( self):
			color = SFColor( "test", 1, list)
			for value,expected in [
				((.2,.3,.4),(.2,.3,.4)),
				('red', (1,0,0)),
				('#ff0000',(1,0,0)),
			]:
				result = color.coerce( value )
				assert arrays.allclose( result,expected), """FAIL: color conversion for %(value)r\nExpected: %(expected)s\nGot:%(result)s"""%(locals())
	unittest.main ()
	
