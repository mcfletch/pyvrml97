"""Behaviour pyvrml97 gives some X3D declarations, as mix-ins

The generated declarations in `vrml.x3d.nodes` carry fields only; a node
that pyvrml97 itself computes something for takes one of these as a base:
`LocalMatrices` for a `Transform`, and `Bindable` (:mod:`vrml.x3d.binding`)
for every bindable node.
"""

from vrml import cache
from vrml.vrml97 import transformmatrix
from vrml.x3d.binding import Bindable

__all__ = ['Bindable', 'LocalMatrices']


class LocalMatrices:
    """The forward and inverse matrices of a Transform's own fields"""

    def localMatrices(self, translate: bool=True, scale: bool=True, rotate: bool=True) -> cache.CacheHolder:
        """Calculate/lookup our local matrices

        Certain operations want, e.g. just the rotation of an item,
        so we actually can store 2**3 possible variations of the local
        matrices.  In practice we only see a very small number.

        returns holder, where holder.data == (forward,inverse) matrix
        for the local node, each of which can be None
        """
        key = ('local_matrices', translate, scale, rotate)
        found = cache.CACHE.get(id(self))
        holder: cache.CacheHolder|None
        mHolder:cache.CacheHolder|None
        holder = None if found is None else found.get(key)
        if holder is None:
            doConnect = True
            holder = cache.CACHE.holder(self, None, key=key)
            mHolder = None
        else:
            doConnect = False
            mHolder = holder.data
        if mHolder is None:
            fields = []
            if translate:
                fields.append('translation')
            if scale or rotate:
                fields.append('center')
            if scale:
                fields.append('scale')
                fields.append('scaleOrientation')
            if rotate:
                fields.append('rotation')
            d = self.__dict__
            forward, inverse = transformmatrix.localMatrices(
                **dict([(k, d.get(k)) for k in fields])
            )
            if doConnect:
                for k in fields:
                    holder.depend(self, k)
            holder.data = (forward, inverse)
        return holder

