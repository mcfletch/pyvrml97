"""VRML97 semantic node-types"""
from vrml import node

class Traversable( object ):
    """Traversable nodes (Nodes which have node attributes)
    """
class Grouping( Traversable ):
    """Grouping nodes (Nodes which group children together)
    """
    sensitive = 0
class Transforming( Grouping ):
    """Nodes which alter the transform matrix for children

    This is a fairly small set of types:

        Transform
        Billboard

    Billboard is not yet implemented, so there's
    only the one functional node in the type-set
    """

class Children( object ):
    """Children nodes (Nodes which can belong to a Grouping)
    """
    sensitive = 0


class Rendering( object ):
    """Rendering nodes (Shapes)
    """
class Geometry( object ):
    """Geometry nodes (Nodes which can appear in the geometry field of shapes)
    """
class Texture( object ):
    """Texture nodes
    """


class Sensor( object ):
    """Sensor nodes

    Note: All Sensors are also Children, though
        that isn't represented here.
    """
class PointingSensor( Sensor ):
    """Pointing-Device Sensor nodes
    """


class Bindable( object ):
    """Bindable nodes

    Note: All Bindables are also Children, though
        that isn't represented here.
    """
class Background( Bindable ):
    """Background nodes
    """
class Viewpoint( Bindable ):
    """Viewpoint nodes
    """
class NavigationInfo( Bindable ):
    """NavigationInfo nodes
    """
class Fog( Bindable ):
    """Fog nodes
    """

class Light( object ):
    """Light nodes
    """


class Interpolator( object ):
    """Interpolator nodes
    """
class TimeDependent( object ):
    """TimeDependent nodes
    """
class Auditory( object ):
    """Auditory nodes (nodes with produce sound)
    """
    