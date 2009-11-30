"""Base namespace for VRML97

The basePrototypes object holds a protonamespace object
which contains a mapping from canonical node name to
node representation.

See vrml.vrml97.basenodes for most of the actual
node definitions.
"""
from vrml import node, protonamespace, fieldtypes, route
from vrml.vrml97 import script, basenodes, scenegraph

basePrototypes = protonamespace.ProtoNamespace(
    {
        'PROTO': node.prototype,
        'sceneGraph': scenegraph.SceneGraph,
        'ROUTE': route.ROUTE,
        'NULL': node.NULL,
        'Script': script.Script,
    }
)
for key,value in basenodes.__dict__.items():
    try:
        if issubclass( value, node.Node ):
            basePrototypes[key] = value
    except:
        pass
    