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

### The TimeSensor follows 19775-1 8.4.1 while it runs

A `startTime` set while it is active is dropped; `loop` and `cycleInterval`
are read at each advance; `cycleTime` is the time the cycle began; the last
`time` is the time it stopped.
