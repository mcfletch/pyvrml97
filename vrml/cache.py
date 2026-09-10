"""Caching mechanism for scene graph

Basically, the scenegraph Cache allows you to associate
data with particular nodes in the scene graph without
actually attaching the information to the particular
node being annotated.

This allows us to store cached information such as:
    display list objects
    texture objects
    compiled array geometry

The cache uses weak reference key dictionaries to clear
the cache of data associated with deleted nodes within
the scene graph.  similarly, cache is cleared when node
fields which are dependencies of the cache are changed.

The cache is based on the vrml.field and dispatch.dispatcher
modules.  All field objects by default provide dispatcher
notifications on set and delete, and can provide
notification on get as well.  The cache watches for these
notifications for dependent nodes where the dispatcher
messages are (type, fieldObject) for type in ("set","del").

There is a per-context cache, and a global cache, display-
lists, textures, etceteras should be stored in the per-
context cache, while data with dependencies only on the
node can be stored in the global cache.

Note:
    The cache makes extensive use of weak references, and
    was the failure case which exposed a number of problems
    with the Python 2.2.2 weakref and weakkeydictionary
    mechanisms.
"""
from typing import Any, Callable, List, Optional
from vrml import protofunctions
import weakref
#from vrml.weakkeydictfix import WeakKeyDictionary
from pydispatch import dispatcher
import traceback

class Cache (dict):
    """Trivial sub-class of a dict which has some convenience methods

    Maps id(client): {
        key="": CacheHolder()
    }

    That is, for each client node, a dictionary
    holds opaque key(normally strings) to CacheHolder
    instances.  The CacheHolder is responsible for
    most of the implementation of the cache.
    """
    def getHolder( self, client: Any, key: Any = "") -> "Optional[CacheHolder]":
        """Return the cache holder for the given client and key"""
        current = self.get(id(client))
        if current is not None:
            return current.get( key)
        return None
    def getData( self, client: Any, key: Any="", default: Any=None) -> Any:
        """Return the data for given client and key, default otherwise"""
        current = self.get( id(client) )
        if current is not None:
            current = current.get( key )
            if current is not None:
                return current.data
        return default
    def holder(
        self,
        client: Any,
        data: Any,
        key: Any="",
    ) -> "CacheHolder":
        """Create a new CacheHolder in this cache"""
        return CacheHolder(
            client,
            data,
            key,
            self,
        )

CACHE = Cache()
getData = CACHE.getData

def cleaner( cache: Any, id: Any ) -> "Callable[[Any], None]":
    """Return callback function that cleans the given id from cache"""
    def clean_id( weak: Any ) -> None:
        try:
            del cache[id]
        except Exception:
            pass
    return clean_id


class CacheHolder( object ):
    """Holder for data values within a cache

    The CacheHolder provides the bulk of the cache
    implementation.  It associates an opaque data value
    with a client node and an opaque key.  The key
    value allows multiple dimensions of storage, to
    allow, for instance storing compiled shadow
    information separate from compiled geometry
    information.

    The depend method uses the dispatcher module
    to invalidate this CacheHolder when the given
    fields for the given nodes are changed.

    Attributes:
        client -- weak reference to the client node
        key -- strong reference to the opaque key value
        data -- strong reference to the opaque data value
        cache -- weak reference to the cache in which
            we are storing ourselves
    """
    #__slots__ = ('client','data','key','cache','nodeDependencies','__weakref__','notifier')
    def __init__(
        self,
        client: Any, data: Any,
        key: Any="",
        cache: Any = CACHE,
    ) -> None:
        """Initialise the cache-deletion callable

        client -- the node doing the caching, if gc'd,
            then the entire cache for the node is deleted
        key -- opaque key into the cache's per-node storage
        cache -- the particular cache in which to store
            ourselves.
        """
        client_id = id(client)
        self.client = weakref.ref(client, cleaner( cache,client_id) )
        self.key = key
        self.data = data
        self.cache = weakref.ref( cache )
        self.nodeDependencies: "List[Any]" = []

        # get the cached values for this client node
        set = cache.get(client_id, None)
        if set is None:
            cache[ client_id ] = set = {}
        set[key] = self
    def set( self, data: Any ) -> None:
        """Set data after instantiation"""
        self.data = data

    def depend( self, node: Any, field: Any=None ) -> None:
        """Add a dependency on given node's field value

        source -- the node being watched
        field -- the field on the node being watched

        Dependency on the node means that this cache
        holder will be invalidated if the field value
        changes.  This does not create a dependency
        on the existence of node, so you should set
        the dependency for the field holding any
        nodes which should invalidate this CacheHolder

        Note:
            This does not affect any other CacheHolder
            for our client node.
        """
        if field is not None:
            if isinstance( field, bytes ):
                field = field.decode( 'utf-8' )
            if isinstance( field, str ):
                field = protofunctions.getField(node, field)
            self.depend_signal(
                ('set', field),#signal
                node, # sender
            )
            self.depend_signal(
                ('del', field),#signal
                node, # sender
            )
            self.depend_signal(
                ('route', field),#signal
                node, # sender
            )
        else:
            # dependency on the mere existence of the node
            self.depend_object( node )
    def depend_signal( self, signal: Any, sender: Any=dispatcher.Any ) -> None:
        """Depend on signal from sender"""
        dispatcher.connect(
            self.clear,#receiver
            signal,
            sender,
        )
    def depend_object( self, node: Any ) -> None:
        """Depend on node's existence"""
        self.nodeDependencies.append(
            weakref.ref(
                node,
                self,
            )
        )
    def clear( self, signal: Any=None, sender: Any=None ) -> None:
        """Clear this object's held value, so the next read builds a new one

        The dependencies stay, since what they record is what the *next*
        value will be built from.
        """
        self.data = None
        if not self.client():
            # Nothing will ask for a value built for a node that has gone, so
            # the entry goes as well rather than sitting empty.
            self( signal=signal, sender=sender )
    def __call__( self, signal: Any=None, sender: Any=None ) -> "Optional[int]":
        """Delete the cached value (this object)

        Answers 1 where an entry was found and removed and 0 where there was
        none to remove, and None where the cache raised while being read --
        which is reported rather than passed on, since this runs as a weak
        reference's callback and has nobody to raise to.

        This de-registers ourselves from our cache object,
        with suitable checks for whether our cache is still
        alive itself, and whether it still has an entry
        for our client and our key.

        If this is the last registered cache object
        for our client, deletes the overall cache dictionary
        for the client.
        """
        try:
            cache = self.cache()
            if cache is None:
                return 0
            client = self.client()
            if client is None:
                return 0
            client_id = id(client)
            current = cache.get( client_id )
            self.data = None
            if current is None:
                return 0
            try:
                del current[ self.key ]
                if not current:
                    # `pop` rather than `del`: this runs as a weak
                    # reference's callback, so another one may have taken the
                    # entry out between the read above and here.
                    cache.pop( client_id, None )
                del self.nodeDependencies[:]
                return 1
            except KeyError:
                return 0
        except RuntimeError:
            traceback.print_exc()
            return None

