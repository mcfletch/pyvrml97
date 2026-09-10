"""Scenegraph node-like "prototype" for VRML97"""
from typing import Optional

from vrml import node, protofunctions, protonamespace, fieldtypes, route
from vrml import copier as copiermodule
from vrml.vrml97 import nodetypes
import weakref
from .._bytes import unicode

class SceneGraph( nodetypes.Traversable, node.Node ):
    ''' A VRML 97 sceneGraph
    Attributes:
        __gi__ -- constant string "sceneGraph"
        DEF -- constant string ""
        children -- Node list
            List of the root children of the sceneGraph, nodes/scripts only
        routes -- ROUTE list
            List of the routes within the sceneGraph
        defNames -- string DEFName: Node node
            Mapping of DEF names to their respective nodes
        protoTypes -- Namespace prototypes
            Namespace (with chaining lookup) collection of prototypes
            getattr( sceneGraph.protoTypes, 'nodeGI' ) retrieves a prototype
    '''
    PROTO = "sceneGraph"
    children = node.MFNode( 'children',)
    routes = route.MFRoute(
        'routes',
    )
    baseURI = fieldtypes.SFString(
        'baseURI',
        1,
        "",
    )
    def __init__(
        self, root=None, protoTypes=None,
        routes=None, defNames=None,
        children=None,
        *args, **namedargs
    ):
        '''
        root -- sceneGraph root or Dictionary root or Module root or None
            Base object for root of protoType namespace hierarchy
        protoTypes -- string nodeGI: Prototype PROTO
            Dictionary of prototype definitions
        routes -- ROUTE list or (string sourcenode, string sourceeventOut, string destinationnode, string destinationeventOut) list
            List of route objects or tuples to be added to the sceneGraph
            see attribute routes
        defNames -- string DEFName: Node node
            see attribute defNames
        children -- Node list
            see attribute children
        '''
        #: A weak reference to the graph this one sits inside, or None where it
        #: is the outermost.  Weak, so a scene graph does not keep its parent
        #: alive.
        self.root: "Optional[weakref.ReferenceType]" = (
            weakref.ref( root ) if root is not None else None
        )
        if protoTypes is None:
            protoTypes = protonamespace.ProtoNamespace()
        self.protoTypes = protoTypes
        if defNames is None:
            defNames = {}
        self.defNames = defNames
        namedargs['children'] = children
        super( SceneGraph, self ).__init__(
            *args,
            **namedargs
        )
        node.Node.rootSceneGraph.fset( self, self )
        if routes:
            for route in routes:
                self.addRoute( route )
    def getProto( self, name ):
        """Get a prototype by name

        go up the scenegraph chain to try to resolve
        """
        current = self.protoTypes.get( name )
        if current is not None:
            return current
        elif hasattr( self, 'root'):
            reference = self.root
            if reference is not None:
                root = reference()
                if root is not None:
                    return root.getProto( name )
        return None

    def getDEF( self, name ):
        """Get a node by DEF name"""
        return self.defNames.get(name)

    def regDefName(self, defName, object):
        ''' Register a DEF name for a particular object

            defName -- string DEFName
            object -- Node node

        Eliminates previous references to the object by
        its current DEFName and sets the object's new
        DEFName.
        '''
        current = protofunctions.defName( object )
        if self.defNames.get(current) is object:
            del self.defNames[current]
        protofunctions.defName( object, defName )
        self.defNames[defName] = object
    def addProto(self, proto):
        '''Register a Prototype for this sceneGraph
        proto -- Prototype PROTO
        '''
        self.protoTypes[protofunctions.name( proto ) ] = proto
    def addRoute(self, route, *args):
        '''Add a route to the scenegraph

        route,args -- Possible forms:

            ROUTE object -- added to routes
            ((source)node,field,(destination)node,field) -- ROUTE
                created, nodes may be strings, in which case
                getDEF( node ) is called for each
            ((source)node,field,target( signal, sender, value )) --
                field.watch( target ) is called for the source
                node (which can be a DEF name).
        '''
        if args:
            route = (route,) + args
        if isinstance( route, (tuple,list)):
            if len(route) == 4:
                # 4-element route definition, e.g. from strings...
                from vrml.route import ROUTE
                source,sourceField,destination,destinationField = route
                if isinstance( source, (str,unicode)):
                    source = self.getDEF( source )
                if isinstance( destination, (str,unicode)):
                    destination = self.getDEF( destination )
                route = ROUTE(
                    source = source,
                    sourceField = sourceField,
                    destination = destination,
                    destinationField = destinationField,
                )
            elif len(route) == 3:
                # 2-element source plus a function to receive...
                source,sourceField,target = route
                if not callable( target ):
                    raise TypeError(
                        """Need a callable target object!"""
                    )
                if isinstance( source, (str,unicode)):
                    source = self.getDEF( source )
                field = protofunctions.getField( source, sourceField )
                field.watch( source, target, ('set',field) )
                field.watch( source, target, ('del',field) )
        self.routes.append( route )
        return route
##	def addIsMap( self, name, node, field ):
##		"""Add an isMap for the given name to the given node+field"""
##		self.isMaps.setdefault( name, []).append( (node,field) )

    def copy( self, copier=None ):
        """Copy this node for copier"""
        if copier is None:
            copier = copiermodule.Copier()
        # order for creation is going to be important to make sure
        # that prototypes are available to nodes getting re-built
        # if we aren't sharing protos...
        if not copier.shareProtos and self.protoTypes:
            # A prototype is a node *class*, and copying one means building a
            # second class with the same fields and the same body -- which
            # `Copier` says it does not do ("we don't currently support not
            # doing this").  Say so here rather than partway through a copy.
            raise NotImplementedError(
                """Copying a scene graph without sharing its prototypes is not"""
                """ supported; this one declares %d (%s). Use a Copier with"""
                """ shareProtos left on."""
                % (len(self.protoTypes), ', '.join(sorted(self.protoTypes)))
            )
        newPrototypes = self.protoTypes.copy()
        newDefs = {}
        for key,value in self.defNames.items():
            if (not key) or value is None:
                continue
            newDefs[key] = value.copy( copier )
        node = super( SceneGraph, self).copy( copier )
        node.protoTypes = newPrototypes
        node.defNames = newDefs
        return node

