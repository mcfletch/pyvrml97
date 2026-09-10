"""object for linearizing a scene graph to VRML97
"""


from typing import Any, Dict, List
from io import StringIO
from vrml import arrays
from vrml import protofunctions
from vrml.protofunctions import *
from vrml import node

#: Where a prototype's URL is kept.  It is written after the interface, as
#: VRML97 puts it, rather than among the fields the interface declares.
EXTERNAL_URL = 'externalURL'

defaults = {
    'subelspacer': ', ',
    'courtesyspace': ' ',
    'curindent': '',
    'indent': '\t',
    'numsep': ',',
    'full_element_separator': '\n',
    'mffieldsep': '\n',
    # EndComments say: if more than this many lines are between node start
    # and end, put a comment at the closing bracket saying what node/proto is
    # being closed.
    'EndComments': 10,
}
minimal1 = {
    'subelspacer': ', ',
    'numsep': ' ',
    'curindent': '',
    'indent': '  ',
    'full_element_separator': '\n',
    'courtesyspace': '',
    'mffieldsep': ' ',
}


def namekey(node: Any) -> Any:
    return node.name


def protoNames(skipProtos: Any) -> "Dict[str, int]":
    """The prototype names in `skipProtos`, as a set to look one up in.

    A caller names the prototypes to leave out either by name or by passing
    the prototype itself, in a mapping (whose keys are read) or any other
    iterable.
    """
    names: "Dict[str, int]" = {}
    if not skipProtos:
        return names
    if hasattr(skipProtos, 'keys'):
        skipProtos = skipProtos.keys()
    for item in skipProtos:
        names[item if isinstance(item, str) else protoName(item)] = 1
    return names


def linearise(value: Any, linvalues: Any=defaults, **namedargs: Any) -> str:
    """Linearise the given (node) value to a string"""
    lineariser = Lineariser(linvalues, **namedargs)
    return lineariser.linear(value)


class Lineariser:
    '''
    A data structure & methods for linearising
    sceneGraphs, nodes, scripts and prototypes.
    Should be used only once as member vars are not
    cleared after the initial linearisation.
    '''

    def __init__(self, linvalues: Any=None, alreadydone: Any=None, *args: Any, **namedargs: Any) -> None:
        if linvalues is None:
            linvalues = defaults
        if namedargs:
            linvalues = linvalues.copy()
            linvalues.update(namedargs)
        self.linvalues = linvalues
        if alreadydone is None:
            self.alreadydone = {}
        else:
            self.alreadydone = alreadydone

    def linear(
        self,
        clientNode: Any,
        buffer: Any=None,
        skipProtos: Any=None,
        skipUnusedProtos: Any=None,
        *args: Any,
        **namedargs: Any
    ) -> str:
        '''Linearise a node, script, or scenegraph

        skipProtos -- the prototypes to leave out, named either by name or by
            the prototype itself, in a mapping or any other iterable.  Their
            instances are still written, so this is how a caller writes a
            fragment for a file that already declares them.
        skipUnusedProtos -- when true, write only the prototypes something in
            the scene is an instance of, rather than every prototype the
            scenegraph has registered.
        '''
        # prototypes named in here are left out, so that a caller can write a
        # fragment for a file that already declares them; instances of them
        # are still written.
        self.skipProtos: "Dict[str, int]" = protoNames(skipProtos)
        # skipUnusedProtos skips the "prototype collection" linearisation step
        # this has the effect of not outputing any prototype which is not actually
        # used in the file.  By default is "off", that is, all protos are linearised
        self.skipUnusedProtos = skipUnusedProtos
        # protobuffer is a seperate buffer into which the prototype definitions are stored
        self.protobuffer = StringIO()
        self.protobuffer.write('#VRML V2.0 utf8\n')
        # protoalreadydone is used in place of the scenegraph-specific
        # node alreadydone.  This allows us to push all protos up to the
        # top level of the hierarchy (thus making the process of linearisation much simpler)
        self.protoalreadydone: "Dict[Any, Any]" = {}
        # main working algo...
        self.typecache = {
            'Script': self._Script,
            'NULL': self._nullNode,
            'sceneGraph': self._sceneGraph,
        }
        self.buffer = buffer or StringIO()
        self.alreadydone.clear()
        #: The scene graphs being written, innermost last; a prototype is
        #: output once per graph that refers to it.
        self.cursceneGraph: "List[Any]" = []
        self.curproto: "List[Any]" = []
        self.indentationlevel = 0
        if type(clientNode) in (list, tuple):
            for child in clientNode:
                self._linear(child)
                self.buffer.write('\n')
        else:
            self._linear(clientNode)
        del self.typecache  # to clear references to this node...
        self.alreadydone.clear()
        # side effect has filled up protobuffer for us
        rval = self.protobuffer.getvalue() + self.buffer.getvalue()
        self.buffer.close()
        self.protobuffer.close()
        return rval

    ### High-level constructs...
    def _sceneGraph(self, clientNode: Any) -> Any:
        '''
        A little niave, the sceneGraph just outputs everything
        in its prototypes, then everything in its childlist, then all its ROUTES
        '''
        for route in clientNode.routes:
            self._preroute(clientNode, route)
        if clientNode is None:
            startind = self.buffer.tell()
            if len(self.cursceneGraph) == 0:  # new file
                self.buffer.write('#VRML V2.0 utf8\n')
            self.alreadydone[id(clientNode)] = (
                startind,
                self.buffer.tell(),
            )  # register this scenegraph's extents
            return None
        startind = self._canUse(clientNode)
        if type(startind) is not int:  # this node has already been declared
            self.buffer.write(startind)
            return None
        # use a seperate Node alreadydone for each sceneGraph
        # so that we don't have cross-barrier USEs occuring
        oldalreadydone = self.alreadydone
        self.alreadydone = {}

        # localise buffer as we will be accessing it many times
        buffer = self.buffer
        # header now part of the protobuffer
        # if not self.cursceneGraph: # top level
        # 	buffer.write( '#VRML V2.0 utf8\n' ) # should only do this when it's the top-level object
        self.cursceneGraph.append(clientNode)

        # linearise the "free" prototypes (any actually registered with the sceneGraph)
        if (
            not self.skipUnusedProtos
        ):  # are supposed to linearise all prototypes currently in the sceneGraph, regardless of whether they are used
            for proto in clientNode.protoTypes.values():
                if id(proto) not in self.protoalreadydone:
                    self._proto(proto)
        # linearise the node/script children, they will include their prototypes if they are not already done
        for child in clientNode.children:
            self._linear(child)
            buffer.write(self.linvalues['full_element_separator'])
        # linearise the routes
        for route in clientNode.routes:
            # should check here to make sure the ROUTEs are valid
            self._route(route)
            # buffer.write( '%(full_element_separator)sROUTE %%s.%%s TO %%s.%%s'%self.linvalues%route )

        # restore original alreadydone dictionary
        self.alreadydone = oldalreadydone
        self.alreadydone[id(clientNode)] = (
            startind,
            buffer.tell(),
        )  # register this scenegraph's extents
        del self.cursceneGraph[-1]
        return None

    def _proto(self, clientNode: Any) -> Any:
        """Linearise a prototype, return whether the prototype is actually linearised"""
        # check that we haven't yet done this prototype, register the fact that we've already started it
        if type(clientNode) is not type:
            return

        clientName = protoName(clientNode)

        if builtin(clientNode):
            # this prototype should not be linearised
            return 0
        if clientName in self.skipProtos:
            # the caller says the output lands where this is already declared
            return 1
        if id(clientNode) in self.protoalreadydone:
            # this precise prototype has been linearised already...
            return 1
        elif self.protoalreadydone.get(name(clientNode)):
            # another prototype with the same name has already been linearised
            self.protoalreadydone[id(clientNode)] = 1
            return 1
        self.curproto.append(clientNode)
        self.protoalreadydone[clientName] = self.protoalreadydone[id(clientNode)] = 1

        # we don't want the prototypes constantly moving inward :)
        oldindent = self.indentationlevel
        self._indent(0)
        oldbuffer = self.buffer
        buffer = self.buffer = StringIO()  # local buffer only for this particular proto

        # write header (PROTO x [, EXTERNPROTO x [ )
        # A prototype is a class, and reading the field off a class answers the
        # field object rather than its value; `getExternalURL` is the accessor
        # that asks the field for the class's own value.
        externalURL = protofunctions.getExternalURL(clientNode)
        if externalURL:
            buffer.write('EXTERNPROTO %s [' % (clientName,))
        else:
            buffer.write('PROTO %s [' % (clientName,))
        # write the declaration...
        self._indent()
        self._eventDict(clientNode)
        # An EXTERNPROTO declares its interface and no values: the file the
        # URL names is where they are.  Writing a default there gives a file
        # the grammar will not read back.
        self._fieldDict(clientNode, requireDefault=not externalURL)
        self._dedent()
        linvalues = self.linvalues
        if externalURL:
            buffer.write('\n] ')
            from vrml import fieldtypes

            buffer.write(fieldtypes.MFString_vrmlstr(externalURL, self))
            buffer.write('\n')
        else:
            buffer.write('\n] {\n')
            # the following will write everything into the current proto's buffer
            # references to prototypes not already linearised will cause a recursive
            # call to proto that will write those into the protobuffer before returning
            sg = getSceneGraph(clientNode)
            if sg is not None:
                self._sceneGraph(sg)
            if 'EndComments' in linvalues and linvalues['EndComments'] * 60 < (
                (buffer.tell())
            ):
                buffer.write('\n}#End PROTO %s\n' % (clientName))
            else:
                buffer.write('\n}\n')
        self.alreadydone[id(clientNode)] = (
            self.protobuffer.tell(),
            self.protobuffer.tell() + buffer.tell(),
        )
        # note that we _always_ write out the prototype to the
        # prototype-specific buffer!  We do not write them into
        # the main buffer.  I suppose we could, but most of the
        # time you want the prototypes all at the front of the
        # file anyway.
        self.protobuffer.write(buffer.getvalue())
        # clear out the memory used by the buffer
        buffer.close()
        # return to the original buffer
        self.buffer = oldbuffer
        self._indent(oldindent)
        # note that startind is irrelevant for prototypes,
        # as they cannot be repeated, only multiply referenced.
        self.curproto.pop()
        return None

    def _Node(self, clientNode: Any, *args: Any, **namedargs: Any) -> Any:
        '''Linearise an individual node'''
        # if we don't already have this nodes prototype in the
        # root namespace, insert it there.  For now we don't allow
        # nested namespaces.  This is a serious limitation and should
        # be fixed at some point in time.
        self._proto(getPrototype(clientNode))
        buffer = self.buffer
        startind = self._canUse(clientNode)
        if type(startind) is not int:  # this node has already been declared
            buffer.write(startind)
            return None
        # now calculate the representation of this node...
        defName = self._defName(clientNode)
        namedargs['linvalues'] = linvalues = self.linvalues
        namedargs['alreadydone'] = self.alreadydone
        buffer.write(
            '%s%s {'
            % (
                defName,
                protoName(clientNode),
            )
        )
        position = buffer.tell()
        self._indent()
        self._attrDict(clientNode)

        # write the node-ending comment
        if buffer.tell() == position:
            buffer.write("%(courtesyspace)s}" % linvalues)
        elif 'EndComments' in linvalues and linvalues['EndComments'] * 60 < (
            (buffer.tell() - startind)
        ):
            DEF = name(clientNode)
            PROTO = protoName(clientNode)
            buffer.write(
                '%(full_element_separator)s%(curindent)s} #EndNode %%s'
                % linvalues
                % (DEF or PROTO)
            )
        else:
            buffer.write('%(full_element_separator)s%(curindent)s}' % linvalues)
        self._dedent()
        self.alreadydone[id(clientNode)] = startind, buffer.tell()
        return None

    def _Script(self, clientNode: Any) -> Any:
        '''
        Scripts should be output in the following format:
        DEF defName Script {
            fields
            events
            attributes
        }
        Both fields or attributes can have "IS's", and possibly
        the attributes as well.
        '''
        buffer = self.buffer
        startind = self._canUse(clientNode)
        if type(startind) is not int:  # this node has already been declared
            buffer.write(startind)
            return None
        # Note: we assume that defNames are being stored in the Node as well as the sceneGraph, if not, will need to do a reverse lookup there
        buffer.write('%sScript {' % (self._defName(clientNode),))
        self._indent()
        self._indent()
        linvalues = self.linvalues

        self._eventDict(getPrototype(clientNode))
        self._fieldDict(
            getPrototype(clientNode),
            requireDefault=1,
            skipFields=(EXTERNAL_URL, 'url', 'directOutput', 'mustEvaluate'),
        )
        self._dedent()
        self._attrDict(clientNode)
        DEF = name(clientNode)
        PROTO = protoName(clientNode)
        buffer.write(
            '%(full_element_separator)s%(curindent)s}#%%s' % linvalues % (DEF or PROTO)
        )
        self._dedent()
        self.alreadydone[id(clientNode)] = startind, buffer.tell()
        return None

    def _attrDict(self, object: Any) -> None:
        """Write out the attribute dictionary for an object"""
        buffer = self.buffer
        linvalues = self.linvalues
        if self.curproto:
            set = node.ismaps(self.curproto[-1])
            isMaps = {}
            for fieldName, fieldList in set.items():
                for n, field in fieldList:
                    if n is object:
                        isMaps[field] = fieldName
        else:
            isMaps = {}
        if protoName(object) == "Script":
            items = [
                field
                for field in getFields(object)
                if field.name in ('url', 'mustEvaluate', 'directOutput')
            ]
        else:
            items = [
                field
                for field in getFields(object)
                if field.name and field.name[0] != ' '
            ]
        items.sort()
        for field in items:
            # following slows us down, but prevents the chaff from showing up...
            val = field.fget(object)
            default = field.getDefault()
            if field.name in isMaps:
                buffer.write(
                    '%(full_element_separator)s%(curindent)s%(indent)s%%s IS %%s\t'
                    % linvalues
                    % (field.name, isMaps.get(field.name))
                )
            elif (
                default is not None and not arrays.safeCompare(default, val)
            ) or default is None:
                buffer.write(
                    '%(full_element_separator)s%(curindent)s%(indent)s%%s\t'
                    % linvalues
                    % (field.name,)
                )
                self._sffield(val, field)

    def _eventDict(self, clientNode: Any) -> None:
        '''
        Event Dictionaries have two possible sources of information,
        the eventDict and the isNames dictionary.  The first provides
        name, type, out, the second provides any IS bindings which
        need to be created.
        '''
        # need to get the IS/USE for the field if available
        buffer = self.buffer

        fields = sorted(getFields(clientNode, events=1), key=namekey)

        for field in [f for f in fields if (f.name and f.name[0] != ' ')]:
            buffer.write('%(full_element_separator)s%(curindent)s' % (self.linvalues))
            field.eventVrmlstr(self)
            # XXX do IS-mapping here!

    def _fieldDict(
        self,
        clientNode: Any,
        requireDefault: int=1,
        skipFields: Any=(EXTERNAL_URL,),
    ) -> None:
        """Write the field declarations of a prototype or a script

        requireDefault -- write each field's default after its declaration.
            An EXTERNPROTO's interface carries no values, so it asks for the
            declarations alone.
        skipFields -- the field names to leave out.
        """
        buffer = self.buffer
        fields = [
            field
            for field in getFields(clientNode)
            if (
                (field.name not in skipFields) and field.name and (field.name[0] != ' ')
            )
        ]
        fields.sort(key=namekey)
        for field in fields:
            buffer.write('%(full_element_separator)s%(curindent)s' % (self.linvalues))
            field.fieldVrmlstr(self, bool(requireDefault))

    def _fieldref(self, clientNode: Any, *args: Any, **namedargs: Any) -> Any:
        self.buffer.write('IS %s' % clientNode.declaredName)
        return None

    def _preroute(self, sceneGraph: Any, clientNode: Any) -> None:
        """Pre-scans all routes, forces all routed nodes to have DEF names"""
        for child in (clientNode.source, clientNode.destination):
            DEF = defName(child)
            if not DEF:
                count = 0
                PROTO = protoName(child)
                while 1:
                    name = "%s_%s" % (PROTO, count)
                    if sceneGraph.getDEF(name) is None:
                        sceneGraph.regDefName(name, child)
                        break
                    count += 1

    def _route(self, clientNode: Any) -> None:
        '''Linearise a route'''
        # should check here to make sure the ROUTEs are valid
        buffer = self.buffer

        sourcenode = defName(clientNode.source)
        destinationnode = defName(clientNode.destination)
        values = (
            sourcenode,
            clientNode.sourceField,
            destinationnode,
            clientNode.destinationField,
        )
        buffer.write(
            '%(full_element_separator)sROUTE %%s.%%s TO %%s.%%s'
            % self.linvalues
            % values
        )

    def _sffield(self, anyobj: Any, field: Any, *args: Any, **namedargs: Any) -> Any:
        '''
        Any to String takes an object and checks how it should
        be linearised given that it is supposed to become a fieldType
        This is done by first determining if the field has a __vrmlStr__
        attribute.  If it doesn't, a standard coerce_to is called with
        the particular fieldType as the source. and 'String' as the
        target.
        This is necessary because the SFNode field can have any of Scripts,
        Nodes, ProtoTypes and ExternProtos (well, not according to the
        parsers, but someone might attempt it).
        '''
        if field is node.RootScenegraphNode:
            return None
        # Whether this holds nodes is the *field's* to say.  `protoName` of a
        # plain list answers `__MFNode__` whatever is in it, so an MFString's
        # list of strings was written as a list of nodes: an opening bracket
        # that was never closed, with the node's next field swallowed inside
        # it, and a file that would not parse back.
        if field.typeName() in ('SFNode', 'MFNode'):
            try:
                pName = protoName(anyobj)
            except AttributeError:
                pass                # NULL, or a value that is not a node
            else:
                handler = self.typecache.get(pName)
                if handler:
                    return handler(anyobj)
                if isinstance(anyobj, list):
                    return self._mfnode(anyobj)
                return self._Node(anyobj)
        if hasattr(field, 'vrmlstr'):
            result = field.vrmlstr(anyobj, self)
            if result is not None:
                self.buffer.write(result)
        elif hasattr(self, field.typeName()):
            result = getattr(self, field.typeName())(anyobj)
            if result is not None:
                self.buffer.write(result)
        else:
            raise TypeError(
                '''Unknown fieldType %s, cannot convert to string''' % field
            )
        return None

    ### Utility functions...
    def _dedent(self) -> None:
        self.indentationlevel = self.indentationlevel - 1
        self.linvalues['curindent'] = self.linvalues['indent'] * self.indentationlevel

    def _indent(self, exact: Any=None) -> None:
        if exact is not None:
            self.indentationlevel = exact
        else:
            self.indentationlevel = self.indentationlevel + 1
        self.linvalues['curindent'] = self.linvalues['indent'] * self.indentationlevel

    def _canUse(self, clientNode: Any) -> Any:
        if id(clientNode) in self.alreadydone:
            DEF = defName(clientNode)
            if DEF:
                return 'USE ' + DEF
            # else have to linearise again, should warn the user
            else:
                keyvals = self.alreadydone[id(clientNode)]
                index = self.buffer.tell()
                try:
                    start, stop = keyvals
                    self.buffer.seek(start)
                    val = self.buffer.read(stop - start)
                    self.buffer.seek(index)
                    return (
                        '#WARNING HERE -- USE of node with no DEF name, Node duplicated\n'
                        + val
                    )
                except TypeError:
                    return '''#ERROR HERE -- USE of a parent node that has no DEF name USE ignored'''
        else:
            ind = self.alreadydone[id(clientNode)] = self.buffer.tell()
            return ind

    def _nullNode(self, clientNode: Any) -> None:
        self.buffer.write('NULL')

    def _defName(self, clientNode: Any) -> Any:
        DEF = defName(clientNode)
        if DEF:
            return 'DEF %s ' % (DEF)
        else:
            return ''

    def _linear(self, clientNode: Any) -> Any:
        '''Linearise a particular client node of whatever type by dispatching to
        appropriate method...'''
        if type(clientNode) is type:
            method = self._proto
        else:
            name = protoName(clientNode)
            method = self.typecache.get(name, self._Node)
        return method(clientNode)

    ### Field-type handlers...
    def _mfnode(self, anyobj: Any, *args: Any, **namedargs: Any) -> None:
        '''
        Really, this will handle any list of elements where all elements
        have a __vrmlStr__ method, but since most of those are nodes, we'll
        keep the name for now.
        format:
            [(mffieldsep)
            (curindent)(indent)child
            ...
            (curindent)]
        or:
            [ ]
        '''
        buffer = self.buffer
        linvalues = self.linvalues
        if anyobj:  # first test to see if there's any point doing the processing
            self._indent()
            buffer.write('[ ')
            for el in anyobj:
                buffer.write(
                    '%(full_element_separator)s%(curindent)s%(indent)s' % linvalues
                )
                self._linear(el)
            buffer.write('%(full_element_separator)s%(curindent)s]' % linvalues)
            self._dedent()
        else:
            buffer.write(' [%(courtesyspace)s]' % linvalues)
