"""Tests for Phase 3C Corridor Geometry and Coordinate Validation."""

import pytest
import math
from ml_model.corridor_geometry import (
    validate_coordinates,
    haversine_distance,
    calculate_bearing,
    generate_corridor_id,
    discretize_corridor,
    EARTH_RADIUS_KM
)


def test_valid_wgs84_coordinates():
    is_valid, err = validate_coordinates(28.6139, 77.2090)
    assert is_valid is True
    assert err is None


def test_invalid_latitude_bounds():
    is_valid, err = validate_coordinates(95.0, 77.2090)
    assert is_valid is False
    assert "Latitude 95.0 out of physical bounds" in err

    is_valid_neg, err_neg = validate_coordinates(-90.1, 77.2090)
    assert is_valid_neg is False
    assert "out of physical bounds" in err_neg


def test_invalid_longitude_bounds():
    is_valid, err = validate_coordinates(28.6139, 185.0)
    assert is_valid is False
    assert "Longitude 185.0 out of physical bounds" in err

    is_valid_neg, err_neg = validate_coordinates(28.6139, -181.0)
    assert is_valid_neg is False
    assert "out of physical bounds" in err_neg


def test_nan_and_inf_coordinates():
    is_valid, err = validate_coordinates(float("nan"), 77.2)
    assert is_valid is False
    assert "cannot be NaN or infinite" in err

    is_valid_inf, err_inf = validate_coordinates(28.6, float("inf"))
    assert is_valid_inf is False
    assert "cannot be NaN or infinite" in err_inf


def test_haversine_same_point_zero_distance():
    lat, lon = 28.6139, 77.2090
    dist = haversine_distance(lat, lon, lat, lon)
    assert dist == 0.0


def test_haversine_known_delhi_distance():
    # Connaught Place (28.6315, 77.2167) to India Gate (28.6129, 77.2295)
    # Expected great-circle distance is approx 2.40 km
    dist = haversine_distance(28.6315, 77.2167, 28.6129, 77.2295)
    assert 2.2 < dist < 2.6
    assert isinstance(dist, float)
    assert dist >= 0.0


def test_bearing_calculation_and_normalization():
    # North: from (28.0, 77.0) to (29.0, 77.0)
    b_north = calculate_bearing(28.0, 77.0, 29.0, 77.0)
    assert abs(b_north - 0.0) < 0.1 or abs(b_north - 360.0) < 0.1

    # East: from (28.0, 77.0) to (28.0, 78.0)
    b_east = calculate_bearing(28.0, 77.0, 28.0, 78.0)
    assert 85.0 < b_east < 95.0

    # South: from (29.0, 77.0) to (28.0, 77.0)
    b_south = calculate_bearing(29.0, 77.0, 28.0, 77.0)
    assert 175.0 < b_south < 185.0

    # West: from (28.0, 78.0) to (28.0, 77.0)
    b_west = calculate_bearing(28.0, 78.0, 28.0, 77.0)
    assert 265.0 < b_west < 275.0

    # Same point bearing returns 0.0
    b_same = calculate_bearing(28.6, 77.2, 28.6, 77.2)
    assert b_same == 0.0


def test_deterministic_corridor_id():
    id1 = generate_corridor_id(28.6315, 77.2167, 28.4950, 77.0895, 1.0)
    id2 = generate_corridor_id(28.6315, 77.2167, 28.4950, 77.0895, 1.0)
    assert id1 == id2
    assert id1.startswith("corr_")

    id_diff = generate_corridor_id(28.6315, 77.2167, 28.5000, 77.0895, 1.0)
    assert id1 != id_diff


def test_discretize_identical_origin_and_destination():
    segments = discretize_corridor(28.6139, 77.2090, 28.6139, 77.2090, segment_length_km=1.0)
    assert len(segments) == 1
    seg = segments[0]
    assert seg["segment_index"] == 0
    assert seg["segment_length_km"] == 0.0
    assert seg["bearing_degrees"] == 0.0
    assert seg["is_single_point"] is True
    assert seg["midpoint_latitude"] == 28.6139
    assert seg["midpoint_longitude"] == 77.2090


def test_discretize_short_corridor():
    # 200m corridor (less than 1.0 km step)
    orig_lat, orig_lon = 28.6315, 77.2167
    dest_lat, dest_lon = 28.6330, 77.2180
    dist = haversine_distance(orig_lat, orig_lon, dest_lat, dest_lon)
    assert dist < 0.5

    segments = discretize_corridor(orig_lat, orig_lon, dest_lat, dest_lon, segment_length_km=1.0)
    assert len(segments) == 1
    assert segments[0]["segment_index"] == 0
    assert 0.0 < segments[0]["segment_length_km"] < 0.5


def test_discretize_standard_corridor():
    # ~20km corridor
    orig_lat, orig_lon = 28.6315, 77.2167
    dest_lat, dest_lon = 28.4950, 77.0895
    total_dist = haversine_distance(orig_lat, orig_lon, dest_lat, dest_lon)

    segments = discretize_corridor(orig_lat, orig_lon, dest_lat, dest_lon, segment_length_km=1.0)
    expected_segments = max(1, int(math.ceil(total_dist / 1.0)))
    assert len(segments) == expected_segments

    # Check continuity of segments
    for i in range(len(segments) - 1):
        assert segments[i]["segment_index"] == i
        assert segments[i]["end_latitude"] == segments[i + 1]["start_latitude"]
        assert segments[i]["end_longitude"] == segments[i + 1]["start_longitude"]
        assert segments[i]["segment_length_km"] > 0.0
        assert 0.0 <= segments[i]["bearing_degrees"] < 360.0
