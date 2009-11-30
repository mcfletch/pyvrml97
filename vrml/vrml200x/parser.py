"""VRML200X SimpleParse 2 Parser

VRML200x is a fairly minor modification to the VRML97 grammar,
with almost all of the changes being the more involved header,
and a few new field-types that are already accepted by the
VRML97 grammar.
"""
from simpleparse.parser import Parser
from simpleparse.common import chartypes

#print file
grammar = r'''
header         := headerStatement,profileStatement,componentStatement*,metaStatement*
headerStatement  := ('#X3D',ts,SFNumber,ts,'utf8',ts,headerComment?,newLine)/('#',headerComment?,newLine)
headerComment  := -newLine+
profileStatement := 'PROFILE', ts, profileName,newLine
profileName    := name
<newLine>      := ('\r\n'/'\r'/'\n')

componentStatement := 'COMPONENT',ts, componentNameId, ts,':', ts, componentSupportLevel
componentNameId := name
componentSupportLevel := SFNumber

metaStatement  := 'META',ts, metakey,ts,metavalue
metakey        := SFString
metavalue      := SFString

# not in the grammar, but apparently part of the VRML200x encoding
importStatement := 'IMPORT',ts,name,ts,'.',ts,name,(ts,asClause)?,ts
exportStatement := 'EXPORT',ts,name,(ts,asClause)?,ts
asClause       := 'AS',ts,name

vrmlFile       := header, vrmlScene, !, EOF
vrmlScene      := rootItem*
rootItem       := ts,(Proto/ExternProto/ROUTE/('USE',ts,USE,ts)/Script/Node),ts

Proto          := 'PROTO',ts,!, nodegi,ts,'[',ts,(fieldDecl/eventDecl)*,']', ts, '{', ts, vrmlScene,ts, '}', ts
fieldDecl	   := fieldExposure,ts,!,dataType,ts,name,ts,Field,ts

# inputOutput/initializeOnly not in the grammar
fieldExposure  := 'inputOutput'/'initializeOnly'/'field'/'exposedField'
dataType       := ('SF'/'MF')?,name
eventDecl      := eventDirection, ts, !,dataType, ts, name, ts

# inputOnly/outputOnly not in the grammar
eventDirection := 'inputOnly'/'outputOnly'/'eventIn'/'eventOut'
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
Field          := ( '[',ts,((SFNumber/SFBool/SFString/('USE',ts,USE,ts)/Script/Node),ts)*, ']'!, ts )/((SFNumber/SFBool/SFNull/SFString/('USE',ts,USE,ts)/Script/Node),ts)+

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
    def buildProcessor( self ):
        """Build and return a vrml.vrml97.parseprocessor.ParseProcessor"""
        from vrml.vrml97 import parseprocessor
        return parseprocessor.ParseProcessor()

def buildParser( declaration = grammar ):
    """Build a new VRMLParser object"""
    return VRMLParser( declaration, "vrmlFile" )