# EXTERNPROTO references that name a browser's own node

The references `vrml.x3d.knownprotos` holds, with where each was seen. Read on
2026-10-10 from the worlds published at
`https://www.bitmanagement.com/developer/contact/nurbs/examples.htm` and from
that page's own text. No browser's source was read.

## Reference forms

| Reference | Seen in |
|---|---|
| `urn:inet:blaxxun.com:node:<Name>` | the first URL of each world below |
| `http://www.blaxxun.com/vrml/protos/nurbs.wrl#<Name>` | the last URL of each world below, except `FredTheBunny.wrl` |
| `urn:inet:bitmanagement.de:node:<Name>` | the page's text, for `NurbsSurface` |

Each world also lists a relative file (`nurbs.wrl#<Name>`,
`NurbsPrototypes.wrl#<Name>`). A relative name is not a known reference.

`FredTheBunny.wrl` also lists
`http://www.web3d.org/TaskGroups/x3d/translation/examples/Nurbs/NurbsPrototypes.wrl#NurbsSurface`
and the same path ending `.x3d`. Neither has an entry: the interface those
files declare has not been read.

## Worlds

`<Name>` is `NurbsSurface` in each, except `nurbscurve.wrl`, where it is
`NurbsCurve`.

`nurbscurve.wrl`, `animated_patch.wrl`, `ci_animated_patch66.wrl`, `head.wrl`,
`parfum.wrl`, `4ducks.wrl`, `sizetest/nrbduck_0.wrl`, `3dsmax/nrbduck.wrl`,
`3dsmax/jack.wrl`, `3dsmax/stingray.wrl`,
`x3d/nurbs/examples/FredTheBunny.wrl`.

## Declared interfaces

`NurbsSurface`, as every world but `FredTheBunny.wrl` declares it:

| Access | Type | Name |
|---|---|---|
| field | SFInt32 | uDimension |
| field | SFInt32 | vDimension |
| field | MFFloat | uKnot |
| field | MFFloat | vKnot |
| field | SFInt32 | uOrder |
| field | SFInt32 | vOrder |
| exposedField | MFVec3f | controlPoint |
| exposedField | MFFloat | weight |
| exposedField | SFInt32 | uTessellation |
| exposedField | SFInt32 | vTessellation |
| exposedField | SFNode | texCoord |
| field | SFBool | ccw |
| field | SFBool | solid |

`FredTheBunny.wrl` declares the same names and types, with `controlPoint`,
`weight`, `uTessellation` and `vTessellation` as `field`.

`NurbsCurve`, as `nurbscurve.wrl` declares it:

| Access | Type | Name |
|---|---|---|
| field | MFFloat | knot |
| field | SFInt32 | order |
| exposedField | MFVec3f | controlPoint |
| exposedField | MFFloat | weight |
| exposedField | SFInt32 | tessellation |

## Node names

The names entered for the three reference forms are the NURBS nodes of
ISO/IEC 14772-1:1997/Amd 1:2003: `Contour2D`, `CoordinateDeformer`,
`NurbsCurve`, `NurbsCurve2D`, `NurbsGroup`, `NurbsPositionInterpolator`,
`NurbsSurface`, `NurbsTextureSurface`, `Polyline2D`, `TrimmedSurface`. Only
`NurbsSurface` and `NurbsCurve` were seen in a reference; the others are
entered on the amendment's list of names, which is to be checked against its
text.
