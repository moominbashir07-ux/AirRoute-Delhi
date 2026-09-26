"""Tests for Phase 3C Station Spatial Matching and Tie-breaking."""

import pytest
import pandas as pd
from ml_model.corridor_geometry import StationSpatialIndex, DEFAULT_MAX_STATION_DISTANCE_KM


@pytest.fixture
def spatial_index():
    return StationSpatialIndex()


def test_station_catalog_loaded_and_ids_preserved(spatial_index):
    assert spatial_index.count() == 42
    # Verify known station IDs exist unaltered
    assert "DS1010001" in spatial_index.station_ids
    assert "site_113" in spatial_index.station_ids
    assert "site_117" in spatial_index.station_ids


def test_nearest_station_exact_station_coordinate(spatial_index):
    # Match at the exact coordinates of ITO (site_117: 28.628624, 77.24106)
    match = spatial_index.nearest_station(28.628624, 77.24106, max_distance_km=10.0)
    assert match["match_status"] == "VALID_MATCH"
    assert match["station_id"] == "site_117"
    assert match["distance_km"] < 0.01
    assert match["backup_station_id"] is not None
    assert match["backup_distance_km"] > match["distance_km"]


def test_nearest_station_max_distance_threshold_enforced(spatial_index):
    # A remote point outside NCR, e.g., Jaipur (26.9124, 75.7873)
    # Distance to Delhi will be > 200 km
    match = spatial_index.nearest_station(26.9124, 75.7873, max_distance_km=10.0)
    assert match["match_status"] == "NO_VALID_STATION"
    assert match["station_id"] is None
    assert match["station_name"] is None
    assert match["distance_km"] > 10.0
    assert match["nearest_candidate_station_id"] is not None


def test_invalid_coordinates_handled_gracefully(spatial_index):
    match = spatial_index.nearest_station(999.0, 77.2, max_distance_km=10.0)
    assert match["match_status"] == "INVALID_COORDINATES"
    assert match["station_id"] is None
    assert "error_message" in match


def test_deterministic_tie_breaking():
    # Construct a synthetic spatial index with two stations at identical distance from origin
    df_synthetic = pd.DataFrame([
        {
            "station_id": "site_Z999",
            "station_name": "Station Z",
            "latitude": 28.6000,
            "longitude": 77.2000,
            "source": "mock"
        },
        {
            "station_id": "site_A001",
            "station_name": "Station A",
            "latitude": 28.6000,
            "longitude": 77.2000,
            "source": "mock"
        }
    ])
    index_syn = StationSpatialIndex(stations_df=df_synthetic)
    # Query at identical coordinates
    match = index_syn.nearest_station(28.6000, 77.2000)
    # Must deterministically select site_A001 because 'site_A001' < 'site_Z999' lexicographically
    assert match["station_id"] == "site_A001"
    assert match["backup_station_id"] == "site_Z999"


def test_map_corridor_segments(spatial_index):
    segments = [
        {
            "corridor_id": "test_corr",
            "segment_index": 0,
            "start_latitude": 28.6315,
            "start_longitude": 77.2167,
            "end_latitude": 28.6250,
            "end_longitude": 77.2150,
            "midpoint_latitude": 28.6282,
            "midpoint_longitude": 77.2158,
            "segment_length_km": 0.8,
            "bearing_degrees": 190.0,
            "is_single_point": False
        }
    ]
    mapped = spatial_index.map_corridor_segments(segments, max_distance_km=10.0)
    assert len(mapped) == 1
    m = mapped[0]
    assert "nearest_station_id" in m
    assert "station_match_status" in m
    assert m["station_match_status"] == "VALID_MATCH"
    assert m["station_distance_km"] < 10.0
    assert m["backup_station_id"] is not None
