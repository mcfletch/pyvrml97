# PyVRML97 2.4.0

`vrml.x3d` reads and writes X3D 3.0 to 4.1 and VRML97 in every encoding, on
one vocabulary generated from Web3D's X3D Unified Object Model; see
[docs/x3d.rst](docs/x3d.rst). This page lists what changes for a program
written against 2.3.

## What changed for a program using this

### The VRML97 node classes are X3D's

`vrml.vrml97.basenodes` exports the X3D classes of the VRML97 names, so a node
built in code takes X3D 4.1's defaults where they differ from VRML97's:

| Field | 2.3 | 2.4 |
|---|---|---|
| `SpotLight.beamWidth` | 1.570796 | 0.589049 |
| `NavigationInfo.type` | `['WALK']` | `['EXAMINE', 'ANY']` |
| `DirectionalLight.global` | not a field | `False` |

A document read as VRML97 (`#VRML V2.0`) still gets VRML97's defaults: the
reader sets them where the document leaves a field out. A program that builds
nodes in code and wants VRML97's values sets them.

### `PointSet` has X3D's fields

`size`, `minSize`, `maxSize` and `attenuation` were pyvrml97's own and are
gone. X3D's `PointProperties`, in an `Appearance`'s `pointProperties`, carries
point size and attenuation; an engine that wants the old fields declares them
on its own `PointSet`, as OpenGLContext does.

### `nodetypes.Sensor` is a `Children`

A class that names both, `(nodetypes.Children, nodetypes.PointingSensor,
node.Node)`, has no consistent method resolution order. Name the sensor type
alone: `(nodetypes.PointingSensor, node.Node)`.

### A field set outside a cascade starts one

`vrml.event.announce` sends every field's `set` and `del` signals: within the
cascade under way, or in a new one where there is none. Every receiver of one
set, routes included, sees the same `vrml.event.current()`, so routes that part
and meet again reach the field where they meet once (ISO/IEC 19775-1,
4.4.8.3). Both builds of the field, and the compiled accelerator, send through
it; rebuild `vrml_accelerate` with this release.

### `SceneBuilder(prototypes=)` adds to the vocabulary

The classes given are laid over pyvrml97's own, so a node type an engine does
not supply keeps pyvrml97's behaviour (a `TimeSensor`, a `BooleanFilter`). A
type built from its bare declaration in such a read is reported once in
`scene.problems`, as `info`.

### `protofunctions.getField` returns a field or an event, and nothing else

`getField` is declared as returning `Field | Event`, and `getFields` as
returning a list of `Field`, or of `Event` when asked for events. A caller
that sets or reads a value narrows first, since an `Event` has no `fset`,
`fget` or `fhas`:

```python
declared = protofunctions.getField(node, name)
if isinstance(declared, field.Field):
    declared.fset(node, value)
```

A class attribute that is neither (a method, a property, a constant) raises
`AttributeError`, as an undeclared name does, where 2.3 returned the
attribute. An attribute that hides an inherited field of its name hides it
from `getField` too.

A value given to an event is refused: `Node(isActive=True)` raises
`TypeError`, and a VRML97 document that gives an event a value raises
`AttributeError` naming the event, the node type and the line.

`protoName(obj, value)` returns the name it set.

### The TimeSensor follows 19775-1 8.4.1 while it runs

A `startTime` set while it is active is dropped; `loop` and `cycleInterval`
are read at each advance; `cycleTime` is the time the cycle began; the last
`time` is the time it stopped.

### An `EXTERNPROTO` naming a known reference is the vocabulary's node

An `EXTERNPROTO` whose URLs include a reference in `vrml.x3d.knownprotos.KNOWN`
(the blaxxun and Bitmanagement URNs and URL for the VRML97 NURBS nodes) gives
the load's own class for that node where 2.3 gave a prototype with no body.
A program that tested such a node with `isinstance(node, PrototypedNode)`
finds the node class. See [docs/x3d.rst](docs/x3d.rst).

### `DialectTables.has_node` counts registered node types

A node class registered with `vrml.x3d.components.register` is a node type of
every X3D version from its `SINCE` on. A program that asked
`has_node('ItsOwnNode')` to tell its own nodes from X3D's gets `True` for a
registered one.

### `vrml.vrml200x` is removed

`vrml.x3d` reads the ClassicVRML encoding. A program that built a parser with
`vrml.vrml200x.parser.buildParser()` calls `vrml.x3d.files.load(path)` or
`loads(text)`, which return the scene.
