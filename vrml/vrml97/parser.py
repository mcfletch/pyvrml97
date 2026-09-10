"""VRML97-compliant SimpleParse 2.0 Parser

This example is a full VRML97 parser, originally created
for the mcf.vrml VRML-processing system.  It supports all
VRML97 constructs, and should be correct for any VRML97
content you can produce.  The parser is fairly fast
(parsing around 280,000 cps on a 1GHz Athlon machine).

This is the errorOnFail version of the grammar, otherwise
identical to the vrml.py module.  Note: there is basically
no speed penalty for the errorOnFail version compared to
the original version, as the errorOnFail code is not touched
unless a syntax error is actually found in the input text.
"""
from typing import Any
# Imported for its effect, not for a name: importing it registers EOF and
# the other character-type productions into simpleparse's shared
# definitions, which the grammar below refers to by name.
from simpleparse.common import chartypes  # noqa: F401
from simpleparse.parser import Parser

#print file
grammar = r'''
header         := -[\n]*
# `ts` before the end, because `header` stops at the newline and a scene of no
# nodes consumes nothing after it: without it a file that is a header alone --
# or one whose last line is a comment -- has whitespace left over and does not
# parse.
vrmlFile       := header, vrmlScene, ts, !, EOF
rootItem       := ts,(Proto/ExternProto/ROUTE/('USE',ts,USE,ts)/Script/Node),ts
vrmlScene      := rootItem*

Proto          := 'PROTO',ts,!, nodegi,ts,'[',ts,(fieldDecl/eventDecl)*,']', ts, '{', ts, vrmlScene,ts, '}', ts
fieldDecl	   := fieldExposure,ts,!,dataType,ts,name,ts,Field,ts
fieldExposure  := 'field'/'exposedField'
dataType       := ('SF'/'MF')?,name
eventDecl      := eventDirection, ts, !,dataType, ts, name, ts
eventDirection := 'eventIn'/'eventOut'
ExternProto    := 'EXTERNPROTO',ts,!,nodegi,ts,'[',ts,(extFieldDecl/eventDecl)*,']', ts, ExtProtoURL
extFieldDecl   := fieldExposure,ts,!,dataType,ts,name,ts
ExtProtoURL    := '['?,(ts,SFString)*, ts, ']'?, ts  # just an MFString by another name :)

ROUTE          := 'ROUTE',ts, !,name,'.',name, ts, 'TO', ts, name,'.',name, ts

Node           := ('DEF',ts,!,name,ts)?,nodegi,ts,'{',ts,(Proto/ExternProto/ROUTE/Attr)*,ts,!,'}', ts

Script         := ('DEF',ts,!,name,ts)?,'Script',ts,!,'{',ts,(ScriptFieldDecl/ScriptEventDecl/Proto/ExternProto/ROUTE/Attr)*,ts,'}', ts
ScriptEventDecl := eventDirection, ts, !,dataType, ts, name, ts, ('IS', ts,!, IS,ts)?
ScriptFieldDecl := fieldExposure,ts,!,dataType,ts,name,ts,(('IS', ts,!,IS,ts)/Field),ts

SFNull         := 'NULL', ts

# should really have an optimised way of declaring a different reporting name for the same production...
USE            := name
IS             := name
nodegi         := name
Attr           := name, ts, (('IS', ts,IS,ts)/Field), ts
Field          := ( '[',ts,((vector/SFNumber/SFBool/SFString/('USE',ts,USE,ts)/Script/Node),ts)*, ']'!, ts )/((SFNumber/SFBool/SFNull/SFString/('USE',ts,USE,ts)/Script/Node),ts)+

vector         := '[',ts,((vector/SFNumber),ts)*,']'
name           := -[][0-9{}\000-\020"'#,.\\ ],  -[][{}\000-\020"'#,.\\ ]*
SFNumber       := [-+]*, ( ('0',[xX],[0-9A-Fa-f]+) / ([0-9.]+,([eE],[-+0-9.]+)?))
SFBool         := 'TRUE'/'FALSE'
SFString       := '"',(CHARNODBLQUOTE/ESCAPEDCHAR/SIMPLEBACKSLASH)*,'"'!
CHARNODBLQUOTE :=  -[\134"]+
SIMPLEBACKSLASH := '\134'
ESCAPEDCHAR    := '\\"'/'\134\134'
<ts>           :=  ( [ \011-\015,]+ / ('#',-'\012'*,'\n')+ )*
'''

class VRMLParser( Parser ):
    """Simple subclassing of Parser to create proper ParseProcessor"""
    def buildProcessor( self ) -> Any:
        """Build and return a vrml.vrml97.parseprocessor.ParseProcessor"""
        from vrml.vrml97 import parseprocessor
        return parseprocessor.ParseProcessor()

def buildParser( declaration: Any = grammar ) -> Any:
    """Build a new VRMLParser object"""
    return VRMLParser( declaration, "vrmlFile" )
