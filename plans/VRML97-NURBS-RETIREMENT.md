# VRML97 NURBS: one implementation, and worlds that load

Status: phase 1 built 2026-10-10, uncommitted. Phases 2 to 4 wait on the
decision recorded under "After phase 1". Recorded 2026-10-10.

Two NURBS implementations exist. `vrml.vrml97.nurbs` declares seven VRML97
extension nodes, and `OpenGLContext.scenegraph.nurbs` draws them with its own
tessellator and its own GL code. `vrml.x3d.nodes` declares the thirteen nodes
of X3D's NURBS component, and `OpenGLContext.scenegraph.nurbsx3d` draws them as
`PBRMesh` and `IndexedLineSet` through `nurbseval`.

This plan has two goals:

1. A VRML97 NURBS world is read into the X3D nodes, with the four fields X3D
   lacks carried as an `x3dExtension`. The VRML97 node classes and their
   renderer are then removed.
2. Published VRML97 NURBS worlds draw. Today they load without an exception
   and draw no NURBS geometry.

Goal 2 is independent of goal 1 and is the smaller change, so it is phase 1.

## Probe of published content

Twelve samples from
<https://www.bitmanagement.com/developer/contact/nurbs/examples.htm> were read
through `OpenGLContext.loaders.vrml97.VRML97Handler.parse` on 2026-10-10
(openglcontext and pyvrml97 `develop`).

| Sample | NURBS nodes | Result |
|---|---|---|
| `nurbscurve.wrl` | 1 `NurbsCurve` | empty prototype instance |
| `animated_patch.wrl` | 1 `NurbsSurface` | empty prototype instance, Script not run |
| `ci_animated_patch66.wrl` | 1 `NurbsSurface` | empty prototype instance |
| `head.wrl` | 3 `NurbsSurface` | empty prototype instances |
| `parfum.wrl` | 2 `NurbsSurface` | empty prototype instances |
| `4ducks.wrl` | 13 `NurbsSurface` | empty prototype instances, Script not run |
| `sizetest/nrbduck_0.wrl` | 3 `NurbsSurface` | empty prototype instances |
| `3dsmax/nrbduck.wrl` | 3 `NurbsSurface` | empty prototype instances |
| `3dsmax/jack.wrl` | 4 `NurbsSurface` | empty prototype instances |
| `3dsmax/stingray.wrl` | 1 `NurbsSurface` | empty prototype instance |
| `x3d/nurbs/examples/FredTheBunny.wrl` | 20 `NurbsSurface` | empty prototype instances |
| `ffd/deform_sphere.wrl` | 1 `NurbsSurface` | `Unknown node type CoordinateDeformer`, 2 dangling names |

Eleven of the twelve fail the same way. Each file opens with a declaration of
this form:

```text
EXTERNPROTO NurbsSurface [ field SFInt32 uDimension ... ]
[ "urn:inet:blaxxun.com:node:NurbsSurface",
  "nurbs.wrl#NurbsSurface",
  "http://www.blaxxun.com/vrml/protos/nurbs.wrl#NurbsSurface" ]
```

`SceneBuilder.end_proto` (`vrml/x3d/builder.py`) registers the declared name in
the document's scope, where it takes precedence over the vocabulary's
`NurbsSurface`. `ExternPrototypes.__call__` (`vrml/x3d/files.py`) then tries
each URL as a file. The URN names no file, `nurbs.wrl` is not beside the
document, and the engine's `ContainedPrototypes` does not read from another
origin. The reader reports one warning, "EXTERNPROTO NurbsSurface: none of ...
could be read", and every `NurbsSurface` in the file is an instance of a
prototype with no body.

A world that names `NurbsSurface` with no EXTERNPROTO is built from the
engine's class and draws (`openglcontext/tests/wrls/nurbscurve.wrl`).

The URN is the first URL in each list. It tells a browser that has the node
built in to use its own, and the file URLs are the fallback for a browser that
does not.

Three other failures appear in the probe and are outside this plan:

- `Script` nodes with `javascript:` bodies are kept and not run, which is the
  decision recorded in `openglcontext/plans/X3D-SUPPORT.md`.
- `CoordinateDeformer` has no class here, and X3D has no such node.
- Textures the samples name by relative URL were not downloaded.

## What the VRML97 nodes have that X3D's do not

| VRML97 | X3D | Difference |
|---|---|---|
| `NurbsSurface` | `NurbsPatchSurface` | `controlPoint` is `MFVec3f`; X3D holds a `Coordinate` node and adds `uClosed`, `vClosed` |
| `TrimmedSurface` | `NurbsTrimmedSurface` | VRML97 wraps a `surface` node; X3D carries the surface fields itself |
| `NurbsCurve` | `NurbsCurve` | `controlPoint` is `MFVec3f`; X3D adds `closed` |
| `NurbsCurve2D` | `NurbsCurve2D` | `MFVec2f` against `MFVec2d`; X3D adds `closed` |
| `Polyline2D` (`point`) | `ContourPolyline2D` (`controlPoint`) | renamed; X3D's `Polyline2D` is a Geometry2D node |
| `Contour2D` | `Contour2D` | X3D adds `addChildren`, `removeChildren` |
| `NurbsGroup` | `NurbsSet` | `NurbsGroup` holds and draws children; `NurbsSet` holds geometry and draws nothing |

Four fields have no X3D counterpart:

- `color` (`MFColor`) on `NurbsSurface` and `NurbsCurve`: one colour per control
  point, evaluated through the basis. Whether the VRML97 amendment declares it,
  or the engine added it, is to be confirmed in step 1.1.
- `ccw` (`SFBool`) on `NurbsSurface`. The blaxxun declaration includes it, and
  `animated_patch.wrl` sets `ccw FALSE`.
- `geometryType` (`SFString`), the engine's own: `"polygon"` fills, `"edge"` and
  `"patch"` draw the triangles as lines.
- `sampling` (`SFNode`), the engine's own: a `NurbsToleranceSample` or
  `NurbsDomainDistanceSample`, each of which answers a rate in intervals per
  unit of knot range.

The VRML97 renderer does not read `uTessellation` or `vTessellation`. Every
sample above sets them. `nurbseval.segments` applies X3D's rule for them, so
the samples get their authored tessellation once they are drawn by the X3D
classes.

## Sources

The node interfaces and their semantics come from two places, neither
copyleft:

- ISO/IEC 14772-1:1997/Amd 1:2003, which standardises the NURBS nodes.
- The `EXTERNPROTO` declarations in the published files, which are the
  interface each world expects.

No browser's source is read. If a behaviour can only be settled that way,
`CLEAN-ROOM.md` applies.

The Bitmanagement samples are not ours to redistribute. Fixtures in the
repositories are written here, in the same dialect. The published samples are
read by an opt-in corpus test that downloads them, as
`pyvrml97/tests/test_x3d_corpus.py` does for X3D.

## Phase 1: known EXTERNPROTO references read as the standard's nodes

pyvrml97 only. No node class changes.

Vendors published prototype files for nodes that a standard later adopted, and
worlds name those files by URN and by URL. The declarations are precursors of
the standard's nodes: the same node under an earlier interface. The files are
on other origins, several of which no longer answer, and the engine's
`ContainedPrototypes` reads from the document's own origin only.

A table of known references maps each one to the node that became of it. A
reference is matched as text and is never fetched, so the read policy is
unchanged and a load makes no request it would not have made before.

1.1. Read Amendment 1 and record in `pyvrml97/specs/` the facts this plan
relies on: each node's fields, types, access and defaults, the tessellation
rule, and what the standard says of URNs in an EXTERNPROTO URL list. Record
each reference seen in published content with the file it was seen in. From
the probe:

- `urn:inet:blaxxun.com:node:<Name>`
- `urn:inet:bitmanagement.de:node:<Name>`
- `http://www.blaxxun.com/vrml/protos/nurbs.wrl#<Name>`

1.2. `vrml.x3d.knownprotos` (new): the table and its lookup. An entry holds:

- the reference, as a URN prefix or a URL, with the node name taken from the
  rest of the URN or from the `#name`;
- the node it is read as, by name in the load's `prototypes`;
- the fields the precursor names differently, and the fields it has that the
  node lacks, each with what becomes of the value.

Entries are nodes, as `vrml.x3d.dialect`'s are, so the table copies, writes
out and is extended by an application with entries of its own. The lookup
takes an EXTERNPROTO's URL list and answers the first entry any URL matches.

1.3. Which URL decides. A known reference anywhere in the list is used, ahead
of a file URL earlier in the list that could be read. The file a world ships
beside itself for this purpose is the fallback for a browser without the node:
`head.wrl`'s draws the control net as an `IndexedLineSet`. A relative file
name (`nurbs.wrl#NurbsSurface`) is never a known reference, since any world
may hold a file of that name.

1.4. `SceneBuilder.end_proto` asks the table before the `extern_resolver`.
When an entry answers, the scope maps the declared name to the entry's class
and no `PENDING_PROTOTYPES` entry is made. The load reports, at `info`, the
reference and the node it was read as. The declaration's interface is compared
with the entry:

- A declared field the entry does not account for is a warning that names it.
- A type difference is a warning.
- An access difference (`field` against `exposedField`) is not reported.
  `FredTheBunny.wrl` declares `uTessellation` as `field` and the other samples
  declare it as `exposedField`.

1.5. Precursor fields. The page that publishes `FredTheBunny.wrl` says its
`closedSurface` field was removed for Contact. A Maya export that keeps it
names a field the VRML97 node lacks and X3D's `uClosed` and `vClosed` cover.
The entry is where that correspondence is stated, once step 1.1 has found
what the field means in the files that carry it.

1.6. What an entry names over the phases. In this phase an entry names the
vocabulary's node of the same name, which for a VRML97 load is the engine's
VRML97 class. After phase 3 it names the X3D node, through the same
translation a VRML97 world's own `NurbsSurface` takes, so a precursor
declaration and the amendment's node are read by one path.

1.7. Survey. NURBS is the family the probe covers. Others that published
prototype files ahead of a standard, each to be confirmed from published
worlds before it gets an entry:

- GeoVRML 1.0, whose nodes became X3D's Geospatial component.
- H-Anim 1.1, whose nodes became X3D's HAnim component.
- The blaxxun and Bitmanagement Contact extension nodes beyond NURBS.
- ParallelGraphics Cortona extension nodes.

A family gets entries when a world that uses it is in hand and the standard
has a node its values can be read into. A reference with no entry behaves as
it does today.

1.8. Tests, red first:

- A fixture with the blaxxun-form declaration builds `NurbsSurface` from the
  vocabulary class, with no "could be read" warning.
- The `http://www.blaxxun.com/...` URL alone, with no URN, builds the same
  class, and the resolver's `read` is not called.
- A known reference listed after a readable local file is used ahead of it.
- A URN with an unknown prefix, a known prefix with an unknown node name, and
  a relative `nurbs.wrl#NurbsSurface` all go on to the resolver.
- A declaration with a field the entry does not account for reports it once.
- An entry an application adds is matched.
- In openglcontext: the fixture's surface has a mesh with more than zero
  triangles, and a capture of it is not the background colour.

1.9. Documentation: `pyvrml97/docs/x3d.rst` (prototypes, and the table with
how to add an entry),
`openglcontext/docs/vrml97.rst` and `openglcontext/docs/loading.rst`.

After phase 1 the eleven samples build engine NURBS nodes. They are still
drawn by the VRML97 renderer, at the default sampling.

## After phase 1

Built: `vrml/x3d/knownprotos.py`, the lookup in `SceneBuilder.end_proto`,
`tests/test_x3d_knownprotos.py`, `specs/vrml97/known-prototype-references.md`,
and one case in `openglcontext/tests/unit/test_vrml97_loading.py`.

Differences from the steps above:

- An entry holds its references and the node's name. Field renames and
  dropped fields (1.2, 1.5) are not built: no world in hand needs one.
- A declared field the node lacks, or holds as another type, leaves the
  declaration to the resolver with a warning (1.4 said warn and use the node).
  X3D's own `NurbsCurve` holds `controlPoint` as a node, so a blaxxun
  declaration read with the plain X3D vocabulary must not be given it.
- Step 1.1's reading of Amendment 1 is not done. The ten node names are
  entered from the amendment's list as remembered, and two were seen in
  published references.
- The opt-in corpus test is not built.

Three defects of the VRML97 renderer showed in the first captures and were
fixed in `openglcontext` the same day, since the samples could not be judged
with them in place:

- `NurbsSurface`, `TrimmedSurface` and `NurbsCurve` had no `boundingVolume`,
  so the viewer framed a world as though they were not in it. Each now
  answers the box of its control points.
- A surface that could not be tessellated logged its error on every frame
  (677 lines in one capture of `ci_animated_patch66.wrl`). Each message is
  now logged once per node (`nurbstess.report`).
- `ci_animated_patch66.wrl` declares a 6 by 6 net and gives 64 control
  points, in the node and in each key of its `CoordinateInterpolator`. The
  first 36 are a regular 6 by 6 grid. A surface with more points than its
  dimensions name now uses the first of them, with a warning.

The eleven samples after those fixes, through `oglc-view --no-cameras` at
640x480:

| Sample | Drawn |
|---|---|
| `nurbscurve.wrl` | the curve and its markers |
| `head.wrl` | the head |
| `parfum.wrl` | the bottle and its stopper |
| `3dsmax/nrbduck.wrl` | the duck, lit |
| `sizetest/nrbduck_0.wrl` | the duck, black |
| `4ducks.wrl` | the floor and the ducks |
| `3dsmax/jack.wrl` | the pumpkin |
| `animated_patch.wrl` | the patch, unanimated (Script not run) |
| `ci_animated_patch66.wrl` | the patch, animated |
| `FredTheBunny.wrl` | the bunny, near black |
| `3dsmax/stingray.wrl` | nothing in the framed view; the ray, black, from `--eye 6.5,0.3,6 --look-at 6.5,0.3,0.1` |

Still open in the VRML97 renderer:

- `uTessellation` and `vTessellation` are not read. `stingray.wrl`'s knots
  run 0 to 1, so a 32 by 43 net is drawn from 30 intervals each way.
- Three samples draw black or near black. Not diagnosed: the normal sense
  under `ccw`, and textures that were not downloaded, are the candidates.
- `stingray.wrl` is outside the viewer's framed view. Not diagnosed.
- `ci_animated_patch66.wrl` gives ten knots for six points at order 3. The
  degree is taken from the knot count, so it draws as a cubic.

### CoordinateDeformer

Built 2026-10-10 in `openglcontext/OpenGLContext/scenegraph/coordinatedeformer.py`,
from the published node reference
(`openglcontext/specs/vrml97-nurbs-coordinatedeformer.md`). It answers open
question 5 for this node: it is the engine's own, with no X3D counterpart.

`ffd/deform_222_grid.wrl` and `ffd/deform_sphere.wrl` load with no error. Both
leave the lattice to a Script, so both are drawn undeformed: the statue from
its `IndexedFaceSet`, the sphere from the `NurbsSurface` the output
`Coordinate` is routed to. Neither is animated.

`oglc-deformer` (`openglcontext/OpenGLContext/bin/deformer_demo.py`) shows the
node deforming: a column whose lattice a `CoordinateInterpolator` moves, and a
block an `inputTransform` carries through a fixed lattice. Writing it found
one defect, an input transform that moves nothing, which is fixed.

The node is in an X3D component of the engine's own, `OpenGLContext`, through
`vrml.x3d.components` (new): X3D documents of every encoding name it and the
writers write it. The demo is X3D in the ClassicVRML encoding, and both of
its shapes are `NurbsPatchSurface` nodes whose `controlPoint` is a deformer's
output `Coordinate`.

Frame time of the demo while animating, 1280x720, on the Radeon 8060S:

| Version | ms per frame |
|---|---|
| two `IndexedFaceSet` meshes, 1,248 quads | 220 |
| two `NurbsPatchSurface` nodes | 22 |
| with the evaluator's products as matrix multiplies (`opengl_extrusions`) | 11 |
| with one tessellation a surface a frame | 8 |

The 220 ms is `ifscompiler.expandedArraysAndSources`: about 100 ms to compile
1,000 quads, a `Vertex` object and a tessellator call for each polygon and a
Python loop for the crease-angle normals. It runs whenever a face set's
coordinates are set. It is not fixed. A NumPy path for face sets of triangles
and quads with generated normals is designed: planar convex quads and
non-planar quads are both split a-b-c, a-c-d by the present compiler, and
collinear triangles are dropped, so the arrays can be built without the
per-polygon objects.

Five rules are the engine's, where the reference is silent: the control point
order along w, the knot count, a parameter outside the knots, fields that
describe no volume, and when the input transform applies. The spec file lists
them.

## Phase 2: the extension fields on the X3D classes

openglcontext, with one decision in pyvrml97.

2.1. `SurfaceDrawn` and `nurbsx3d.NurbsCurve` set
`x3dExtension = 'OpenGLContext'` and declare:

| Field | Type | Default | On |
|---|---|---|---|
| `ccw` | `SFBool` | `TRUE` | patch and trimmed surfaces (swept and swung have X3D's own) |
| `color` | `MFColor` | `[]` | surfaces and `NurbsCurve` |
| `geometryType` | `SFString` | `"polygon"` | surfaces |
| `samplingRate` | `SFVec2f` | `0 0` | surfaces |

`samplingRate` is intervals per unit of knot range along u and v. A component
of 0 means that direction uses its tessellation field. It replaces the
`sampling` node: `NurbsDomainDistanceSample` is two rates, and
`NurbsToleranceSample` reduces to one rate, 150 divided by the tolerance and
held between 20 and 100.

A node-valued extension field is rebuilt by looking its type up in the X3D
vocabulary, and the two sampling classes are not in it, so a `sampling` field
would restore as `NULL`. `PhysicalMaterial.reflector` holds a
`PlanarReflector`, which is also outside the vocabulary. A round-trip test for
it belongs in this phase; if it fails, the fix is in `extension.node_from` and
the vocabulary, and it is separate from NURBS.

2.2. `nurbseval`: colours evaluated through the surface's and the curve's
basis, returned with the positions. `ccw` reverses the triangle winding and
the normals, as `nurbseval.swept` does.

2.3. Drawing:

- `color` becomes the mesh's `COLOR_0` array, and the `IndexedLineSet`'s
  `color` for a curve.
- `geometryType` of `"edge"` or `"patch"` draws the tessellation's edges. The
  decision to make: an `IndexedLineSet` of the edges, or a line mode on
  `PBRMesh`. The first needs no change to the mesh class.
- `samplingRate` is applied in `SurfaceDrawn.buildMesh` before the `NurbsSet`
  scale and the distance level.

2.4. Tests: `check_memo_inputs` over each new field, a mirrored-geometry case
for `ccw`, a still-frame case, and an extension round trip through the XML and
ClassicVRML writers for all four fields.

2.5. Documentation: `openglcontext/docs/nurbs.rst` and
`openglcontext/docs/x3d.rst`.

## Phase 3: VRML97 names read as the X3D nodes

3.1. Where the translation lives. A VRML97 name does not map to an X3D node by
renaming fields: `controlPoint` changes from a value to a node, and
`TrimmedSurface` folds a child into itself. `vrml.x3d.dialect` has
`FieldRename`, `FieldDefault`, `ContainerDefault` and `AbsentFields`, none of
which does that. Two options:

1. A dialect entry that names a function, called by the builder when the node
   is closed, which answers the node to put in its place.
2. Engine classes with the VRML97 names that subclass the X3D classes and
   convert in their field setters.

Option 1 is recommended. It keeps one class per node in the scene, so the
writers, the editor's control net and `meshArrays()` see X3D nodes only.
Option 2 leaves seven node types in the registry, which is what this plan
removes.

3.2. The translations:

| VRML97 | Becomes |
|---|---|
| `NurbsSurface` | `NurbsPatchSurface`; `controlPoint` wrapped in a `Coordinate`; `ccw`, `color` carried by the extension |
| `NurbsCurve` | `NurbsCurve`; `controlPoint` wrapped in a `Coordinate` |
| `NurbsCurve2D` | `NurbsCurve2D`; points widened to doubles |
| `Polyline2D` in a `Contour2D` | `ContourPolyline2D`; `point` to `controlPoint` |
| `Contour2D` | `Contour2D` |
| `TrimmedSurface` | `NurbsTrimmedSurface` with the `surface` node's fields and the contours |
| `NurbsGroup` | a `Group` of its children, and a `NurbsSet` of their NURBS geometry carrying `tessellationScale` |

A `ROUTE` to `NurbsSurface.controlPoint` in a VRML97 world is redirected to the
`Coordinate`'s `point`. `ci_animated_patch66.wrl` drives the control points
this way from a `CoordinateInterpolator`.

3.3. `TrimmedSurface.surface` holding a `USE`. The trimmed surface gets its own
copy of the fields and shares the `Coordinate` node, so an animated control net
moves both. The `DEF` name stays with the untrimmed `NurbsPatchSurface`.

3.4. Writing VRML97. `vrml.x3d.writers.classic` at version '2.0' applies the
same table in reverse, so a scene read from VRML97 writes the VRML97 names. A
field with no VRML97 form (`uClosed`, `closed`) set to other than its default
is reported as a write problem.

3.5. Tests: each row of 3.2 from a fixture, the route redirection, the shared
`USE`, a VRML97 read and write that gives the same text, and a differential
test that the VRML97 fixture and its X3D equivalent build equal meshes.

## Phase 4: removal

4.1. Callers of the VRML97 classes move to the X3D classes:

- `OpenGLContext/scenegraph/teapot_nurbs.py`
- `OpenGLContext/edit/controlnet.py`
- `tests/molehill.py`, `tests/molehill_edit.py`, `tests/lod_demo.py`,
  `tests/nurbsobject.py`, `tests/teapot_nurbs.py`
- `tests/unit/`: `test_nurbs_lod.py`, `test_nurbs_render_gl.py`,
  `test_nurbs_vao_caching_gl.py`, `test_nurbstess.py`, `test_meshdata.py`,
  `test_mirrored_geometry.py`, `test_still_frames.py`, `test_vrml97_loading.py`

`molehill.py` is a tutorial. Its code and its commentary change together.

4.2. Removed from openglcontext: the node classes in `scenegraph/nurbs.py`,
`nurbssampling.py`, the node classes in `nurbstrim.py`, the eight `Node(...)`
registrations in `OpenGLContext/__init__.py`, and the `X3D_ONLY` entries in
`loaders/x3d.py` that exist because the registry gave four names to the
VRML97 classes. `nurbstess.py` is removed if nothing reads it after 4.1; the
differential test of 3.5 runs before that.

4.3. Removed from pyvrml97: `vrml/vrml97/nurbs.py` and its cases in
`tests/test_node_definitions.py`.

4.4. Public names. `OpenGLContext.scenegraph.nurbs.NurbsSurface` and the
`basenodes` names are public. Decision for the maintainer: remove them in the
release that lands this, or keep the module for one release as functions that
build the X3D nodes from the VRML97 keyword arguments and warn.

4.5. Reference images for `nurbsobject.py`, `teapot_nurbs.py`, `molehill.py` and
`lod_demo.py` are compared before any baseline is replaced. A surface that sets no
tessellation moves from a rate of 30 per knot unit to X3D's default count, so
its triangles change.

4.6. Documentation: `openglcontext/docs/nurbs.rst` rewritten around the X3D
nodes, `docs/vrml97.rst`, `docs/structure.rst`, the directory map in
`openglcontext/CLAUDE.md`, and both projects' release notes.

## Open questions

1. `color` in Amendment 1 (step 1.1). If the standard has no such field it
   stays an engine extension and nothing else changes.
2. `geometryType` drawn as an `IndexedLineSet` or as a mesh line mode (2.3).
3. Dialect function or subclass for the translation (3.1).
4. Removal or one release of forwarding for the public names (4.4).
5. `CoordinateDeformer`, `NurbsTextureSurface` and VRML97's
   `NurbsPositionInterpolator`. Amendment 1 has all three. The interpolator and
   the texture surface have X3D counterparts and fit the table in 3.2.
   `CoordinateDeformer` has none; it is built (see "CoordinateDeformer").

6. The known-reference survey (1.7): which families get entries, and in what
   order. Each needs published worlds to test against.

## Gates

`tools/preflight.py pyvrml97` after phase 1, `tools/preflight.py pyvrml97
openglcontext` after each later phase, and the opt-in corpus test over the
twelve samples with the count of NURBS nodes that have a mesh.
