"""VRML97 nodes for volumetric tree rendering

Provides node definitions for procedural tree generation using
space colonization algorithm and volumetric rendering.
"""
from vrml.vrml97 import nodetypes
from vrml import node, field


class TreeNode(node.Node):
    """Single node in tree skeleton

    Represents a point in the tree structure with parent/child
    relationships and branch radius information.
    """
    PROTO = 'TreeNode'

    # Position in 3D space
    position = field.newField('position', 'SFVec3f', 1, [0.0, 0.0, 0.0])

    # Parent node (None for root)
    parent = field.newField('parent', 'SFNode', 1, node.NULL)

    # Child nodes (branches)
    children = field.newField('children', 'MFNode', 1, list)

    # Branch radius at this node
    radius = field.newField('radius', 'SFFloat', 1, 0.1)

    # Depth from root (0 = root)
    depth = field.newField('depth', 'SFInt32', 1, 0)


class TreeAttractor(node.Node):
    """Attractor point for space colonization algorithm

    Attractors guide branch growth - branches grow toward
    active attractors until they get close enough to "consume" them.
    """
    PROTO = 'TreeAttractor'

    # Position in 3D space
    position = field.newField('position', 'SFVec3f', 1, [0.0, 0.0, 0.0])

    # Whether this attractor is still active
    active = field.newField('active', 'SFBool', 1, True)


class TreeParameters(node.Node):
    """Parameters controlling tree generation

    Configures the space colonization algorithm and resulting
    tree structure.
    """
    PROTO = 'TreeParameters'

    # Core geometry - where the tree grows
    basePosition = field.newField('basePosition', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    trunkDirection = field.newField('trunkDirection', 'SFVec3f', 1, [0.0, 1.0, 0.0])
    boundingSize = field.newField('boundingSize', 'SFVec3f', 1, [4.0, 6.0, 4.0])

    # Space colonization algorithm parameters
    attractionDistance = field.newField('attractionDistance', 'SFFloat', 1, 2.0)
    killDistance = field.newField('killDistance', 'SFFloat', 1, 0.3)
    segmentLength = field.newField('segmentLength', 'SFFloat', 1, 0.2)

    # Crown shape and size
    attractorCount = field.newField('attractorCount', 'SFInt32', 1, 2000)
    crownShape = field.newField('crownShape', 'SFString', 1, 'sphere')  # sphere/cone/cylinder
    crownOffset = field.newField('crownOffset', 'SFFloat', 1, 2.0)
    crownRadius = field.newField('crownRadius', 'SFFloat', 1, 2.0)

    # Branch properties
    initialRadius = field.newField('initialRadius', 'SFFloat', 1, 0.15)
    radiusDecay = field.newField('radiusDecay', 'SFFloat', 1, 0.92)
    minRadius = field.newField('minRadius', 'SFFloat', 1, 0.02)


class VolumetricTree(nodetypes.Children, nodetypes.Rendering, node.Node):
    """Volumetric tree rendered via ray-marching

    Generates a tree structure using space colonization algorithm,
    voxelizes it into a 3D texture, and renders using ray-marching
    in a fragment shader.
    """
    PROTO = 'VolumetricTree'

    # Tree generation parameters (optional - uses defaults if not set)
    parameters = field.newField('parameters', 'SFNode', 1, node.NULL)

    # Convenience fields that override parameters if set
    # (allows setting common options directly on the node)
    basePosition = field.newField('basePosition', 'SFVec3f', 1, [0.0, 0.0, 0.0])
    trunkDirection = field.newField('trunkDirection', 'SFVec3f', 1, [0.0, 1.0, 0.0])
    boundingSize = field.newField('boundingSize', 'SFVec3f', 1, [4.0, 6.0, 4.0])
    crownShape = field.newField('crownShape', 'SFString', 1, 'sphere')
    crownRadius = field.newField('crownRadius', 'SFFloat', 1, 2.0)
    crownOffset = field.newField('crownOffset', 'SFFloat', 1, 2.0)
    attractorCount = field.newField('attractorCount', 'SFInt32', 1, 2000)

    # Material/appearance
    barkColor = field.newField('barkColor', 'SFColor', 1, [0.4, 0.25, 0.1])
    leafColor = field.newField('leafColor', 'SFColor', 1, [0.2, 0.5, 0.15])
    leafDensity = field.newField('leafDensity', 'SFFloat', 1, 0.3)
    leafClusterSize = field.newField('leafClusterSize', 'SFFloat', 1, 0.4)

    # Rendering quality
    volumeResolution = field.newField('volumeResolution', 'SFInt32', 1, 64)
    maxRaySteps = field.newField('maxRaySteps', 'SFInt32', 1, 128)
    rayStepSize = field.newField('rayStepSize', 'SFFloat', 1, 0.02)
    densityScale = field.newField('densityScale', 'SFFloat', 1, 1.0)

    # Random seed (0 = use random seed)
    seed = field.newField('seed', 'SFInt32', 1, 0)

    # Generated skeleton - can be saved/loaded with scene
    skeleton = field.newField('skeleton', 'MFNode', 1, list)
