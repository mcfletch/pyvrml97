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
reports ``x3d.Shape(geometry=x3d.Appearance())``. Constructors also take
``**fields``, for the fields an engine's implementation of a node adds; a
name the class does not have raises ``AttributeError`` when the node is
made. Reading a node field is typed ``Any``; it returns the node or ``NULL``.

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
(``FieldRename`` nodes in ``renamed``), the defaults it gives differently
(``FieldDefault`` nodes in ``defaults``, each value written as XML attribute
text) and the fields of its node types it does not have (``AbsentFields``
nodes in ``absent``). ``vrml.x3d.dialects.DIALECTS`` holds one per version, keyed by the
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
``defaults(nodeType)``, ``has_node(nodeType)`` and
``has_field(nodeType, name)``. A dialect is a node, so an
application can build its own.

``vrml.vrml97.basenodes`` exports the 53 VRML97 node classes, which are the
X3D classes of the same names; a VRML97 document is read with VRML97's
defaults where they differ.

Reading
-------

``vrml.x3d.load(path)`` and ``loads(data)`` read any encoding and return an
``X3DScene``::

    from vrml import x3d

    scene = x3d.load('world.x3d')      # .x3dv, .wrl, .json, .x3dz, .x3dvz, .wrz
    scene.profile, scene.version       # ('Immersive', '3.3')
    scene.getDEF('Gold').translation
    for problem in scene.problems:
        print(problem)                 # error line 12 column 5: ...

The encoding is recognised from the content, then from the file suffix; a
gzip-compressed document is decompressed first. A document of more than
2 GiB, compressed or not, is refused.

``X3DScene`` is a ``SceneGraph`` with the document's ``profile``,
``version``, ``components``, ``units``, ``meta``, ``imports``, ``exports``
and ``problems``. Reading does not stop at an error: each problem is a
``LoadProblem`` node with ``severity`` (``error``, ``warning`` or ``info``),
``line``, ``column`` (0 where the encoding gives none), ``message`` and the
``node`` concerned. ``load(path, strict=True)`` raises ``X3DLoadError`` at
the first error instead.

What reading does:

- A version's old field names and defaults are applied, so the scene holds
  X3D 4.1 names and values. A node type or field the document's version does
  not have is read, with a warning.
- ``UNIT`` statements (X3D 3.3 and later) scale each field in the unit's
  category, and its derived categories, into base units (metres, radians,
  kilograms, newtons). ``scene.units`` records them.
- ``PROTO``/``ProtoDeclare`` makes a prototype class registered on the
  scene. An ``EXTERNPROTO`` whose URL names a local file, relative to the
  document, is read from that file (any encoding, eight levels deep at
  most). Nothing is fetched over a network; ``extern_resolver`` lets an
  application supply prototypes from elsewhere. An unresolved
  ``EXTERNPROTO`` has its declared interface and no body, and is completed
  when ``builder.complete_extern_proto`` is given its definition.
- A ``Script`` keeps its declared fields, ``url`` and ``sourceCode`` and is
  not run.
- An ``IMPORT`` names a node an ``Inline``'s scene exports; routes to it
  wait in ``scene.pendingRoutes`` until ``builder.bind_imports`` is called
  with the loaded inline scene.

``prototypes=`` gives the node classes to build by X3D name, so an engine
reads documents into its own implementations of the nodes, and its
``X3DScene`` subclass under ``'X3DScene'``. A field the document leaves out
has the X3D declaration's default, also where the engine's class defaults it
otherwise for a node made in code; a field the document's version does not
have keeps the engine's default.

The readers are ``vrml.x3d.readers.xml`` (expat; external entities are not
read), ``json`` and ``classic`` (a SimpleParse grammar for ClassicVRML and
VRML97). Each turns its syntax into calls on one ``SceneBuilder``.

Behaviour
---------

The declarations carry fields; ``vrml.x3d.runtime`` gives some nodes their
behaviour. Setting an ``inputOnly`` event on a node calls its handler, and the
outputs the handler sets are forwarded along routes as any field change is:

- ``BooleanFilter``, ``BooleanToggle``, ``BooleanTrigger``, ``IntegerTrigger``
  and ``TimeTrigger``, which sends the time of its scene.
- ``BooleanSequencer`` and ``IntegerSequencer``: the value of the last key a
  ``set_fraction`` has reached, sent when that key changes; ``next`` and
  ``previous`` step through the keys, wrapping at the ends.
- ``KeySensor``: ``keyDown(name)`` and ``keyUp(name)`` send ``keyPress``,
  ``actionKeyPress`` (``runtime.ACTION_KEYS``), the modifiers' booleans and
  ``isActive``. Whoever has the keyboard calls them.
- ``StringSensor``: ``typed(character)`` adds to ``enteredText``; a return
  sends ``finalText``, and a backspace deletes where ``deletionAllowed``.
- ``PositionInterpolator2D`` and ``CoordinateInterpolator2D`` straight between
  keys; ``SplinePositionInterpolator``, ``SplinePositionInterpolator2D`` and
  ``SplineScalarInterpolator`` on X3D's Hermite spline, with ``keyVelocity``,
  ``normalizeVelocity`` and ``closed``; ``SquadOrientationInterpolator`` by
  spherical cubic interpolation; and ``EaseInEaseOut``. The arithmetic is
  ``vrml.x3d.interpolation``.
- The followers, ``vrml.x3d.followers``: each chaser reaches a destination
  ``duration`` seconds after it is set, along a smooth step, and each damper
  approaches it through ``order`` first-order filters of time constant
  ``tau``, resting within ``tolerance``. ``advance(now)`` moves one and sends
  its value; it answers whether the follower is still moving, and ``isActive``
  says the same. ``wake()`` is called when one starts moving, for whoever
  calls ``advance`` each frame.

The time a node is at is its scene's: ``vrml.x3d.timing.now_for(node)`` calls
the ``clock()`` of the scene the node is rooted in, and ``timing.clock``
(``time.time``) for a node in no scene with one. An engine gives its scene
class a ``clock`` method returning the time its frames run on, so a
``TimeTrigger``, a follower's change of destination and a frame's ``advance``
agree.

A document read with no ``prototypes=`` is built from these classes where they
exist; ``runtime.PROTOTYPES`` maps them by name for merging with an engine's.

Writing
-------

``vrml.x3d.dump(scene, path)`` writes a file in the encoding its suffix
names; ``dumps(scene, encoding='xml')`` returns the text::

    x3d.dump(scene, 'world.json')
    x3d.dump(scene, 'world.wrl')                  # VRML97
    x3d.dump(scene, 'world.x3dz')                 # gzip-compressed XML
    text = x3d.dumps(scene, encoding='classic', version='3.3')
    text = x3d.dumps(scene, canonical=True)

``encoding`` is ``xml``, ``classic`` or ``json``. ``version`` is the VRML or
X3D version to write: ``'2.0'`` (VRML97, the ``classic`` encoding only) or
``'3.0'`` to ``'4.1'``; the scene's own version where not given, and 4.1 for
a VRML97 scene written as XML or JSON. A ``.wrl`` or ``.wrz`` file is
written as VRML97.

What is written:

- Only fields whose values differ from the target version's defaults, under
  the version's field names. ``DEF``/``USE`` follow the graph: a node used
  more than once, or named by a route, is given a ``DEF`` name if it has
  none, and two nodes with one name are told apart with a suffix (``_2``).
- Prototypes, prototype bodies with their ``IS`` connections, ``EXTERNPROTO``
  interfaces and URLs, routes, ``IMPORT``/``EXPORT`` and the header
  statements. A version with ``UNIT`` statements has them written and its
  values written in those units; an earlier one has values in base units.
- A program's source as CDATA (XML), ``#sourceCode`` (JSON), the
  ``sourceCode`` field (ClassicVRML) or, for VRML97, an ``ecmascript:`` entry
  first in ``url``.
- Numbers in their shortest form at the field's precision, with no exponent
  below 10\ :sup:`16`.

A node type, field or field type the target version does not have raises
``X3DWriteError``, whose ``problems`` lists every one found; a field the
version lacks is written only if its value differs from the default.
Nothing is written to a file then. ``scene.problems`` is not written.

Classes of an engine's own
~~~~~~~~~~~~~~~~~~~~~~~~~~

A node class that subclasses an X3D node and adds fields names a metadata set
for them with a class attribute::

    class Glossy(x3d.Material):
        x3dExtension = 'Glossy'
        sheen = field.newField('sheen', 'SFFloat', 1, 0.0)

The writers put each added field whose value differs from its default in a
``MetadataSet`` of that name on the node's ``metadata``, one metadata node per
field, named after it: ``MetadataBoolean``, ``MetadataInteger``,
``MetadataDouble``, ``MetadataString``, or ``MetadataFloat`` with a vector's
components in order. A node value is a ``MetadataSet`` whose ``reference`` is
the node's type and whose entries are its own fields. MFNode fields are not
carried. The node's own metadata becomes the set's ``metadata``. A class that
adds fields and names no set raises ``X3DWriteError``.

Read with the class among ``prototypes=``, the builder sets the fields back
from the set and gives the node its own metadata again; an entry naming no
field is a warning in ``scene.problems``. Read without it, the set is the
node's metadata. ``vrml.x3d.extension`` holds the encoding.

A node with no X3D type of its own gives ``x3dEquivalent()``, which returns
the X3D node to write in its place: an image held in memory as an
``ImageTexture`` with a ``data:`` URL, say. A node reached more than once has
one equivalent, written once and used thereafter.

The XML writer orders attributes as X3D canonical form does (``DEF``,
``USE``, a ``containerField`` the reader would not infer, then
alphabetically) and delimits MFString attributes with single quotes.
``canonical=True`` adds the DTD and the schema attributes. Written XML
validates against the X3D 4.1 XML Schema.

Validating
----------

``vrml.x3d.validate(scene, profile=None)`` returns a list of
``LoadProblem`` nodes for the scene's problems against the X3D model: a value outside its field's range, a value
outside a closed enumeration, and a node whose component level the profile
and ``COMPONENT`` statements do not give. It is separate from reading, which
does none of these checks.

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
