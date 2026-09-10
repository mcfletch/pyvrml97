"""SimpleParse post-processor builds node-graph from parse-tree
"""

from typing import Any, List
# Named rather than starred, and `getString` is aliased on the way in: the
# module defines its own `getString` below, and this read `_getString =
# getString` *before* that definition, relying on the star import still
# holding the name at that point. Importing it under the name it is kept
# under says what is meant and does not depend on the order.
from simpleparse.dispatchprocessor import (
    DispatchProcessor,
    dispatch,
    dispatchList,
    lines,
)
from simpleparse.dispatchprocessor import getString as _getString

from vrml import node, field
from vrml.protofunctions import *
from vrml.arrays import array


def as_str(value: Any, encoding: str='utf-8') -> str:
    """A slice of the parse buffer as text

    simpleparse hands back whichever of bytes and text the source was read as,
    and a VRML97 string field holds text.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode(encoding)
    return str(value)


def getString(*args: Any, **named: Any) -> str:
    base = _getString(*args, **named)
    return as_str(base)


class ParseProcessor(DispatchProcessor):
    """Builds in-memory node-graph from VRML97 parse-tree"""

    def __init__(self, basePrototypes: Any=None, baseURI: str="") -> None:
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

            basePrototypes = basenamespaces.basePrototypes.copy()
        self.basePrototypes = basePrototypes
        self.baseURI = baseURI
        self.sceneGraphStack: "List[Any]" = []
        self.prototypeStack: "List[Any]" = []
        self.nodeStack: "List[Any]" = []
        self.fieldTypeStack: "List[Any]" = []

    ### High-level constructs in the grammar
    def header(self, table: Any, buffer: Any) -> None:
        """We ignore the header for now"""

    EOF = header

    def rootItem(self, table: Any, buffer: Any) -> None:
        """A scenegraph root-item"""
        (tag, left, right, children) = table
        # ROUTE and proto are already taken care of, as would be is
        # so we only need to worry about USE, Script and Node types
        items = dispatchList(self, children, buffer)
        result = [item for item in items if isinstance(item, node.Node)]
        self.sceneGraphStack[-1].children.extend(result)

    def vrmlScene(self, table: Any, buffer: Any) -> Any:
        """Instantiate a VRML scene object"""
        (tag, left, right, children) = table
        if self.sceneGraphStack:
            root = self.sceneGraphStack[-1]
            protoTypes = None
        else:
            root = None
            protoTypes = self.basePrototypes
        self.sceneGraphStack.append(
            self.basePrototypes.get('sceneGraph')(
                root=root,
                protoTypes=protoTypes,
                baseURI=self.baseURI,
            )
        )
        dispatchList(self, children, buffer)
        node = self.sceneGraphStack.pop()
        return node

    ### The two prototype sub-types
    def Proto(self, table: Any, buffer: Any) -> None:
        """Process a regular Prototype declaration"""
        (tag, left, right, children) = table
        proto = node.prototype(getString(children[0], buffer))
        self.prototypeStack.append(proto)
        try:
            dispatchList(self, children[1:-1], buffer)
            setSceneGraph(proto, dispatch(self, children[-1], buffer))
            self.sceneGraphStack[-1].addProto(proto)
        finally:
            self.prototypeStack.pop()

    def ExternProto(self, table: Any, buffer: Any) -> None:
        """Process an external Prototype declaration"""
        (tag, left, right, children) = table
        proto = node.prototype(getString(children[0], buffer))
        self.prototypeStack.append(proto)
        try:
            dispatchList(self, children[1:-1], buffer)
            setExternalURL(proto, dispatch(self, children[-1], buffer))
            self.sceneGraphStack[-1].addProto(proto)
        finally:
            self.prototypeStack.pop()

    ### Node instances of the various types
    def Node(self, table: Any, buffer: Any) -> Any:
        '''Create new node, returning the value to the caller'''
        (tag, start, stop, sublist) = table
        if sublist[0][0] == 'name':
            name = getString(sublist[0], buffer)
            GI = getString(sublist[1], buffer)
            rest = sublist[2:]
        else:
            name = ""
            GI = getString(sublist[0], buffer)
            rest = sublist[1:]
        prototype = self.sceneGraphStack[-1].getProto(GI)
        if prototype is None:
            raise NameError(
                """Prototype %s used without declaration on line %s"""
                % (
                    GI,
                    lines(end=start, buffer=buffer),
                )
            )
        newNode = prototype()
        root(newNode, self.sceneGraphStack[0])
        if name:
            self.sceneGraphStack[-1].regDefName(name, newNode)
        self.nodeStack.append(newNode)
        dispatchList(self, rest, buffer)
        self.nodeStack.pop()
        return newNode

    def Script(self, table: Any, buffer: Any) -> Any:
        '''A script node (can be a root node)'''
        (tag, start, stop, sublist) = table
        # what's the DEF name...
        if sublist and sublist[0][0] == 'name':
            name = getString(sublist[0], buffer)
            rest = sublist[1:]
        else:
            name = ""
            rest = sublist
        # build the node, with dummy fields
        newNode = self.basePrototypes.get('Script')(
            (),
        )
        vProto = newNode.__class__
        # register it
        root(newNode, self.sceneGraphStack[0])
        if name:
            self.sceneGraphStack[-1].regDefName(name, newNode)
        self.nodeStack.append(newNode)
        # now get the field-declarations...
        _fields: "List[Any]" = []
        attributes: "List[Any]" = []
        isMaps: "List[Any]" = []
        for item in rest:
            if item[0] in ("ScriptEventDecl", "ScriptFieldDecl"):
                f, mapName = dispatch(self, item, buffer)
                setattr(vProto, f.name, f)
                if mapName is not None:
                    isMaps.append((mapName, f.name))
            elif item[0] == 'Attr':
                attributes.append(item)
            else:
                dispatch(self, item, buffer)
        if isMaps:
            set = node.ismaps(self.prototypeStack[-1])
            for name, field in isMaps:
                set.setdefault(name, []).append((newNode, field))
        dispatchList(self, attributes, buffer)
        self.nodeStack.pop()
        return newNode

    def SFNull(self, tup: Any, buffer: Any) -> Any:
        '''Create a reference to the SFNull node'''
        return self.sceneGraphStack[-1].getProto("NULL")

    def USE(self, tup: Any, buffer: Any) -> Any:
        """Create a reference to an existing named node"""
        name = getString(tup, buffer)
        node = self.sceneGraphStack[-1].getDEF(name)
        if node is None:
            raise NameError(
                """Use of un-DEF'd name %s on line %s"""
                % (
                    name,
                    lines(end=tup[1], buffer=buffer),
                )
            )
        return node

    def ROUTE(self, table: Any, buffer: Any) -> Any:
        '''Create a new route object/node, add the current sceneGraph'''
        (tag, start, stop, sublist) = table
        (s, sf, d, df) = [getString(item, buffer) for item in sublist]
        (sn, dn) = [self.sceneGraphStack[-1].getDEF(name) for name in (s, d)]
        for each_node, name in ((sn, s), (dn, d)):
            if each_node is None:
                raise NameError(
                    """ROUTE of un-DEF'd name %s on line %s"""
                    % (
                        name,
                        lines(end=start, buffer=buffer),
                    )
                )
        self.sceneGraphStack[-1].addRoute(
            self.basePrototypes.get('ROUTE')(
                source=sn,
                sourceField=sf,
                destination=dn,
                destinationField=df,
            )
        )

    ### Field and event declarations
    def fieldDecl(self, table: Any, buffer: Any) -> None:
        (tag, left, right, (exposure, datatype, name, value)) = table
        datatype = getString(datatype, buffer)
        self.fieldTypeStack.append(datatype)
        try:
            value = dispatch(self, value, buffer)
            addField(
                self.prototypeStack[-1],
                field.newField(
                    getString(name, buffer),
                    datatype,
                    getString(exposure, buffer) == 'exposedField',
                    value,
                ),
            )
        finally:
            self.fieldTypeStack.pop()

    def extFieldDecl(self, table: Any, buffer: Any) -> None:
        '''An external field declaration, no default value'''
        (tag, start, stop, (exposure, datatype, name)) = table
        datatype = getString(datatype, buffer)
        addField(
            self.prototypeStack[-1],
            field.newField(
                getString(name, buffer),
                datatype,
                getString(exposure, buffer) == 'exposedField',
            ),
        )

    def eventDecl(self, table: Any, buffer: Any) -> None:
        (tag, left, right, (direction, datatype, name)) = table
        datatype = getString(datatype, buffer)
        addField(
            self.prototypeStack[-1],
            field.newEvent(
                getString(name, buffer),
                datatype,
                getString(direction, buffer) == 'eventOut',
            ),
        )

    def ScriptEventDecl(self, table: Any, buffer: Any) -> Any:
        (tag, left, right, sublist) = table
        direction, datatype, name = [getString(item, buffer) for item in sublist[:3]]
        if len(sublist) > 3:
            mapName = dispatch(self, sublist[3], buffer)
        else:
            mapName = None
        return (
            field.newEvent(name, datatype, direction == 'eventOut'),
            mapName,
        )

    def ScriptFieldDecl(self, table: Any, buffer: Any) -> Any:
        """Field declaration for a script node"""
        (tag, left, right, (exposure, datatype, name, value)) = table
        datatype = getString(datatype, buffer)
        self.fieldTypeStack.append(datatype)
        try:
            if value[0] == 'IS':
                mapName = self.IS(value, buffer)
                value = None
                fieldObject = field.newField(
                    getString(name, buffer),
                    datatype,
                    getString(exposure, buffer) == 'exposedField',
                )
            else:
                mapName = None
                value = dispatch(self, value, buffer)
                fieldObject = field.newField(
                    getString(name, buffer),
                    datatype,
                    getString(exposure, buffer) == 'exposedField',
                    value,
                )
            return (fieldObject, mapName)
        finally:
            self.fieldTypeStack.pop()

    ### Node attributes and field values
    def Attr(self, table: Any, buffer: Any) -> Any:
        '''An attribute of a node or script'''
        (tag, start, stop, (name, value)) = table
        name = getString(name, buffer)
        clientNode = self.nodeStack[-1]
        try:
            field = getField(clientNode, name)
        except AttributeError:
            raise AttributeError(
                """Unknown field name %s for node type %s on line %s"""
                % (
                    name,
                    protoName(clientNode),
                    lines(end=start, buffer=buffer),
                )
            ) from None
        if value[0] == 'IS':
            mapName = dispatch(self, value, buffer)
            set = node.ismaps(self.prototypeStack[-1])
            set.setdefault(mapName, []).append((clientNode, name))
        else:
            self.fieldTypeStack.append(field.typeName())
            try:
                value = dispatch(self, value, buffer)
                if isinstance(clientNode, node.PrototypedNode):
                    # prototyped nodes get IS-value updates
                    field.fset(clientNode, value, notify=1)
                else:
                    field.fset(clientNode, value, notify=0)
            finally:
                self.fieldTypeStack.pop()

    def Field(self, table: Any, buffer: Any) -> Any:
        '''A field value (of any type)'''
        (tag, start, stop, sublist) = table
        if sublist and sublist[0][0] in ('USE', 'Script', 'Node', 'SFNull'):
            if self.fieldTypeStack[-1] == 'SFNode':
                return dispatch(self, sublist[0], buffer)
            else:
                return dispatchList(self, sublist, buffer)
        elif self.fieldTypeStack[-1] == 'MFNode':
            return []
        else:
            # is a simple data type...
            function = getattr(self, self.fieldTypeStack[-1])
            return function(sublist, buffer)

    def SFBool(self, table: Any, buffer: Any) -> Any:
        '''Boolean, in Python tradition is either 0 or 1'''
        (tup,) = table
        return getString(tup, buffer) == 'TRUE'

    def SFFloat(self, table: Any, buffer: Any) -> Any:
        (tup,) = table
        return float(getString(tup, buffer))

    SFTime = SFFloat

    def SFInt32(self, table: Any, buffer: Any) -> Any:
        (tup,) = table
        return int(getString(tup, buffer), 0)

    SFUInt32 = SFInt32

    def SFVec3f(self, table: Any, buffer: Any) -> Any:
        return [float(getString(item, buffer)) for item in table]

    def SFVec2f(self, table: Any, buffer: Any) -> Any:
        return [float(getString(item, buffer)) for item in table]

    SFColor = SFVec3f

    def SFRotation(self, table: Any, buffer: Any) -> Any:
        return [float(getString(item, buffer)) for item in table]

    #: Every single vector is a run of numbers in the file, whatever its
    #: length and precision; the field is what knows how many to expect.
    SFVec4f = SFVec2d = SFVec3d = SFVec4d = SFRotation

    def SFArray(self, values: Any, buffer: Any, final: bool=True) -> Any:
        """Process a vector-of-values data-set"""
        result = []
        for tag, start, stop, children in values:
            if tag == 'vector':
                result.append(self.SFArray(children, buffer, final=False))
            else:
                result.append(float(buffer[start:stop]))
        if final:
            return array(result, 'f')
        return result

    #: A matrix is written as rows, so it is read as a nested run of numbers
    #: and the field reshapes it. A list of them is the same, one row deeper.
    SFArray32 = SFMatrix3f = SFMatrix4f = SFMatrix3d = SFMatrix4d = SFArray
    MFMatrix3f = MFMatrix4f = MFMatrix3d = MFMatrix4d = SFArray

    def MFInt32(self, tuples: Any, buffer: Any) -> Any:
        # localisation
        if not tuples:
            return []
        return [int(buffer[start:stop], 0) for (tag, start, stop, children) in tuples]

    SFImage = MFInt32

    def MFUInt32(self, tuples: Any, buffer: Any) -> Any:
        # localisation
        return [int(buffer[start:stop], 0) for (tag, start, stop, children) in tuples]

    def MFFloat(self, tuples: Any, buffer: Any) -> Any:
        return [float(buffer[start:stop]) for (tag, start, stop, children) in tuples]

    #: Every list of vectors is a flat run of numbers in the file; the field
    #: is what knows how wide each row is.
    MFColor = MFRotation = MFVec2f = MFVec3f = MFTime = MFFloat32 = MFFloat
    MFVec4f = MFVec2d = MFVec3d = MFVec4d = MFFloat

    def MFString(self, tuples: Any, buffer: Any) -> Any:
        bigresult = []
        for _tag, _start, _stop, sublist in tuples:
            result = []
            for element in sublist:
                if element[0] == 'CHARNODBLQUOTE':
                    result.append(as_str(buffer[element[1] : element[2]]))
                elif element[0] == 'ESCAPEDCHAR':
                    result.append(as_str(buffer[element[1] + 1 : element[2]]))
                elif element[0] == 'SIMPLEBACKSLASH':
                    result.append('\\')
            bigresult.append("".join(result))
        return bigresult

    def SFString(self, table: Any, buffer: Any) -> Any:
        '''Return the (escaped) string as a simple Python string'''
        ((tag, start, stop, sublist),) = table
        result = []
        for element in sublist:
            if element[0] == 'CHARNODBLQUOTE':
                result.append(as_str(buffer[element[1] : element[2]]))
            elif element[0] == 'ESCAPEDCHAR':
                result.append(as_str(buffer[element[1] + 1 : element[2]]))
            elif element[0] == 'SIMPLEBACKSLASH':
                result.append('\\')
        return "".join(result)

    ### Low-level/trivial constructs which have their own processing functions
    def IS(self, table: Any, buffer: Any) -> Any:
        '''Create a field reference'''
        (tag, start, stop, (nametuple,)) = table
        return getString(nametuple, buffer)

    def ExtProtoURL(self, table: Any, buffer: Any) -> Any:
        '''add the url to the external prototype'''
        (tag, start, stop, sublist) = table
        return self.MFString(sublist, buffer)
