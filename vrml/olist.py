"""Observable list class"""
from pydispatch.dispatcher import send
import sets

class OList( list ):
	"""List sub-class which can generate pydispatch events on changes
	
	Note that the OList semantics are a little loose currently, as 
	it sometimes acts as though adding a new duplicate child is not 
	an event and sometimes acts as though it is.  This doesn't cause 
	problems for the OpenGLContext scenegraph.
	"""
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
	def __delitem__( self, index ):
		"""Delete a single item"""
		value = self[index]
		send( 'del', self, value=value )
		return value
	def __delslice__( self, i,j ):
		"""Delete a slice of sub-items"""
		current = self[i:j]
		for value in current:
			send( 'del', self, value=value )
		super( OList,self ).__delslice__( i,j )
		return current 
	def __setitem__( self, index, value ):
		"""Set a value and send a message"""
		current = self[index]
		if current is not value:
			send( 'del', self, value=current )
		super( OList,self ).__setitem__( index, value )
		if current is not value:
			send( 'new', self, value=value)
		return value 
	def __setslice__(self, i,j, iterable ):
		"""Set values and send messages"""
		values = list(iterable)
		previous = self.__getslice__( i,j )
		currents = sets.Set( previous )
		super(OList,self).__setslice__( i,j, values )
		for value in values:
			if value not in currents:
				send( 'new', self, value=value )
			else:
				try:
					previous.remove( value )
				except ValueError, err:
					pass
		for current in previous:
			send( 'del', self, value=current )
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
	assert out == [('new','those'),('new','them'),('del','this'),], out
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
	
	
	o[:] = [ 'those','them','their' ]
	del out[:]
	del o[1:2]
	assert out == [('del','them')], out

	o[:] = [ 'those','them','their','thou' ]
	del out[:]
	o[1:3] = ['them','those','that','them']
	assert out == [('new','those'),('new','that'),('del','their')], out
	
