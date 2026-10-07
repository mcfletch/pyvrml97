"""X3D's interpolation arithmetic -- NumPy only

The interpolator nodes of :mod:`vrml.x3d.runtime` call these with their keys
and values (ISO/IEC 19775-1, 19.2):

- :func:`segment` finds the keys a fraction lies between;
- :func:`linear` interpolates straight between them, one value or a run of
  values per key;
- :func:`spline` follows X3D's Hermite spline through the values, with
  tangents from :func:`tangents`;
- :func:`ease` reshapes a fraction as `EaseInEaseOut` does;
- :func:`squad` interpolates rotations by spherical cubic interpolation.

Rotations are X3D's (axis x, y, z, angle in radians); quaternions are
(x, y, z, w).
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from numpy.typing import ArrayLike

__all__ = ['ease', 'linear', 'quaternion_of', 'rotation_of', 'segment', 'slerp', 'spline',
           'squad', 'tangents']


def segment(keys: ArrayLike, fraction: float) -> "tuple[int, float]":
    """(i, s): the fraction lies `s` of the way from key i to key i+1

    Before the first key is (0, 0); after the last is the last segment's
    end. One key is (0, 0).
    """
    found = np.asarray(keys, dtype=np.float64).ravel()
    if len(found) < 2:
        return 0, 0.0
    fraction = float(fraction)
    if fraction <= found[0]:
        return 0, 0.0
    if fraction >= found[-1]:
        return len(found) - 2, 1.0
    index = int(np.searchsorted(found, fraction, side='right')) - 1
    index = min(max(index, 0), len(found) - 2)
    span = found[index + 1] - found[index]
    return index, float((fraction - found[index]) / span) if span > 0 else 0.0


def _per_key(values: ArrayLike, count: int, per_key: int) -> np.ndarray:
    found = np.asarray(values, dtype=np.float64)
    width = found.shape[-1] if found.ndim > 1 else 1
    return found.reshape(count, per_key, width)


def linear(keys: ArrayLike, values: ArrayLike, fraction: float, per_key: int = 1) -> np.ndarray:
    """The value (or run of `per_key` values) a fraction names, straight between keys"""
    count = len(np.asarray(keys).ravel())
    runs = _per_key(values, count, per_key)
    index, s = segment(keys, fraction)
    if count < 2:
        found = runs[0]
    else:
        found = runs[index] * (1.0 - s) + runs[index + 1] * s
    shape: Any = np.asarray(values).shape[1:] if per_key == 1 else (per_key,) + np.asarray(values).shape[1:]
    return np.asarray(found).reshape(shape)


def tangents(values: ArrayLike, closed: bool = False,
             velocities: Optional[ArrayLike] = None, normalize: bool = False) -> np.ndarray:
    """The tangent at each value of X3D's spline, before the keys' spacing scales it

    Given velocities, one per key or (on an open curve) one for each end, are
    used; the others are half the difference of the neighbouring values, with
    the neighbours of the ends found round the join on a closed curve and the
    ends' tangents zero on an open one. `normalize` scales each tangent to
    the length of the whole curve through the values.
    """
    found = np.asarray(values, dtype=np.float64)
    points = found.reshape(len(found), -1)
    count = len(points)
    result = np.zeros_like(points)
    for index in range(count):
        if index == 0 or index == count - 1:
            if closed and count > 2:
                before, after = points[-2], points[1]
                result[index] = (after - before) / 2.0
        else:
            result[index] = (points[index + 1] - points[index - 1]) / 2.0
    given = np.asarray(velocities if velocities is not None else (), dtype=np.float64)
    if given.size:
        given = given.reshape(-1, points.shape[1])
        if len(given) == count:
            result = given.copy()
        elif len(given) == 2 and not closed:
            result[0], result[-1] = given[0], given[1]
    if normalize:
        total = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
        lengths = np.linalg.norm(result, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        result = result / lengths * total
    return result.reshape(found.shape)


def spline(keys: ArrayLike, values: ArrayLike, fraction: float, closed: bool = False,
           velocities: Optional[ArrayLike] = None, normalize: bool = False) -> np.ndarray:
    """The value of X3D's Hermite spline through `values` at a fraction

    `closed` joins the last value to the first where they are the same. Each
    key's tangent is scaled for the spacing of its neighbouring keys.
    """
    key = np.asarray(keys, dtype=np.float64).ravel()
    found = np.asarray(values, dtype=np.float64)
    if len(key) < 2:
        return found[0] if len(found) else found
    points = found.reshape(len(found), -1)
    closed = bool(closed) and np.allclose(points[0], points[-1])
    tangent = tangents(points, closed, velocities, normalize).reshape(points.shape)
    index, s = segment(key, fraction)

    def scaled(at: int, outgoing: bool) -> np.ndarray:
        """The tangent at key `at`, scaled for the spacing of its neighbours"""
        found: np.ndarray = tangent[at]
        if (at == 0 or at == len(key) - 1) and not closed:
            return found
        if at == 0 or at == len(key) - 1:
            before, after = key[-1] - key[-2], key[1] - key[0]
        else:
            before, after = key[at] - key[at - 1], key[at + 1] - key[at]
        total = before + after
        if total > 0:
            found = found * (2.0 * (after if outgoing else before) / total)
        return found

    h00 = 2 * s ** 3 - 3 * s ** 2 + 1
    h10 = s ** 3 - 2 * s ** 2 + s
    h01 = -2 * s ** 3 + 3 * s ** 2
    h11 = s ** 3 - s ** 2
    value = (h00 * points[index] + h10 * scaled(index, True)
             + h01 * points[index + 1] + h11 * scaled(index + 1, False))
    return np.asarray(value).reshape(found.shape[1:])


def ease(keys: ArrayLike, pairs: ArrayLike, fraction: float) -> float:
    """`EaseInEaseOut`'s modified fraction

    Between keys i and i+1 the motion eases out of key i over pair i's
    second value and into key i+1 over pair i+1's first; the two are scaled
    down together where they add up to more than 1.
    """
    key = np.asarray(keys, dtype=np.float64).ravel()
    ease_pairs = np.asarray(pairs, dtype=np.float64).reshape(-1, 2)
    if len(key) < 2 or len(ease_pairs) < len(key):
        return float(fraction)
    index, u = segment(key, fraction)
    out_of, into = float(ease_pairs[index][1]), float(ease_pairs[index + 1][0])
    if out_of + into > 1.0:
        out_of, into = out_of / (out_of + into), into / (out_of + into)
    k = 1.0 / (2.0 - out_of - into)
    if u < out_of:
        modified = (k / out_of) * u * u
    elif u <= 1.0 - into:
        modified = k * (2.0 * u - out_of)
    else:
        modified = 1.0 - (k * (1.0 - u) ** 2) / into
    return float(key[index] + (key[index + 1] - key[index]) * modified)


def quaternion_of(rotation: ArrayLike) -> np.ndarray:
    """A rotation (axis, angle) as a unit quaternion (x, y, z, w)"""
    found = np.asarray(rotation, dtype=np.float64).ravel()
    axis = found[:3]
    length = np.linalg.norm(axis)
    axis = axis / length if length > 0 else np.array([0.0, 0.0, 1.0])
    half = float(found[3]) / 2.0
    return np.concatenate([axis * math.sin(half), [math.cos(half)]])


def rotation_of(quaternion: ArrayLike) -> np.ndarray:
    """A unit quaternion (x, y, z, w) as a rotation (axis, angle), the angle in [0, pi]"""
    found = np.asarray(quaternion, dtype=np.float64)
    found = found / np.linalg.norm(found)
    if found[3] < 0:
        found = -found
    angle = 2.0 * math.acos(min(1.0, max(-1.0, found[3])))
    axis = found[:3]
    length = np.linalg.norm(axis)
    if length < 1e-12:
        return np.array([0.0, 0.0, 1.0, 0.0])
    return np.concatenate([axis / length, [angle]])


def _multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def _inverse(q: np.ndarray) -> np.ndarray:
    return np.array([-q[0], -q[1], -q[2], q[3]])


def _log(q: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(q[:3])
    if length < 1e-12:
        return np.zeros(4)
    angle = math.atan2(length, q[3])
    return np.concatenate([q[:3] / length * angle, [0.0]])


def _exp(v: np.ndarray) -> np.ndarray:
    angle = np.linalg.norm(v[:3])
    if angle < 1e-12:
        return np.array([0.0, 0.0, 0.0, 1.0])
    return np.concatenate([v[:3] / angle * math.sin(angle), [math.cos(angle)]])


def slerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """The unit quaternion `t` of the way from `a` to `b` along the shorter arc"""
    cosine = float(np.dot(a, b))
    if cosine < 0:
        b, cosine = -b, -cosine
    found: np.ndarray
    if cosine > 1.0 - 1e-9:
        found = a + (b - a) * t
        found = found / np.linalg.norm(found)
    else:
        angle = math.acos(cosine)
        found = (math.sin((1 - t) * angle) * a + math.sin(t * angle) * b) / math.sin(angle)
    return found


def squad(keys: ArrayLike, rotations: ArrayLike, fraction: float) -> np.ndarray:
    """The rotation `SquadOrientationInterpolator` sends at a fraction

    Spherical cubic interpolation of the rotations as quaternions, each key
    given an inner control quaternion from its neighbours.
    """
    key = np.asarray(keys, dtype=np.float64).ravel()
    quaternions = [quaternion_of(rotation) for rotation in np.asarray(rotations, np.float64)]
    for index in range(1, len(quaternions)):
        if np.dot(quaternions[index - 1], quaternions[index]) < 0:
            quaternions[index] = -quaternions[index]
    if len(key) < 2:
        return rotation_of(quaternions[0])
    inner = []
    for index, q in enumerate(quaternions):
        if index == 0 or index == len(quaternions) - 1:
            inner.append(q)
            continue
        back = _inverse(q)
        tangent = (_log(_multiply(back, quaternions[index + 1]))
                   + _log(_multiply(back, quaternions[index - 1]))) / -4.0
        inner.append(_multiply(q, _exp(tangent)))
    index, h = segment(key, fraction)
    outer = slerp(quaternions[index], quaternions[index + 1], h)
    middle = slerp(inner[index], inner[index + 1], h)
    return rotation_of(slerp(outer, middle, 2.0 * h * (1.0 - h)))
