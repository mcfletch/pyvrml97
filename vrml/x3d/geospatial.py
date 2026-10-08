"""X3D's spatial reference frames (ISO/IEC 19775-1, 25.2), in double precision; no GL

A geospatial node's `geoSystem` names its frame: ``GD`` geodetic (latitude,
longitude in degrees and elevation in metres above the ellipsoid; longitude
first with ``"longitude_first"``), ``UTM`` Universal Transverse Mercator
(northing, easting, elevation in zone ``"Z<n>"``, the southern hemisphere
with ``"S"``, easting first with ``"easting_first"``) or ``GC`` geocentric
(metres along X through the prime meridian at the equator, Y through 90
degrees east, Z through the north pole). A GD or UTM system names its
ellipsoid by the two-letter codes of :data:`ELLIPSOIDS`, WGS84 (``"WE"``)
where it names none; an unknown word is ignored.

:func:`to_geocentric` and :func:`from_geocentric` convert between a system's
coordinates and geocentric ones; :func:`up` is the ellipsoid's normal at a
geocentric point and :func:`location_matrix` the frame a geospatial node
places its children in: +Y up along that normal, +X east and -Z north, at the
point. An :class:`Origin` (X3D's GeoOrigin) is subtracted from geocentric
coordinates to keep them small, and turned so its own up is +Y where
`rotateYUp` asks.

UTM is the Transverse Mercator projection in the Krüger series to the sixth
order (C. F. F. Karney, "Transverse Mercator with an accuracy of a few
nanometers", J. Geodesy 85, 2011), with the scale factor 0.9996 on the
central meridian, a false easting of 500 000 m and a false northing of
10 000 000 m in the southern hemisphere.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, NamedTuple

import numpy as np

__all__ = ['ELLIPSOIDS', 'Ellipsoid', 'GeoSystem', 'Origin', 'elevations', 'frame', 'from_geocentric',
           'geo_coordinates', 'grid_coordinates', 'location_matrix', 'node_origin', 'node_system',
           'scene_matrix', 'scene_points', 'slerp_points', 'system', 'to_geocentric', 'up']


class Ellipsoid(NamedTuple):
    """A reference ellipsoid: semi-major axis `a` in metres and the inverse of its flattening"""

    a: float
    inverse_flattening: float

    @property
    def f(self) -> float:
        """The flattening"""
        return 1.0 / self.inverse_flattening

    @property
    def e2(self) -> float:
        """The square of the first eccentricity"""
        return self.f * (2.0 - self.f)

    @property
    def b(self) -> float:
        """The semi-minor axis, in metres"""
        return self.a * (1.0 - self.f)


#: X3D's ellipsoid codes (19775-1, table 25.3) by code.
ELLIPSOIDS: dict[str, Ellipsoid] = {
    'AA': Ellipsoid(6377563.396, 299.3249646),     # Airy 1830
    'AM': Ellipsoid(6377340.189, 299.3249646),     # Modified Airy
    'AN': Ellipsoid(6378160.0, 298.25),            # Australian National
    'BN': Ellipsoid(6377483.865, 299.1528128),     # Bessel 1841 (Namibia)
    'BR': Ellipsoid(6377397.155, 299.1528128),     # Bessel 1841 (Ethiopia, Indonesia...)
    'CC': Ellipsoid(6378206.4, 294.9786982),       # Clarke 1866
    'CD': Ellipsoid(6378249.145, 293.465),         # Clarke 1880
    'EA': Ellipsoid(6377276.345, 300.8017),        # Everest (India 1830)
    'EB': Ellipsoid(6377298.556, 300.8017),        # Everest (Sabah & Sarawak)
    'EC': Ellipsoid(6377301.243, 300.8017),        # Everest (India 1956)
    'ED': Ellipsoid(6377304.063, 300.8017),        # Everest (W. Malaysia & Singapore 1948)
    'EE': Ellipsoid(6377295.664, 300.8017),        # Everest (W. Malaysia 1969)
    'EF': Ellipsoid(6377309.613, 300.8017),        # Everest (Pakistan)
    'FA': Ellipsoid(6378155.0, 298.3),             # Modified Fischer 1960
    'HE': Ellipsoid(6378200.0, 298.3),             # Helmert 1906
    'HO': Ellipsoid(6378270.0, 297.0),             # Hough 1960
    'ID': Ellipsoid(6378160.0, 298.247),           # Indonesian 1974
    'IN': Ellipsoid(6378388.0, 297.0),             # International 1924
    'KA': Ellipsoid(6378245.0, 298.3),             # Krassovsky 1940
    'RF': Ellipsoid(6378137.0, 298.257222101),     # Geodetic Reference System 1980
    'SA': Ellipsoid(6378160.0, 298.25),            # South American 1969
    'WD': Ellipsoid(6378135.0, 298.26),            # WGS 72
    'WE': Ellipsoid(6378137.0, 298.257223563),     # WGS 84
}

#: UTM's scale on the central meridian, and its false easting and southern northing.
UTM_SCALE = 0.9996
UTM_FALSE_EASTING = 500000.0
UTM_FALSE_NORTHING = 10000000.0


class GeoSystem(NamedTuple):
    """A `geoSystem` read: the kind of frame, its ellipsoid, and the order and zone of its coordinates"""

    kind: str = 'GD'
    ellipsoid: Ellipsoid = ELLIPSOIDS['WE']
    latitude_first: bool = True
    zone: int = 1
    northern: bool = True
    northing_first: bool = True


def system(names: Sequence[str]) -> GeoSystem:
    """The frame a `geoSystem` field's strings name"""
    words = [str(name) for name in names]
    kind = next((word for word in words if word in ('GD', 'GDC', 'UTM', 'GC', 'GCC')), 'GD')
    kind = {'GDC': 'GD', 'GCC': 'GC'}.get(kind, kind)
    ellipsoid = next((ELLIPSOIDS[word] for word in words if word in ELLIPSOIDS), ELLIPSOIDS['WE'])
    zone = next((int(word[1:]) for word in words
                 if len(word) > 1 and word[0] == 'Z' and word[1:].isdigit()), 1)
    return GeoSystem(kind, ellipsoid, 'longitude_first' not in words, zone, 'S' not in words,
                     'easting_first' not in words)


def _points(values: Any) -> np.ndarray:
    return np.asarray(values, dtype=np.float64).reshape(-1, 3)


def _geodetic_to_geocentric(ellipsoid: Ellipsoid, latitude: np.ndarray, longitude: np.ndarray,
                            height: np.ndarray) -> np.ndarray:
    """Geocentric points of latitudes and longitudes in radians and heights in metres"""
    sine = np.sin(latitude)
    normal = ellipsoid.a / np.sqrt(1.0 - ellipsoid.e2 * sine * sine)
    across = (normal + height) * np.cos(latitude)
    return np.column_stack([across * np.cos(longitude), across * np.sin(longitude),
                            (normal * (1.0 - ellipsoid.e2) + height) * sine])


def _geocentric_to_geodetic(ellipsoid: Ellipsoid, points: np.ndarray
                            ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Latitudes and longitudes in radians and heights in metres of geocentric points"""
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    e2 = ellipsoid.e2
    across = np.hypot(x, y)
    longitude = np.arctan2(y, x)
    latitude = np.arctan2(z, across * (1.0 - e2))
    for _ in range(8):
        sine = np.sin(latitude)
        normal = ellipsoid.a / np.sqrt(1.0 - e2 * sine * sine)
        latitude = np.arctan2(z + e2 * normal * sine, across)
    sine, cosine = np.sin(latitude), np.cos(latitude)
    height = across * cosine + z * sine - ellipsoid.a * np.sqrt(1.0 - e2 * sine * sine)
    return latitude, longitude, height


class _Kruger(NamedTuple):
    """An ellipsoid's Transverse Mercator series"""

    rectifying: float                 # the radius of the rectifying sphere, A
    alpha: tuple[float, ...]          # forward
    beta: tuple[float, ...]           # inverse
    delta: tuple[float, ...]          # conformal to geodetic latitude
    conformal: float                  # 2 sqrt(n) / (1 + n)


def _kruger(ellipsoid: Ellipsoid) -> _Kruger:
    n = ellipsoid.f / (2.0 - ellipsoid.f)
    n2, n3, n4, n5, n6 = n ** 2, n ** 3, n ** 4, n ** 5, n ** 6
    rectifying = ellipsoid.a / (1.0 + n) * (1.0 + n2 / 4.0 + n4 / 64.0 + n6 / 256.0)
    alpha = (n / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800,
             13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360,
             61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440,
             49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600,
             34729 * n5 / 80640 - 3418889 * n6 / 1995840,
             212378941 * n6 / 319334400)
    beta = (n / 2 - 2 * n2 / 3 + 37 * n3 / 96 - n4 / 360 - 81 * n5 / 512 + 96199 * n6 / 604800,
            n2 / 48 + n3 / 15 - 437 * n4 / 1440 + 46 * n5 / 105 - 1118711 * n6 / 3870720,
            17 * n3 / 480 - 37 * n4 / 840 - 209 * n5 / 4480 + 5569 * n6 / 90720,
            4397 * n4 / 161280 - 11 * n5 / 504 - 830251 * n6 / 7257600,
            4583 * n5 / 161280 - 108847 * n6 / 3991680,
            20648693 * n6 / 638668800)
    delta = (2 * n - 2 * n2 / 3 - 2 * n3 + 116 * n4 / 45 + 26 * n5 / 45 - 2854 * n6 / 675,
             7 * n2 / 3 - 8 * n3 / 5 - 227 * n4 / 45 + 2704 * n5 / 315 + 2323 * n6 / 945,
             56 * n3 / 15 - 136 * n4 / 35 - 1262 * n5 / 105 + 73814 * n6 / 2835,
             4279 * n4 / 630 - 332 * n5 / 35 - 399572 * n6 / 14175,
             4174 * n5 / 315 - 144838 * n6 / 6237,
             601676 * n6 / 22275)
    return _Kruger(rectifying, alpha, beta, delta, 2.0 * math.sqrt(n) / (1.0 + n))


def _central_meridian(zone: int) -> float:
    return math.radians(6.0 * zone - 183.0)


def _utm_to_geodetic(geo: GeoSystem, northing: np.ndarray, easting: np.ndarray
                     ) -> tuple[np.ndarray, np.ndarray]:
    series = _kruger(geo.ellipsoid)
    north = northing - (0.0 if geo.northern else UTM_FALSE_NORTHING)
    xi = north / (UTM_SCALE * series.rectifying)
    eta = (easting - UTM_FALSE_EASTING) / (UTM_SCALE * series.rectifying)
    xi_prime, eta_prime = xi.copy(), eta.copy()
    for order, coefficient in enumerate(series.beta, 1):
        xi_prime -= coefficient * np.sin(2 * order * xi) * np.cosh(2 * order * eta)
        eta_prime -= coefficient * np.cos(2 * order * xi) * np.sinh(2 * order * eta)
    chi = np.arcsin(np.sin(xi_prime) / np.cosh(eta_prime))
    latitude = chi.copy()
    for order, coefficient in enumerate(series.delta, 1):
        latitude += coefficient * np.sin(2 * order * chi)
    longitude = _central_meridian(geo.zone) + np.arctan2(np.sinh(eta_prime), np.cos(xi_prime))
    return latitude, longitude


def _geodetic_to_utm(geo: GeoSystem, latitude: np.ndarray, longitude: np.ndarray
                     ) -> tuple[np.ndarray, np.ndarray]:
    series = _kruger(geo.ellipsoid)
    sine = np.sin(latitude)
    t = np.sinh(np.arctanh(sine) - series.conformal * np.arctanh(series.conformal * sine))
    turn = longitude - _central_meridian(geo.zone)
    xi_prime = np.arctan2(t, np.cos(turn))
    eta_prime = np.arctanh(np.sin(turn) / np.sqrt(1.0 + t * t))
    xi, eta = xi_prime.copy(), eta_prime.copy()
    for order, coefficient in enumerate(series.alpha, 1):
        xi += coefficient * np.sin(2 * order * xi_prime) * np.cosh(2 * order * eta_prime)
        eta += coefficient * np.cos(2 * order * xi_prime) * np.sinh(2 * order * eta_prime)
    easting = UTM_FALSE_EASTING + UTM_SCALE * series.rectifying * eta
    northing = UTM_SCALE * series.rectifying * xi + (0.0 if geo.northern else UTM_FALSE_NORTHING)
    return northing, easting


def to_geocentric(geo: GeoSystem, coordinates: Any) -> np.ndarray:
    """Geocentric points, (N, 3) metres, of `coordinates` in `geo`"""
    points = _points(coordinates)
    if geo.kind == 'GC':
        return points.copy()
    first, second, height = points[:, 0], points[:, 1], points[:, 2]
    if geo.kind == 'UTM':
        northing, easting = (first, second) if geo.northing_first else (second, first)
        latitude, longitude = _utm_to_geodetic(geo, northing, easting)
    else:
        degrees = (first, second) if geo.latitude_first else (second, first)
        latitude, longitude = np.radians(degrees[0]), np.radians(degrees[1])
    return _geodetic_to_geocentric(geo.ellipsoid, latitude, longitude, height)


def from_geocentric(geo: GeoSystem, points: Any) -> np.ndarray:
    """`geo`'s coordinates, (N, 3), of geocentric points"""
    points = _points(points)
    if geo.kind == 'GC':
        return points.copy()
    latitude, longitude, height = _geocentric_to_geodetic(geo.ellipsoid, points)
    if geo.kind == 'UTM':
        northing, easting = _geodetic_to_utm(geo, latitude, longitude)
        pair = (northing, easting) if geo.northing_first else (easting, northing)
    else:
        degrees = (np.degrees(latitude), np.degrees(longitude))
        pair = degrees if geo.latitude_first else (degrees[1], degrees[0])
    return np.column_stack([pair[0], pair[1], height])


def up(geo: GeoSystem, points: Any) -> np.ndarray:
    """The ellipsoid's unit normal, (N, 3), at each geocentric point"""
    latitude, longitude, _height = _geocentric_to_geodetic(geo.ellipsoid, _points(points))
    cosine = np.cos(latitude)
    return np.column_stack([cosine * np.cos(longitude), cosine * np.sin(longitude),
                            np.sin(latitude)])


def frame(geo: GeoSystem, point: Any) -> np.ndarray:
    """The row-vector 4x4 frame at a geocentric point: rows east, up, south, and the point"""
    point = _points(point)[0]
    normal = up(geo, point)[0]
    east = np.cross((0.0, 0.0, 1.0), normal)
    if np.linalg.norm(east) < 1e-12:
        east = np.array((1.0, 0.0, 0.0))
    east /= np.linalg.norm(east)
    south = np.cross(east, normal)
    south /= np.linalg.norm(south)
    matrix = np.eye(4)
    matrix[0, :3], matrix[1, :3], matrix[2, :3], matrix[3, :3] = east, normal, south, point
    return matrix


def location_matrix(geo: GeoSystem, coordinates: Any) -> np.ndarray:
    """The row-vector 4x4 frame a geospatial node places its children in at `coordinates`

    +Y is up along the ellipsoid's normal, +X east and -Z north, at the point
    the coordinates name, in geocentric metres. At a pole, east is +X.
    """
    return frame(geo, to_geocentric(geo, coordinates))


class Origin:
    """X3D's GeoOrigin: geocentric points made local by subtracting its point,
    and turned so its up is +Y where `rotate_y_up` is true"""

    def __init__(self, geo: GeoSystem, coordinates: Any, rotate_y_up: bool = False) -> None:
        self.system = geo
        self.point = to_geocentric(geo, coordinates)[0]
        self.rotate_y_up = bool(rotate_y_up)
        self.matrix = frame(geo, self.point) if rotate_y_up else np.eye(4)
        if not rotate_y_up:
            self.matrix[3, :3] = self.point
        self.inverse = np.linalg.inv(self.matrix)

    def local(self, points: Any) -> np.ndarray:
        """Geocentric points as the scene's coordinates"""
        points = _points(points)
        return points @ self.inverse[:3, :3] + self.inverse[3, :3]

    def geocentric(self, points: Any) -> np.ndarray:
        """The scene's coordinates as geocentric points"""
        points = _points(points)
        return points @ self.matrix[:3, :3] + self.matrix[3, :3]

    def local_matrix(self, matrix: Any) -> np.ndarray:
        """A row-vector geocentric 4x4 frame as the scene's"""
        return np.asarray(matrix, dtype=np.float64) @ self.inverse


def node_origin(node: Any) -> "Origin | None":
    """The :class:`Origin` a geospatial node's `geoOrigin` names, or None for none"""
    found = getattr(node, 'geoOrigin', None)
    if not found:
        return None
    return Origin(system(found.geoSystem), found.geoCoords, bool(found.rotateYUp))


def node_system(node: Any) -> GeoSystem:
    """The frame a geospatial node's `geoSystem` names"""
    return system(getattr(node, 'geoSystem', ()) or ())


def scene_points(node: Any, coordinates: Any) -> np.ndarray:
    """A geospatial node's `coordinates` as the scene's points, in double precision

    Geocentric metres, less the node's GeoOrigin where it has one.
    """
    points = to_geocentric(node_system(node), coordinates)
    origin = node_origin(node)
    return origin.local(points) if origin is not None else points


def scene_matrix(node: Any, coordinates: Any) -> np.ndarray:
    """The row-vector frame a geospatial node places children in at `coordinates`, in the scene"""
    matrix = location_matrix(node_system(node), coordinates)
    origin = node_origin(node)
    return origin.local_matrix(matrix) if origin is not None else matrix


def geo_coordinates(node: Any, points: Any) -> np.ndarray:
    """The scene's points as a geospatial node's coordinates"""
    origin = node_origin(node)
    geocentric = origin.geocentric(points) if origin is not None else _points(points)
    return from_geocentric(node_system(node), geocentric)


def elevations(node: Any, points: Any) -> np.ndarray:
    """The heights of the scene's `points` above a geospatial node's ellipsoid, metres"""
    origin = node_origin(node)
    geocentric = origin.geocentric(points) if origin is not None else _points(points)
    geodetic = GeoSystem('GD', node_system(node).ellipsoid)
    heights: np.ndarray = from_geocentric(geodetic, geocentric)[:, 2]
    return heights


def grid_coordinates(geo: GeoSystem, origin: Any, across: int, deep: int, x_spacing: float,
                     z_spacing: float, heights: Any, y_scale: float = 1.0) -> np.ndarray:
    """A GeoElevationGrid's points, (across * deep, 3) coordinates in `geo`

    Row by row from `origin`: each step across adds `x_spacing` to the
    longitude or easting, each step deep adds `z_spacing` to the latitude or
    northing, and each point is `y_scale` times its height above the origin's
    elevation. A height `heights` is short of is 0.
    """
    rows, columns = np.meshgrid(np.arange(deep, dtype=np.float64),
                                np.arange(across, dtype=np.float64), indexing='ij')
    count = across * deep
    elevation = np.zeros(count, np.float64)
    given = np.asarray(heights, dtype=np.float64).ravel()[:count]
    elevation[:len(given)] = given
    northward = rows.ravel() * z_spacing
    eastward = columns.ravel() * x_spacing
    standard = geo.latitude_first if geo.kind == 'GD' else geo.northing_first
    first, second = (northward, eastward) if standard else (eastward, northward)
    start = np.asarray(origin, dtype=np.float64).reshape(3)
    return np.column_stack([start[0] + first, start[1] + second,
                            start[2] + elevation * y_scale])


def slerp_points(start: Any, end: Any, fraction: float) -> np.ndarray:
    """A geocentric point `fraction` of the way from `start` to `end` around the globe

    Its direction along the great circle between theirs, its distance from
    the centre straight between theirs.
    """
    start, end = np.asarray(start, np.float64), np.asarray(end, np.float64)
    first, second = np.linalg.norm(start), np.linalg.norm(end)
    if first == 0.0 or second == 0.0:
        return start + (end - start) * fraction
    a, b = start / first, end / second
    angle = math.acos(max(-1.0, min(1.0, float(np.dot(a, b)))))
    if angle < 1e-12:
        direction = a
    else:
        direction = (math.sin((1 - fraction) * angle) * a
                     + math.sin(fraction * angle) * b) / math.sin(angle)
    return direction * (first + (second - first) * fraction)
