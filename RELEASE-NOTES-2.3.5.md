# PyVRML97 2.3.5

## What changed for a program using this

### `transformmatrix.orthoMatrix` is transposed

It answers the row-vector form now, matching `perspectiveMatrix`, the three
primitives beside it, and the module's own instructions: a point goes through
a matrix here as `dot( point, matrix )`. The previous form put the offset in
the last column, so a point through it landed the translation in `w`; a
centred box came out right and an off-centre one did not.

A caller that fed the result straight to `glLoadMatrixf` was relying on GL's
column-major upload to transpose it back. That caller now wants
`matrix.T` — or, better, one of the core-profile paths that take a row-vector
matrix.

### `Node.copy()` copies the whole subtree

A node's copy shared the nodes its fields pointed at, so writing to the copy's
child was writing to the original's. Each instance of a PROTO is a copy of the
prototype's body, so this was also why two instances of one prototype drew the
same thing: `Wheel { radius 2 }` beside `Wheel { radius 5 }` gave two wheels of
radius 5. A node reached twice in the original is still one node in the copy,
which is what DEF/USE and a prototype's IS wiring need.

### `NULL` compares and hashes as a value

`NullNode.__eq__` answered a three-way comparison — 0 for equal, which reads as
false, and -1 for anything else, which reads as true. `NULL == 42` was true and
`NULL == NullNode()` was false, and the class was unhashable. It now equals
another NULL, differs from anything that is not a node, and can be a dictionary
key.

### A field left at its default is no longer written

`arrays.safeCompare` is what the lineariser asks about every field it is about
to write, and it answered two questions wrongly. Two arrays were "the same"
when they shared a single element, and a list compared as a different type from
an array — which is the pair the question is usually about, since a node
declares its default as a list of numbers and stores its value as an array. So
no vector field ever looked like its default, and every one was written out.

A `Transform` with a translation set was written with all eight of its fields;
it is written with the one now. Files are shorter and read back the same. NULL
node fields go the same way, now that `NULL` compares as a value.

A program that read the output looking for a field it had not set will not find
it. That is what the format says, and what a file written by anything else
looks like.

### `del someNode.children[0]` removes the child

It announced the removal and left the child in the list. Only the slice form
deleted anything.

### A node appended to a scene learns which scene it is in

`scene.children.append(node)` left the node without a scene root, so `getProto`
and the DEF names did not reach it; only assignment to the whole field passed
the root down. Both do now.

## What a file can say that it could not

- **Every registered field type can be read.** `SFVec4f`, `SFVec2d`, `SFVec3d`,
  `SFVec4d`, `SFUInt32`, `SFArray32`, `MFVec4f`, `MFVec2d`, `MFVec3d`,
  `MFVec4d` and the four `MFMatrix` types had no reader; a file naming one
  raised. The four `SFMatrix` types were not registered at all, so a PROTO
  could not declare one.
- **A file that is a header and nothing else parses**, as does one whose last
  line is a comment.
- **A PROTO declared without a body can be written out.**

## What the writer gets right

- An **MFString** field is written as a list of strings rather than as a list of
  nodes. A node with a non-empty MFString — `Text`, `WorldInfo`, `Anchor`,
  `ImageTexture`, `Script`, `Inline` — was written with an opening bracket that
  was never closed and its next field swallowed inside it.
- An **EXTERNPROTO** reads back: its interface is written without values, which
  is what VRML97 has room for, and `externalURL` is no longer written as one of
  the fields the prototype declares.
- A **Script** is written as `DEF x Script` rather than `DEF x  Script`, and
  closed with a comment naming `x`.
- `Lineariser.linear( scene, skipProtos=... )` leaves the named prototypes out.
  The argument was accepted and dropped. Name them by name, by the prototype
  itself, or as the keys of a mapping such as a scene graph's `protoTypes`;
  their instances are still written, which is how a caller writes a fragment
  for a file that already declares them.

## Smaller things

- `protofunctions.getField` answers the field for a name that is not an
  attribute — `' DEF'`, or an event stored under a name a program cannot write.
  It answered the name itself.
- `str(node)` says the node's DEF name.
- Setting a vector field from one number works: `transform.scale = 2` raised.
- `MFString` refuses a value it cannot read with a ValueError naming the field,
  as its sibling types do.
- `field.PyBaseField` names the Python implementation of the field primitives
  whichever build is installed, so the two can be compared. Where the
  accelerator is installed, `field.BaseField` is the compiled class as before.
- `vrml.arrays` drops what it carried for Numeric. `typeCode` reads
  `dtype.char`; the `typecode()` fallbacks are gone.
