X3D in PyVRML97
===============

``vrml.x3d`` is the X3D 4.1 vocabulary as PyVRML97 nodes. VRML97 and the
earlier X3D versions are dialects of that one vocabulary, so a node class
serves every version: ``isinstance(node, x3d.Transform)`` is true whatever
file the node came from.

The vocabulary
--------------

``vrml.x3d.nodes`` declares the 266 concrete X3D 4.1 nodes and the abstract
types they are built from::

    from vrml.x3d import nodes as x3d

    shape = x3d.Shape(
        appearance=x3d.Appearance(material=x3d.PhysicalMaterial(
            baseColor=(1.0, 0.766, 0.336), metallic=1.0, roughness=0.25,
        )),
        geometry=x3d.Sphere(radius=1.0),
    )
    gold = x3d.Transform(DEF='Gold', translation=(-2.2, 0, 0), children=[shape])

Each class says where it sits in the specification:

``PROTO``
    The node's X3D name.
``COMPONENT``
    The component and level that introduce it, for example
    ``('Grouping', 1)``.
``CONTAINER_FIELD``
    The parent field the XML encoding puts it in when the file does not say.

Abstract types (``X3DChildNode``, ``X3DGeometryNode``, ...) are classes, and
each also inherits the matching ``vrml.vrml97.nodetypes`` marker
(``Children``, ``Geometry``, ``Light``, ...), so code that tests for a marker
accepts every X3D node of that kind, and a node that is not an X3D node but
carries the marker is accepted where X3D accepts the abstract type.

A field's declaration carries its X3D interface:

``accessType``
    ``initializeOnly``, ``inputOutput``, ``inputOnly`` or ``outputOnly``.
``minimum``, ``maximum``, ``minimumExclusive``, ``maximumExclusive``
    The range the specification gives, or ``None``.
``choices``, ``choicesOpen``
    An enumerated string field's values, and whether others are allowed.
``requiredTypes``
    On node fields, the node types the field holds. Setting any other type
    raises ``ValueError``.

Fields named by a Python keyword (the lights' ``global``) are read with
``getattr(light, 'global')`` and set with ``Light(**{'global': True})``.

``vrml/x3d/nodes.pyi`` types every constructor and field, so a type checker
reports ``x3d.Shape(geometry=x3d.Appearance())`` and a misspelt field name.

Field types
-----------

X3D's field types are all registered: VRML97's, plus ``SFDouble`` and
``MFDouble`` (float64), ``SFColorRGBA`` and ``MFColorRGBA`` (float32, clamped
to 0..1), ``MFBool`` (a NumPy bool array), ``MFImage`` (a list of ``SFImage``
arrays), and ``SFQuaternion``/``MFQuaternion``. Single-precision vectors are
float32 arrays and double-precision ones (``SFVec3d``, ``MFVec2d``, ...)
float64.

``vrml.x3d.codecs`` reads and writes field values as X3D XML attribute text:
``decode('MFVec3f', '0 0 0, 1 1 1')`` and ``encode('MFString', ['A', 'B'])``.

Dialects
--------

A ``Dialect`` node lists what one version says differently from X3D 4.1: the
node types it has (``nodeTypes``), the fields it names differently
(``FieldRename`` nodes in ``renamed``) and the defaults it gives differently
(``FieldDefault`` nodes in ``defaults``, each value written as XML attribute
text). ``vrml.x3d.dialects.DIALECTS`` holds one per version, keyed by the
version a document's header gives: ``'2.0'`` (VRML97), ``'3.0'`` to
``'3.3'``, ``'4.0'`` and ``'4.1'``.

============  ===========================================  ==================================
From          Renamed fields                               Different defaults
============  ===========================================  ==================================
VRML97        ``Collision.collide``, ``LOD.level``,        ``SpotLight.beamWidth`` and
              ``Switch.choice``                            ``cutOffAngle``,
                                                           ``NavigationInfo.type``,
                                                           ``CylinderSensor.diskAngle``
X3D 3.x       ``ComposedCubeMapTexture.back`` and its      ``SpotLight.beamWidth``; the axes
              five sides, ``ParticleSystem.colorRamp``     of four RigidBodyPhysics joints
              and ``texCoordRamp``,
              ``Layer.isPickable``, ``LoadSensor.watchList``,
              ``DISEntityManager.mapping``
X3D 4.0       none                                         none (4.1 adds seven node types)
============  ===========================================  ==================================

The old names are aliases on the X3D classes: ``lod.level`` reads and writes
``lod.children``. An alias is not a field and ``getFields`` does not list it.

``Dialect.tables()`` gives the lookups a reader or writer uses for one
document: ``current_name(nodeType, name)``, ``dialect_name(nodeType, name)``,
``defaults(nodeType)`` and ``has_node(nodeType)``. A dialect is a node, so an
application can build its own.

``vrml.vrml97.basenodes`` exports the 53 VRML97 node classes, which are the
X3D classes of the same names; a VRML97 document is read with VRML97's
defaults where they differ.

Regenerating the vocabulary
---------------------------

``vrml/x3d/nodes.py``, ``nodes.pyi`` and ``dialects.py`` are generated by
``tools/generate_x3d.py`` from Web3D's X3D Unified Object Model (X3DUOM) for
each version. The X3DUOM files are downloaded from Web3D's x3d Subversion
repository at the revision ``REVISION`` names, cached under the user's cache
directory, and checked against the SHA-256 digests in ``SOURCES``.

To move to a newer X3DUOM: change ``REVISION`` and the digests, run
``tools/generate_x3d.py``, review the diff, and run
``tools/generate_x3d.py --report`` for the version differences a dialect
cannot record (fields removed without a confirmed new name, changed types).
A field the X3DUOM records as removed beside a new field of the same type is
a rename only once it is confirmed against the specification and added to
the generator's ``RENAMES`` table.

``tox -e x3d-generated`` regenerates into a temporary directory and fails if
the checked-in modules differ. It needs the network, so it is a check of its
own rather than part of the unit suite.
