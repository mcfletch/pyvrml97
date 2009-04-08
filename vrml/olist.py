"""Observable list class"""
from pydispatch.dispatcher import send
class OList( list ):
	"""List sub-class which can generate pydispatch events on changes"""
	def append( self, value ):
		"""Append a value and send a message"""
		super( OList,self ).append( value )
		send( 'new', self, value=value)
		return value 
	def insert( self, index, value ):
		"""Insert a new item at index"""
		super( OList,self ).insert( index, value )
		send( 'new', self, value=value)
		return value 
	def pop( self, index=None ):
		"""Pop a single item out of the list"""
		if index is None:
			index = len(self)-1
		value = super( OList,self ).pop( index )
		send( 'del', self, value = value )
		return value
	def remove( self, item ):
		"""Remove this instance from the list"""
		super(OList,self).remove( item )
		send( 'del', self, value = item )
		return item
	def __setitem__( self, index, value ):
		"""Set a value and send a message"""
		send( 'del', self, value=self[index] )
		super( OList,self ).__setitem__( index, value )
		send( 'new', self, value=value)
		return value 
	def __setslice__(self, i,j, iterable ):
		"""Set values and send messages"""
		for current in self.__getslice__( i,j ):
			send( 'del', self, value=current )
		values = list(iterable)
		super(OList,self).__setslice__( i,j, values )
		for value in values:
			send( 'new', self, value=value )
		return values 
	def __iadd__( self, iterable ):
		"""Do an in-place add"""
		return self.__setslice__( len(self),len(self), iterable )
	extend = __iadd__
	

if __name__ == "__main__":
	from pydispatch.dispatcher import connect
	o = OList()
	out = []
	def on_new( signal, value ):
		out.append( (signal,value) )
	connect( on_new, sender=o )
	o.append( 'this' )
	assert out == [('new','this')], out
	del out[:]

	o[0:2] = [ 'those','them' ]
	assert out == [('del','this'),('new','those'),('new','them')], out
	del out[:]
	
	o[1] = 'that'
	assert out == [('del','them'),('new','that')], out
	del out[:]

	popped = o.pop( )
	assert popped == 'that', popped
	assert out == [('del','that')]
	del out[:]
	
	o.insert( 0, 'those' )
	assert out == [('new','those')]
	del out[:]
	
	o.remove( 'those' )
	assert out == [('del','those')]
	del out[:]
