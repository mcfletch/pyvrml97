# X3D 4.1 XML Schema

The schema the XML writer's output is validated against in
`tests/test_x3d_writers.py`. Copied from Web3D's x3d Subversion repository,
`www.web3d.org/specifications/`, at revision 40303, the revision
`tools/generate_x3d.py` reads the X3DUOM at.

| File | SHA-256 |
| --- | --- |
| `x3d-4.1.xsd` | `424c7717fec66bae8b7598673bc4ba2359fb56c853b997cba4f44a518d06d173` |
| `x3d-4.1-Web3dExtensionsPublic.xsd` | `8643f06321b8152e481f30c03c1c9f00efd61b6ea3806c5e752289092c3289a2` |
| `x3d-4.1-Web3dExtensionsPrivate.xsd` | `784ee866095751eb9ca559837defdf3c1b9980ce66623aaa7635ced6a0d645d3` |
| `xmldsig-core-schema.xsd` | `35cf8197da812c85e40d57891b35c94187569ed474a2dac813ce5090dafcd35c` |

`x3d-4.1.xsd` imports `xmldsig-core-schema.xsd` and includes the other two.

The X3D schema files are under the Web3D Consortium Open-Source License
(`license.html`). `xmldsig-core-schema.xsd` is the W3C XML Signature schema,
under the W3C Software and Document License.
