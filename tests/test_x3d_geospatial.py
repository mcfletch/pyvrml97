"""Tests for vrml.x3d.geospatial: X3D's spatial reference frames, in double precision"""
import numpy as np
import pytest

from vrml.x3d import geospatial
from vrml.x3d import nodes as x3d
from vrml.x3d.runtime import PROTOTYPES

WGS84_A = 6378137.0
WGS84_B = 6356752.314245


def test_the_default_system_is_geodetic_on_wgs84_latitude_first():
    system = geospatial.system(['GD', 'WE'])
    assert system.kind == 'GD' and system.latitude_first
    assert system.ellipsoid.a == WGS84_A


@pytest.mark.parametrize('names, kind', [(['UTM', 'Z10'], 'UTM'), (['GC'], 'GC'),
                                         ([], 'GD'), (['nonsense'], 'GD')])
def test_the_system_kind(names, kind):
    assert geospatial.system(names).kind == kind


def test_utm_reads_its_zone_and_hemisphere():
    system = geospatial.system(['UTM', 'Z33', 'S', 'easting_first'])
    assert system.zone == 33 and not system.northern and not system.northing_first


@pytest.mark.parametrize('point, expected', [
    ((0.0, 0.0, 0.0), (WGS84_A, 0.0, 0.0)),
    ((0.0, 90.0, 0.0), (0.0, WGS84_A, 0.0)),
    ((90.0, 0.0, 0.0), (0.0, 0.0, WGS84_B)),
    ((0.0, 0.0, 100.0), (WGS84_A + 100.0, 0.0, 0.0)),
])
def test_geodetic_to_geocentric(point, expected):
    found = geospatial.to_geocentric(geospatial.system(['GD']), [point])
    assert np.allclose(found[0], expected, atol=1e-3)


def test_longitude_first_swaps_the_order():
    first = geospatial.to_geocentric(geospatial.system(['GD', 'longitude_first']),
                                     [(90.0, 0.0, 0.0)])
    assert np.allclose(first[0], (0.0, WGS84_A, 0.0), atol=1e-3)


def test_geocentric_is_itself():
    point = [(1.0, 2.0, 3.0)]
    assert np.allclose(geospatial.to_geocentric(geospatial.system(['GC']), point), point)


@pytest.mark.parametrize('names, point', [
    (['GD'], (43.65, -79.38, 76.5)),
    (['GD'], (-33.86, 151.21, 3.0)),
    (['GD', 'longitude_first'], (2.35, 48.85, 35.0)),
    (['UTM', 'Z17'], (4834000.0, 630000.0, 100.0)),
    (['UTM', 'Z56', 'S'], (6250000.0, 334000.0, 20.0)),
    (['UTM', 'Z17', 'easting_first'], (630000.0, 4834000.0, 100.0)),
    (['GD', 'CC'], (40.0, -100.0, 1500.0)),
])
def test_coordinates_round_trip(names, point):
    system = geospatial.system(names)
    back = geospatial.from_geocentric(system, geospatial.to_geocentric(system, [point]))
    assert np.allclose(back[0], point, atol=1e-6, rtol=0)


def meridian_arc(latitude):
    """The meridian's length from the equator to `latitude` degrees on WGS84, integrated"""
    e2 = geospatial.ELLIPSOIDS['WE'].e2
    phi = np.linspace(0.0, np.radians(latitude), 200001)
    radius = WGS84_A * (1 - e2) / (1 - e2 * np.sin(phi) ** 2) ** 1.5
    return float(np.trapezoid(radius, phi))


def test_utm_on_the_central_meridian_is_its_scaled_meridian_arc():
    """Zone 18's central meridian is 75 degrees west"""
    gd = geospatial.system(['GD'])
    utm = geospatial.system(['UTM', 'Z18'])
    found = geospatial.from_geocentric(utm, geospatial.to_geocentric(gd, [(40.0, -75.0, 0.0)]))
    northing, easting, _ = found[0]
    assert easting == pytest.approx(500000.0, abs=1e-6)
    assert northing == pytest.approx(0.9996 * meridian_arc(40.0), abs=1e-4)


def test_up_is_the_ellipsoid_normal():
    gd = geospatial.system(['GD'])
    points = geospatial.to_geocentric(gd, [(0, 0, 0), (90, 0, 0), (45, 0, 0)])
    up = geospatial.up(gd, points)
    assert np.allclose(up[0], (1, 0, 0)) and np.allclose(up[1], (0, 0, 1))
    assert np.allclose(np.linalg.norm(up, axis=1), 1)
    # A geodetic latitude of 45 degrees: the normal is 45 degrees up from the equator
    assert np.degrees(np.arcsin(up[2][2])) == pytest.approx(45.0)


def test_the_local_frame_has_y_up_x_east_and_minus_z_north():
    gd = geospatial.system(['GD'])
    matrix = geospatial.location_matrix(gd, (0.0, 0.0, 0.0))
    assert np.allclose(matrix[0, :3], (0, 1, 0))      # east, along +Y geocentric
    assert np.allclose(matrix[1, :3], (1, 0, 0))      # up
    assert np.allclose(matrix[2, :3], (0, 0, -1))     # south; -Z is north
    assert np.allclose(matrix[3, :3], (WGS84_A, 0, 0))


def test_the_frame_at_a_pole_is_still_a_rotation():
    matrix = geospatial.location_matrix(geospatial.system(['GD']), (90.0, 0.0, 0.0))
    rotation = matrix[:3, :3]
    assert np.allclose(rotation @ rotation.T, np.eye(3))


def test_an_origin_is_subtracted():
    gd = geospatial.system(['GD'])
    origin = geospatial.Origin(gd, (0.0, 0.0, 0.0), rotate_y_up=False)
    local = origin.local(geospatial.to_geocentric(gd, [(0.0, 0.0, 10.0)]))
    assert np.allclose(local[0], (10.0, 0, 0))


def test_rotate_y_up_turns_the_origins_up_to_y():
    gd = geospatial.system(['GD'])
    origin = geospatial.Origin(gd, (45.0, 10.0, 0.0), rotate_y_up=True)
    local = origin.local(geospatial.to_geocentric(gd, [(45.0, 10.0, 25.0)]))
    assert np.allclose(local[0], (0, 25.0, 0), atol=1e-6)
    back = origin.geocentric(local)
    assert np.allclose(back, geospatial.to_geocentric(gd, [(45.0, 10.0, 25.0)]))


@pytest.mark.parametrize('code', sorted(geospatial.ELLIPSOIDS))
def test_every_ellipsoid_is_flattened_a_little(code):
    ellipsoid = geospatial.ELLIPSOIDS[code]
    assert 6.37e6 < ellipsoid.a < 6.38e6 and 290 < ellipsoid.inverse_flattening < 302


def test_a_node_without_an_origin_is_in_geocentric_metres():
    node = x3d.GeoLocation(geoCoords=(0.0, 0.0, 0.0))
    assert geospatial.node_origin(node) is None
    assert np.allclose(geospatial.scene_points(node, [(0.0, 0.0, 0.0)]), [(WGS84_A, 0, 0)])


def test_a_nodes_origin_is_its_geo_origin():
    node = x3d.GeoLocation(geoOrigin=x3d.GeoOrigin(geoCoords=(0.0, 0.0, 0.0)))
    assert np.allclose(geospatial.scene_points(node, [(0.0, 0.0, 5.0)]), [(5.0, 0, 0)])


def test_slerp_keeps_the_height_and_follows_the_globe():
    a = np.array([WGS84_A, 0.0, 0.0])
    b = np.array([0.0, WGS84_A, 0.0])
    middle = geospatial.slerp_points(a, b, 0.5)
    assert np.linalg.norm(middle) == pytest.approx(WGS84_A)
    assert np.allclose(middle / np.linalg.norm(middle), (np.sqrt(0.5), np.sqrt(0.5), 0))


def test_a_geo_position_interpolator_sends_scene_and_geo_coordinates():
    interpolator = PROTOTYPES['GeoPositionInterpolator'](
        key=[0, 1], keyValue=[(0.0, 0.0, 0.0), (0.0, 90.0, 0.0)],
        geoOrigin=x3d.GeoOrigin(geoCoords=(0.0, 0.0, 0.0)))
    interpolator.on_set_fraction(0.5)
    assert np.allclose(interpolator.geovalue_changed, (0.0, 45.0, 0.0), atol=1e-9)
    local = np.asarray(interpolator.value_changed)
    expected = geospatial.to_geocentric(geospatial.system(['GD']), [(0.0, 45.0, 0.0)])[0]
    assert np.allclose(local + (WGS84_A, 0, 0), expected, atol=0.5)



def test_a_geodetic_grid_steps_longitude_across_and_latitude_deep():
    found = geospatial.grid_coordinates(geospatial.system(['GD']), (10, 20, 5), 3, 2,
                                        0.5, 0.25, [0, 1, 2, 3, 4, 5], 2.0)
    assert found.tolist() == [[10, 20, 5], [10, 20.5, 7], [10, 21, 9],
                              [10.25, 20, 11], [10.25, 20.5, 13], [10.25, 21, 15]]


@pytest.mark.parametrize('names', [['GD', 'longitude_first'], ['UTM', 'Z10', 'easting_first']])
def test_a_grid_in_the_other_order_steps_its_first_coordinate_across(names):
    found = geospatial.grid_coordinates(geospatial.system(names), (20, 10, 0), 2, 2,
                                        0.5, 0.25, [0, 0, 0, 0], 1.0)
    assert found[:, :2].tolist() == [[20, 10], [20.5, 10], [20, 10.25], [20.5, 10.25]]


def test_a_utm_grid_steps_easting_across_and_northing_deep():
    found = geospatial.grid_coordinates(geospatial.system(['UTM', 'Z10']), (4000000, 500000, 0),
                                        2, 2, 30, 30, [0, 0, 0, 0], 1.0)
    assert found[:, :2].tolist() == [[4000000, 500000], [4000000, 500030],
                                     [4000030, 500000], [4000030, 500030]]


def test_a_grid_short_of_heights_is_flat_where_they_are_missing():
    found = geospatial.grid_coordinates(geospatial.system(['GD']), (0, 0, 1), 2, 2,
                                        1, 1, [4], 1.0)
    assert found[:, 2].tolist() == [5, 1, 1, 1]


@pytest.mark.parametrize('names', [['GD'], ['UTM', 'Z31'], ['GC']])
def test_an_elevation_is_the_height_above_the_nodes_ellipsoid(names):
    node = x3d.GeoViewpoint(geoSystem=names,
                            geoOrigin=x3d.GeoOrigin(geoCoords=(0.0, 0.0, 0.0)))
    assert geospatial.elevations(node, [(250.0, 0.0, 0.0), (0.0, 0.0, 0.0)]) == pytest.approx(
        [250.0, 0.0], abs=1e-6)
