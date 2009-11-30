"""SimpleParse post-processor builds node-graph from parse-tree
"""
from simpleparse.dispatchprocessor import *
from vrml import node, field, fieldtypes
from vrml.protofunctions import *
from vrml.arrays import array

class ParseProcessor( DispatchProcessor ):
    """Builds in-memory node-graph from VRML97 parse-tree
    """
    def __init__( self, basePrototypes=None, baseURI=""):
        """Initialise the ParseProcessor

        basePrototypes -- name: constructor mapping for all
            prototypes to be built by the processor.  Should
            include at least:

                * Script
                * PROTO
                * NULL
                * sceneGraph
                * ROUTE

            as those "node" types are used during the
            building process.  You must also include any
            built-in node types which you want recognised
            without needing a prototype declaration.

            If None, will use:
                vrml.vrml97.basenamespaces.basePrototypes
            
        """
        self.position = 0
        if basePrototypes is None:
            from vrml.vrml97 import basenamespaces
            basePrototypes = basenamespaces.basePrototypes
        self.basePrototypes = basePrototypes
        self.baseURI = baseURI
        self.sceneGraphStack = [
        ]
        self.prototypeStack = []
        self.nodeStack = []
        self.fieldTypeStack = []

    ### High-level constructs in the grammar
    def header( self, (tag, left, right, children), buffer):
        """We ignore the header for now"""
    EOF = header
    def rootItem( self, (tag, left, right, children), buffer):
        """A scenegraph root-item"""
        # ROUTE and proto are already taken care of, as would be is
        # so we only need to worry about USE, Script and Node types
        items  = dispatchList( self, children, buffer )
        result = [
            item for item in items
            if isinstance( item, node.Node )
        ]
        self.sceneGraphStack[-1].children.extend( result )
    def vrmlScene( self, (tag, left, right, children), buffer):
        """Instantiate a VRML scene object"""
        if self.sceneGraphStack:
            root = self.sceneGraphStack[-1]
            protoTypes = None
        else:
            root = None
            protoTypes = self.basePrototypes
        self.sceneGraphStack.append(
            self.basePrototypes.get( 'sceneGraph')(
                root = root,
                protoTypes=protoTypes,
                baseURI = self.baseURI,
            )
        )
        dispatchList( self, children, buffer )
        node = self.sceneGraphStack.pop()
        return node
    ### The two prototype sub-types
    def Proto( self, (tag, left, right, children), buffer):
        """Process a regular Prototype declaration"""
        proto = node.prototype(getString( children[0], buffer))
        self.prototypeStack.append(
            proto
        )
        try:
            dispatchList( self, children[1:-1], buffer )
            setSceneGraph( proto, dispatch( self, children[-1], buffer ))
            self.sceneGraphStack[-1].addProto( proto )
        finally:
            self.prototypeStack.pop( )
    def ExternProto( self, (tag, left, right, children), buffer):
        """Process an external Prototype declaration"""
        proto = node.prototype(getString( children[0], buffer))
        self.prototypeStack.append(
            proto
        )
        try:
            dispatchList( self, children[1:-1], buffer )
            setExternalURL( proto, dispatch( self, children[-1], buffer ))
            self.sceneGraphStack[-1].addProto( proto )
        finally:
            self.prototypeStack.pop( )
            
    ### Node instances of the various types
    def Node (self, (tag, start, stop, sublist), buffer):
        ''' Create new node, returning the value to the caller'''
        if sublist[0][0] == 'name':
            name = getString ( sublist [0], buffer)
            GI = getString ( sublist [1], buffer)
            rest = sublist [2:]
        else:
            name = ""
            GI = getString ( sublist [0], buffer)
            rest = sublist [1:]
        prototype = self.sceneGraphStack [-1].getProto( GI )
        if prototype is None:
            raise NameError(
                """Prototype %s used without declaration on line %s"""%(
                    GI,
                    lines( end=start, buffer=buffer),
                )
            )
        newNode = prototype()
        root( newNode, self.sceneGraphStack [0])
        if name:
            self.sceneGraphStack [-1].regDefName( name, newNode )
        self.nodeStack.append (newNode)
        dispatchList(self, rest, buffer)
        self.nodeStack.pop ()
        return newNode

    def Script( self, (tag, start, stop, sublist), buffer):
        ''' A script node (can be a root node)'''
        # what's the DEF name...
        if sublist and sublist[0][0] == 'name':
            name = getString ( sublist [0], buffer)
            rest = sublist [1:]
        else:
            name = ""
            rest = sublist
        # build the node, with dummy fields
        newNode = self.basePrototypes.get('Script')(
            (),
        )
        vProto = newNode.__class__
        # register it
        root( newNode, self.sceneGraphStack [0])
        if name:
            self.sceneGraphStack [-1].regDefName( name, newNode )
        self.nodeStack.append (newNode)
        # now get the field-declarations...
        fields, attributes,isMaps = [], [], []
        for item in rest:
            if item[0] in ("ScriptEventDecl", "ScriptFieldDecl"):
                f,mapName = dispatch( self, item, buffer)
                setattr( vProto, f.name, f )
                if mapName is not None:
                    isMaps.append( (mapName,f.name) )
            elif item[0] == 'Attr':
                attributes.append( item )
            else:
                dispatch( self, item, buffer)
        if isMaps:
            set = node.ismaps( self.prototypeStack[-1] )
            for (name, field) in isMaps:
                set.setdefault( name, []).append( (newNode,field) )
        dispatchList(self, attributes, buffer)
        self.nodeStack.pop ()
        return newNode

    def SFNull(self, tup, buffer):
        ''' Create a reference to the SFNull node '''
        return self.sceneGraphStack [-1].getProto( "NULL" )

    def USE( self, tup, buffer ):
        """Create a reference to an existing named node"""
        name = getString( tup, buffer)
        node = self.sceneGraphStack[-1].getDEF( name )
        if node is None:
            raise NameError(
                """Use of un-DEF'd name %s on line %s"""%(
                    name,
                    lines( end=tup[1], buffer=buffer),
                )
            )
        return node

    def ROUTE(self, (tag, start, stop,  sublist), buffer):
        ''' Create a new route object/node, add the current sceneGraph '''
        (s,sf,d,df)  = [getString(item, buffer) for item in sublist]
        (sn,dn) = [ self.sceneGraphStack[-1].getDEF( name ) for name in (s,d)]
        for (node,name) in ((sn,s),(dn,d)):
            if node is None:
                raise NameError(
                    """ROUTE of un-DEF'd name %s on line %s"""%(
                        name,
                        lines( end=start, buffer=buffer),
                    )
                )
        self.sceneGraphStack[-1].addRoute(
            self.basePrototypes.get( 'ROUTE' )(
                source = sn,
                sourceField = sf,
                destination = dn,
                destinationField = df,
            )
        )

    ### Field and event declarations
    def fieldDecl( self, (tag, left, right, (exposure, datatype, name, value)), buffer):
        datatype = getString( datatype, buffer )
        self.fieldTypeStack.append(
            datatype
        )
        try:
            value = dispatch( self, value, buffer )
            addField(
                self.prototypeStack[-1],
                field.newField(
                    getString(name, buffer),
                    datatype,
                    getString( exposure, buffer ) == 'exposedField',
                    value,
                )
            )
        finally:
            self.fieldTypeStack.pop()
    def extFieldDecl(self, (tag, start, stop, (exposure, datatype, name)), buffer):
        ''' An external field declaration, no default value '''
        datatype = getString( datatype, buffer )
        addField(
            self.prototypeStack[-1],
            field.newField(
                getString(name, buffer),
                datatype,
                getString( exposure, buffer ) == 'exposedField',
            )
        )
        
    def eventDecl( self, (tag, left, right, (direction, datatype, name)), buffer):
        datatype = getString( datatype, buffer )
        addField(
            self.prototypeStack[-1],
            field.newEvent(
                getString(name, buffer),
                datatype,
                getString( direction, buffer ) == 'eventOut',
            )
        )
    def ScriptEventDecl( self,(tag, left, right, sublist), buffer):
        direction, datatype, name = [getString( item,buffer) for item in sublist[:3]]
        if len(sublist) > 3:
            mapName = dispatch( self, sublist[3], buffer)
        else:
            mapName = None
        return (
            field.newEvent(name, datatype, direction=='eventOut'),
            mapName,
        )
    def ScriptFieldDecl( self, (tag, left, right, (exposure, datatype, name, value)), buffer):
        """Field declaration for a script node"""
        datatype = getString( datatype, buffer )
        self.fieldTypeStack.append(
            datatype
        )
        try:
            if value[0] == 'IS':
                mapName = self.IS( value, buffer )
                value = None
                fieldObject = field.newField(
                    getString(name, buffer),
                    datatype,
                    getString( exposure, buffer ) == 'exposedField',
                )
            else:
                mapName = None
                value = dispatch( self, value, buffer )
                fieldObject = field.newField(
                    getString(name, buffer),
                    datatype,
                    getString( exposure, buffer ) == 'exposedField',
                    value
                )
            return (fieldObject, mapName)
        finally:
            self.fieldTypeStack.pop()

    ### Node attributes and field values
    def Attr(self, (tag, start, stop, (name, value)), buffer):
        ''' An attribute of a node or script '''
        name = getString ( name, buffer )
        clientNode = self.nodeStack[-1]
        try:
            field = getField( clientNode, name )
        except AttributeError:
            raise AttributeError(
                """Unknown field name %s for node type %s on line %s"""%(
                    name,
                    protoName(clientNode),
                    lines( end=start, buffer=buffer),
                )
            )
        if value[0] == 'IS':
            mapName = dispatch( self, value, buffer )
            set = node.ismaps( self.prototypeStack[-1] )
            set.setdefault( mapName, []).append( (clientNode,name) )
        else:
            self.fieldTypeStack.append(
                field.typeName()
            )
            try:
                value = dispatch( self, value, buffer )
                if isinstance( clientNode, node.PrototypedNode):
                    # prototyped nodes get IS-value updates
                    field.fset( clientNode, value, notify=1 )
                else:
                    field.fset( clientNode, value, notify=0 )
            finally:
                self.fieldTypeStack.pop()

    def Field( self, (tag, start, stop, sublist), buffer):
        ''' A field value (of any type) '''
        if sublist and sublist[0][0] in ('USE','Script','Node','SFNull'):
            if self.fieldTypeStack[-1] == 'SFNode':
                return dispatch( self, sublist[0], buffer )
            else:
                return dispatchList(self, sublist, buffer )
        elif self.fieldTypeStack[-1] == 'MFNode':
            return []
        else:
            # is a simple data type...
            function = getattr( self, self.fieldTypeStack[-1] )
            return function( sublist, buffer )
            
    def SFBool( self, (tup,), buffer):
        '''Boolean, in Python tradition is either 0 or 1'''
        return getString(tup, buffer) == 'TRUE'

    def SFFloat( self, (tup,), buffer):
        return float( getString(tup, buffer) )
    SFTime = SFFloat
    def SFInt32( self, (tup,), buffer ):
        return int( getString(tup, buffer), 0 )
    def SFVec3f( self, (x,y,z), buffer ):
        return [ float( getString(item,buffer)) for item in (x,y,z) ]
    def SFVec2f( self, (x,y), buffer ):
        return [ float( getString(item,buffer)) for item in (x,y) ]
    SFColor = SFVec3f
    def SFRotation( self, (x,y,z,a), buffer ):
        return [ float( getString(item,buffer)) for item in (x,y,z,a) ]
    
    def SFArray( self, values, buffer, final=True ):
        """Process a vector-of-values data-set"""
        result = []
        for (tag,start,stop,children) in values:
            if tag == 'vector':
                result.append( self.SFArray( children, buffer, final=False ))
            else:
                result.append( float(buffer[start:stop] ) )
        if final:
            result = array( result, 'f' )
        return result 

    def MFInt32( self, tuples, buffer ):
        # localisation
        return [
            int(buffer[start:stop],0) 
            for (tag, start, stop, children) in tuples
        ]
    SFImage = MFInt32
    def MFUInt32( self, tuples, buffer ):
        # localisation
        return [
            long(buffer[start:stop],0) 
            for (tag, start, stop, children) in tuples
        ]
    def MFFloat( self, tuples, buffer ):
        return [float(buffer[start:stop]) for (tag, start, stop, children) in tuples]
    MFColor = MFRotation = MFVec2f = MFVec3f = MFTime = MFFloat32 = MFFloat
    

    def MFString( self, tuples, buffer ):
        bigresult = []
        for (tag, start, stop, sublist) in tuples:
            result = []
            for element in sublist:
                if element[0] == 'CHARNODBLQUOTE':
                    result.append( buffer[element[1]:element[2]] )
                elif element[0] == 'ESCAPEDCHAR':
                    result.append( buffer[element[1]+1:element[2]] )
                elif element[0] == 'SIMPLEBACKSLASH':
                    result.append( '\\' )
            bigresult.append( "".join( result) )
        return bigresult
    def SFString( self, ((tag, start, stop, sublist),), buffer):
        '''Return the (escaped) string as a simple Python string'''
        result = []
        for element in sublist:
            if element[0] == 'CHARNODBLQUOTE':
                result.append( buffer[element[1]:element[2]] )
            elif element[0] == 'ESCAPEDCHAR':
                result.append( buffer[element[1]+1:element[2]] )
            elif element[0] == 'SIMPLEBACKSLASH':
                result.append( '\\' )
        return "".join( result )

    ### Low-level/trivial constructs which have their own processing functions
    def IS(self, (tag, start, stop, (nametuple,)), buffer):
        ''' Create a field reference '''
        return getString (nametuple, buffer)
    def ExtProtoURL( self, (tag, start, stop, sublist), buffer):
        ''' add the url to the external prototype '''
        return self.MFString( sublist, buffer )