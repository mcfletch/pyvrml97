"""Observable list class"""
from pydispatch.dispatcher import send
import sets

class OList( list ):
	"""List sub-class which generates pydispatch events on changes
	
	Generates 4 types of events:
	
		* NEW_CHILD_EVT, from self, with value=child, for each added child
		* NEW_PARENT_EVT, from child, with parent=self, for each added child 
		* DEL_CHILD_EVT, from self, with value=child, for each removed child 
		* DEL_PARENT_EVT, from child, with parent=self, for each removed child
		
	Note that the OList semantics are a little loose currently, as 
	it sometimes acts as though adding a new duplicate child is not 
	an event and sometimes acts as though it is.  This doesn't cause 
	problems for the OpenGLContext scenegraph.
	
	The OList is intended for situations where slow-write-fast-read 
	is the primary requirement, it allows you to hook writing events 
	in order to recalculate/cache values.
	"""
	NEW_CHILD_EVT = 'new'
	NEW_PARENT_EVT = 'added'
	DEL_CHILD_EVT = 'del'
	DEL_PARENT_EVT = 'removed'
	def _sendAdded( self, value ):
		"""Send events for adding value to self"""
		send( self.NEW_CHILD_EVT, self, value=value)
		send( self.NEW_PARENT_EVT, value, parent=self)
	def _sendRemoved( self, value ):
		"""Send events for removing value from self"""
		send( self.DEL_CHILD_EVT, self, value=value)
		send( self.DEL_PARENT_EVT, value, parent=self)
	
	def append( self, value ):
		"""Append a value and send a message"""
		super( OList,self ).append( value )
		self._sendAdded( value )
		return value 
	def insert( self, index, value ):
		"""Insert a new item at index"""
		super( OList,self ).insert( index, value )
		self._sendAdded( value )
		return value 
	def pop( self, index=None ):
		"""Pop a single item out of the list"""
		if index is None:
			index = len(self)-1
		value = super( OList,self ).pop( index )
		self._sendRemoved( value )
		return value
	def remove( self, item ):
		"""Remove this instance from the list"""
		super(OList,self).remove( item )
		self._sendRemoved( item )
		return item
	def __delitem__( self, index ):
		"""Delete a single item"""
		value = self[index]
		self._sendRemoved( value )
		return value
	def __delslice__( self, i,j ):
		"""Delete a slice of sub-items"""
		current = self[i:j]
		for value in current:
			self._sendRemoved( value )
		super( OList,self ).__delslice__( i,j )
		return current 
	def __setitem__( self, index, value ):
		"""Set a value and send a message"""
		current = self[index]
		if current is not value:
			self._sendRemoved( current )
		super( OList,self ).__setitem__( index, value )
		if current is not value:
			self._sendAdded( value )
		return value 
	def __setslice__(self, i,j, iterable ):
		"""Set values and send messages"""
		values = list(iterable)
		previous = self.__getslice__( i,j )
		currents = sets.Set( previous )
		super(OList,self).__setslice__( i,j, values )
		for value in values:
			if value not in currents:
				self._sendAdded( value )
			else:
				try:
					previous.remove( value )
				except ValueError, err:
					pass
		for current in previous:
			self._sendRemoved( current )
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
	
