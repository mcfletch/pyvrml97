"""VRML97 Script-node stub"""
from vrml import node, fieldtypes
from vrml.vrml97 import nodetypes

class _Script( nodetypes.Children, node.Node ):
    """A sub-type of node with scripting/pseudo-proto support

    The class here just handles basic node-like functionality,
    a special constructor factory takes care of the PROTO-like
    functionality.
    """
    url = fieldtypes.MFString(
        'url', 1,
    )
    directOutput = fieldtypes.SFBool(
        'directOutput', default = 0,
    )
    mustEvaluate = fieldtypes.SFBool(
        'mustEvaluate', default = 0,
    )
    
def Script( fields, **namedarguments ):
    """Create a new script prototype and an instance of that prototype"""
    proto = node.prototype( 'Script', fields, baseClasses = (_Script,) )
    return proto( **namedarguments )
