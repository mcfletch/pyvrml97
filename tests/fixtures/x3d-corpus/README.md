# Web3D X3D example subset

Twenty-nine scenes from two of Web3D's X3D example archives, each in the five
encodings Web3D publishes (`.x3d`, `.x3dv`, `.json`, `.x3db`, `.wrl`):
145 files. `tests/test_x3d_corpus.py` and `tests/test_x3d_fastinfoset.py` read
them, so the readers and writers are tested without the full corpus, which
`tools/fetch_x3d_corpus.py` fetches into a cache (`vrml.x3d.corpus`).

The files are copied unchanged from these archives, laid out as Web3D
publishes them under `www.web3d.org/x3d/content/examples/`:

| Archive | Download | SHA-256 |
| --- | --- | --- |
| ConformanceNist | `https://www.web3d.org/x3d/content/examples/X3dExamplesConformanceNist.zip` | `adcd5acecbcfa1c94c54e1d753308ebccaa2b19fdb40eb22f2f1e0cdad7b236b` |
| Vrml2Sourcebook | `https://www.web3d.org/x3d/content/examples/X3dExamplesVrml2Sourcebook.zip` | `2f41d8b64a40b142bafbc88ab7600313d92623bfa84deb8f30e1bc101a8e6ae0` |

The digests are those `vrml.x3d.corpus.DIGESTS` records. Web3D rebuilds the
archives as the examples change; its version control is the x3d Subversion
repository on SourceForge (`https://sourceforge.net/p/x3d/code/`).

The examples are under the Web3D Consortium Open-Source License, a copy of
which is in each archive's folder (`license.html`).
