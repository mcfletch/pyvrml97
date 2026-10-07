"""X3D profiles: the components, and their levels, each profile includes

Transcribed from ISO/IEC 19775-1:2023 (X3D 4.0), Annexes A to F, H and M,
"Components and levels" tables; the X3D 4.1 committee draft gives the same
tables. `specs/x3d/profiles.md` records the transcription. One set of tables
serves every version: a document of an X3D 3.x version is checked against
4.0's.
"""

from vrml import field, node
from vrml import fieldtypes  # noqa: F401 registers the field types used below
from vrml.x3d.scene import ComponentInfo


class Profile(node.Node):
    """A named set of components, each at a level"""

    PROTO = 'Profile'
    name = field.newField('name', 'SFString', 1, '')
    components = field.newField('components', 'MFNode', 1, list,
                                requiredTypes=ComponentInfo)

    def levels(self) -> "dict[str, int]":
        """Each component's level, by name"""
        return {item.name: item.level for item in self.components}


def _profile(name: str, components: "dict[str, int]") -> Profile:
    return Profile(name=name, components=[
        ComponentInfo(name=component, level=level)
        for component, level in components.items()
    ])


#: The highest level of each X3D 4.1 component: the Full profile's table
#: (Annex F), raised where X3D 4.1 declares a node at a higher level
#: (GaussianSplats, Shape 5, Text 2).
COMPONENTS = {
    'CADGeometry': 2, 'Core': 2, 'CubeMapTexturing': 3, 'DIS': 2,
    'EnvironmentalEffects': 4, 'EnvironmentalSensor': 3, 'EventUtilities': 1,
    'Followers': 1, 'GaussianSplats': 1, 'Geometry2D': 2, 'Geometry3D': 4,
    'Geospatial': 2, 'Grouping': 3, 'HAnim': 3, 'Interpolation': 5,
    'KeyDeviceSensor': 2, 'Layering': 1, 'Layout': 2, 'Lighting': 3,
    'NURBS': 4, 'Navigation': 3, 'Networking': 4, 'ParticleSystems': 3,
    'Picking': 3, 'PointingDeviceSensor': 1, 'Rendering': 5,
    'RigidBodyPhysics': 2, 'Scripting': 1, 'Shaders': 1, 'Shape': 5,
    'Sound': 3, 'Text': 2, 'TextureProjection': 2, 'Texturing': 4,
    'Texturing3D': 2, 'Time': 2, 'VolumeRendering': 4,
}

#: Other spellings of component names that documents use.
COMPONENT_ALIASES = {'H-Anim': 'HAnim'}

PROFILES = {
    # Annex A
    'Core': _profile('Core', {'Core': 1}),
    # Annex B, Table B.2
    'Interchange': _profile('Interchange', {
        'Core': 1, 'Time': 1, 'Networking': 1, 'Grouping': 1, 'Rendering': 3,
        'Shape': 1, 'Geometry3D': 2, 'Lighting': 1, 'Texturing': 2,
        'Interpolation': 2, 'Navigation': 1, 'EnvironmentalEffects': 1,
    }),
    # Annex C
    'Interactive': _profile('Interactive', {
        'Core': 1, 'Time': 1, 'Networking': 2, 'Grouping': 2, 'Rendering': 3,
        'Shape': 1, 'Geometry3D': 3, 'Lighting': 2, 'Texturing': 2,
        'Interpolation': 2, 'PointingDeviceSensor': 1, 'KeyDeviceSensor': 1,
        'EnvironmentalSensor': 1, 'Navigation': 1, 'EnvironmentalEffects': 1,
        'EventUtilities': 1,
    }),
    # Annex D
    'MPEG4Interactive': _profile('MPEG4Interactive', {
        'Core': 1, 'Time': 1, 'Networking': 2, 'Grouping': 2, 'Rendering': 1,
        'Shape': 1, 'Geometry3D': 2, 'Lighting': 2, 'Texturing': 1,
        'Interpolation': 2, 'PointingDeviceSensor': 1, 'EnvironmentalSensor': 1,
        'Navigation': 1, 'EnvironmentalEffects': 1,
    }),
    # Annex E
    'Immersive': _profile('Immersive', {
        'Core': 2, 'Time': 1, 'Networking': 3, 'Grouping': 2, 'Rendering': 3,
        'Shape': 2, 'Geometry3D': 4, 'Geometry2D': 1, 'Text': 1, 'Sound': 1,
        'Lighting': 2, 'Texturing': 3, 'Interpolation': 2,
        'PointingDeviceSensor': 1, 'KeyDeviceSensor': 2, 'EnvironmentalSensor': 2,
        'Navigation': 2, 'EnvironmentalEffects': 2, 'Scripting': 1,
        'EventUtilities': 1,
    }),
    # Annex F: every component at its highest level.
    'Full': _profile('Full', COMPONENTS),
    # Annex H
    'CADInterchange': _profile('CADInterchange', {
        'Core': 1, 'Networking': 2, 'Grouping': 1, 'Rendering': 4, 'Shape': 2,
        'Lighting': 1, 'Texturing': 2, 'Navigation': 3, 'Shaders': 1,
        'CADGeometry': 2,
    }),
    # Annex M
    'MedicalInterchange': _profile('MedicalInterchange', {
        'Core': 1, 'Time': 1, 'Networking': 2, 'Grouping': 3, 'Rendering': 5,
        'Shape': 3, 'Geometry3D': 2, 'Geometry2D': 2, 'Text': 1, 'Lighting': 1,
        'Texturing': 2, 'Interpolation': 2, 'Navigation': 3,
        'EnvironmentalEffects': 1, 'EventUtilities': 1, 'Texturing3D': 2,
        'VolumeRendering': 4,
    }),
}
