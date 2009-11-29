"""property sub-class providing VRML field semantics"""
from pydispatch import dispatcher, robustapply
import weakref
from vrml import protonamespace

# conditional import via package entry points
try:
	from vrml_accelerate import fieldaccel
except ImportError, err:
	fieldaccel = None

baseFieldTypes = protonamespace.ProtoNamespace({})
baseEventTypes = protonamespace.ProtoNamespace({})

### stuff used by the various field sub-types
NUMERIC_TYPES = (int,float,long)
SEQUENCE_TYPES = (tuple, list)
_NULL = []

def register( cls ):
	"""Register a new Field or Event class"""
	name = typeName(cls)
	if issubclass( cls, Event ):
		dictionary = baseEventTypes
	else:
		dictionary = baseFieldTypes
	if name in dictionary:
		print 'Warning: redefining field-type %s from %s to %s'%( name, dictionary.get(name), cls)
	dictionary[ name ] = cls
		
	
def typeName( cls ):
	"""Get the name of a field/event"""
	if hasattr( cls, 'fieldType'):
		return cls.fieldType
	else:
		return cls.__name__.split('.')[-1]

def newField( name, dataType, exposure=1, default=_NULL ):
	"""Create a new field with support for using strings to specify type

		name -- string name
		dataType -- string (or Field sub-class) specifying datatype
		exposure -- boolean (0/1) indicating whether this is an exposed field
		default -- default value for the field
	"""
	if isinstance( dataType, str ):
		dataType = baseFieldTypes[dataType]
	return dataType( name, exposure, default )
def newEvent( name, dataType, direction=1 ):
	"""Create a new event object (a specialised Field)
		name -- string name
		dataType -- 
		direction -- 0 == in, 1 == out
	"""
	if isinstance( dataType, str ):
		dataType = baseEventTypes[dataType]
	return dataType( name, direction )


class Field( property ):
	"""Property sub-class with VRML field semantics

	The field basically binds a name, a dataType, and
	a default value (with some other meta-data that isn't
	actually used by the current implementation).

	Fields are normally accessed through the protofunctions
	module, which retrieves field objects from node or
	prototype objects.

	The field offers vrml.dispatcher notification of
	changes to values (see fget, fset and fdel methods).
	Which allows code to watch for those changes, a
	facility you can see in the OpenGLContext.scenegraph.cache
	module.
	"""
	nodes = 0
	defaultDefault = None
	def __init__(
		self, name, exposure=1,
		default=_NULL,
	):
		"""Initialise the field object

		name -- string name
		exposure -- boolean (0/1) indicating whether this is an exposed field
		default -- default value for the field
		"""
		self.name = name
		self.exposure = exposure
		if default is _NULL:
			default = self.defaultDefault
		self.default = default
		property.__init__( self, self.fget, self.fset, self.fdel, repr(self))
		setattr( self, "__doc__", str(self))
	def getDefault( self, client = None ):
		"""Get the default value of this field

		if client, set client's attribute to default
		without sending a notification event.
		"""
		if hasattr(self.default, '__call__' ):
			default = self.default()
		else:
			default = self.default
		if client is not None:
			default = self.fset( client, default, notify=0)
		return default
		
	def fset( self, client, value, notify = 1 ):
		"""Set the client's value for this property

		if notify is true send a notification event.
		"""
		try:
			value = self.coerce( value )
		except ValueError, x:
			raise ValueError( """Field %s could not accept value %s (%s)"""%( self, value, x))
		except TypeError, x:
			raise ValueError( """Field %s could not accept value %s of type %s (%s)"""%( self, value, type(value), x))
		if isinstance( client, type ):
			setattr( client, self.name, value )
		else:
			client.__dict__[self.name] = value
		if notify:
			dispatcher.send( ('set',self), client, value=value)
		return value
	def fget( self, client ):#, notify=0 ):
		"""Get the client's value for this property

		if notify is true send a notification event.
		"""
		current = client.__dict__.get( self.name, _NULL )
		if current is _NULL:
			current = self.getDefault(client)
		return current
	def fdel( self, client, notify=1 ):
		"""Delete the client's value for this property

		if notify is true send a notification event.
		"""
		if isinstance( client, type ):
			delattr( client, self.name)
		else:
			if self.name in client.__dict__:
				del client.__dict__[ self.name ]
		if notify:
			dispatcher.send( ('del',self), client, field=self )
	def fhas( self, client ):
		"""Determine whether the client currently has a non-default value"""
		if isinstance( client, type ):
			return hasattr( client, self.name )
		elif client.__dict__.has_key( self.name ):
			return 1
		else:
			return 0
		
	def copy( self, client=None, copier=None ):
		"""Copy this property's value/definition for client node/proto

		if client is a prototype, copy this field definition
		for use in a new prototype.

		if client is a node, and it has a set value for this
		field, then returns self.copyValue( currentValue )

		otherwise returns _NULL, a singleton object which
		shouldn't turn up anywhere else.
		"""
		if isinstance( client, type ):
			# copy the field definition itself...
			return self.__class__(
				self.name,
				self.exposure,
				self.copyValue(self.default, copier),
			)
		elif self.fhas( client ):
			return self.copyValue( self.fget( client ), copier)
		else:
			return _NULL

	def copyValue( self, value, copier=None ):
		"""Copy a value for copier"""
		return value

	def typeName( self ):
		"""Get the typeName of this field"""
		return typeName( self.__class__ )
		
	def __str__( self ):
		"""Get a human-friendly representation of the field"""
		if self.exposure:
			exposed = "exposedField"
		else:
			exposed = "field"
		return '%s %s %s %s'%(exposed, self.typeName(), self.name, str(self.default)[:20])


	def coerce( self, value ):
		"""Coerce the given value to our type"""
		return value
	def check( self, value ):
		"Raise ValueError if isn't correct type"
		return value
	def vrmlstr( self, value, lineariser ):
		"""Convert the given value to a VRML97 representation"""
		return ""
	def fieldVrmlstr( self, lineariser ):
		"""Write the field's definition to the lineariser

		Basically this gives you a VRML97 fragment
		which can be used for creating a PROTO which
		will have the equivalent of this field available.
		"""
		if self.exposure:
			exposed = "exposedField"
		else:
			exposed = "field"
		lineariser.buffer.write(
			'%s %s %s '%(
				exposed,
				self.typeName(),
				self.name,
			)
		)
		result = self.vrmlstr(
			# coerce is necessary because the
			# default values are often not in
			# the canonical representation
			self.coerce(
				self.getDefault()
			),
			lineariser,
		)
		if result:
			lineariser.buffer.write( result )
		return
	def watch( self, node, receiver, signal = dispatcher.Any ):
		"""Make receiver receive all update events for this field+node
		
		receiver( signal, sender, value=None )
		
			signal -- ('del',self), ('set',self) etc...
			sender -- node 
			value -- new value set (for set values)
		"""
		return dispatcher.connect(
			receiver = receiver,
			sender = node,
			signal = signal,
		)


if fieldaccel:
	import new
	Field.fget = new.instancemethod(fieldaccel.simpleGet, None, Field )


class WeakField( object ):
	"""A Mix-in for fields which stores weak-references to values"""
	def fset( self, client, value, notify = 1 ):
		"""Set the client's value for this property

		if notify is true send a notification event.
		"""
		if isinstance( value, weakref.ReferenceType ):
			value = value()
		if not value:
			if not isinstance( client, type):
				self.fdel( client, notify=notify )
			return None
		value = weakref.ref( value )
		value = super( WeakField, self).fset( client, value, notify=notify )
		return value()
	def fget( self, client ):
		"""Get the client's value for this property

		if notify is true send a notification event.
		"""
		value = super( WeakField, self).fget( client )
		if not value:
			# is already default value, since refs are always non-null
			return value
		value = value()
		# value now really is the ref'd value, or None
		if value is None:
			if not isinstance( client, type):
				self.fdel( client, notify=0 )
			return None # super( WeakField, self).fget( client )
		return value
		
##
##
##class PROTOField( Field ):
##	"""Field on a prototyped node"""
##	def fset( self, client, value ):
##		"""Set the client's value for this property"""
##		value = super(PROTOField, self).fset( client, value )
##		for (node,field) in client._Node__isMaps.get(self.name,[]):
##			field.fset( node, value )
##		return value
##
##
##class IsField( Field ):
##	"""Field defined as a reference to a node + a field"""
##	def __init__( self, name, field, node=None ):
##		"""Initialise the field object
##
##		name -- string name
##		field -- pointer to the property from which we derive
##		node -- either the prototyped node or the prototype class
##		"""
##		self.field = field
##		self.node = node
##		super( IsField, self).__init__( name, field.exposure, field.default )
##	def fset( self, client, value ):
##		"""Set the outer-node's value (fail if un-instantiated)"""
##		if isinstance( self.node, type):
##			raise TypeError( """Attempted to set value %s of an un-instantiated is-mapped field %s for node %s of proto %s"""%( value, self, client, self.node ))
##		setattr( self.node, self.field.name, value )
##	def fget( self, client ):
##		"""Get the outer-node's value (default if un-instantiated)"""
##		if isinstance( self.node, type):
##			value = self.field.default
##			if callable( value):
##				value = value()
##			return value
##		return getattr( self.node, self.field.name )
##	def fdel( self, client ):
##		"""Delete the outer-node's value (fail if un-instantiated)"""
##		if isinstance( self.node, type):
##			raise TypeError( """Attempted to delete value %s of an un-instantiated is-mapped field %s for node %s of proto %s"""%( value, self, client, self.node ))
##		return delattr( self.node, self.field.name )
##		
##	def __str__( self ):
##		return """%s IS %s"""%( self.name, self.field.name )


class Event( object ):
	"""An Event-handling Port definition

	The event is currently non-functional, it's just
	here to allow VRML content to parse and be represented
	in-memory.
	"""
	def __init__( self, name, direction=1 ):
		"""Initialise the field object

		name -- string name
		direction -- 0 == in, 1 == out
		"""
		self.name = name
		self.direction = direction
	def __set__( self, client, value, notify=1 ):
		"""Set an event value"""
		method = getattr( client, 'on_%s'%(self.name,), None)
		if method is not None:
			robustapply.robustApply(
				method, value, event=self,
			)
		# now set as a normal property...
		client.__dict__[self.name] = value
		# and then send event letting world know...
		if notify:
			dispatcher.send( ('set',self), client, value=value)
	def __get__( self, client=None, cls=None ):
		"""Get an event's last value"""
		if client is None:
			return self
		try:
			return client.__dict__[self.name]
		except KeyError, err:
			raise AttributeError(
				"""Event %s doesn't have a value for %s"""%(
					self.name, client,
				)
			)
	def clone( self, name=None, direction=None ):
		"""Clone this property"""
		if name is None:
			name = self.name
		if direction is None:
			direction = self.direction
		return self.__class__( name, direction )
	def typeName( self ):
		"""Get the typeName of this field"""
		return typeName( self.__class__ )
	def __str__( self ):
		"""Get a human-friendly representation of the event"""
		if self.direction:
			exposed = "eventOut"
		else:
			exposed = "eventIn"
		return '%s %s %s'%(exposed, self.typeName(), self.name)

	def eventVrmlstr( self, lineariser ):
		"""Write the event's definition to the lineariser

		Basically this gives you a VRML97 fragment
		which can be used for creating a PROTO which
		will have the equivalent of this event available.
		"""
		if self.direction:
			exposed = "eventOut"
		else:
			exposed = "eventIn"
		base = '%s %s %s'%(
			exposed,
			self.typeName(),
			self.name,
		)
		lineariser.buffer.write( base )
		return base
	def watch( self, node, receiver, signal = dispatcher.Any ):
		"""Make receiver receive all update events for this field+node
		
		receiver( signal, sender, value=None )
		
			signal -- ('del',self), ('set',self) etc...
			sender -- node 
			value -- new value set (for set values)
		"""
		return dispatcher.connect(
			receiver = receiver,
			sender = node,
			signal = signal,
		)
