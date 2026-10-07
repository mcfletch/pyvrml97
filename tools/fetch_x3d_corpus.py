#!/usr/bin/env python3
"""Fetch Web3D's X3D example archives, the corpus the readers are tested on

    tools/fetch_x3d_corpus.py                 ConformanceNist and Vrml2Sourcebook
    tools/fetch_x3d_corpus.py Basic Savage    others by name
    tools/fetch_x3d_corpus.py --resources     with the images and Web3D's renders

The archives are downloaded into the corpus directory and their scene files
and licence extracted (`vrml.x3d.corpus`, which says where and what).
`tests/test_x3d_corpus.py` reads them from there and skips where they are not.
"""

import argparse
import sys
from collections.abc import Sequence

from vrml.x3d import corpus


def main(arguments: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('archives', nargs='*', choices=corpus.ARCHIVES)
    parser.add_argument('--resources', action='store_true',
                        help='also extract the images the scenes name and Web3D\'s renders')
    options = parser.parse_args(arguments)
    where = corpus.directory()
    for name, count in corpus.fetch(options.archives or corpus.DEFAULT_ARCHIVES,
                                    where, options.resources).items():
        print('%s: %d scenes in %s/%s' % (name, count, where, name))
    return 0


if __name__ == '__main__':
    sys.exit(main())
