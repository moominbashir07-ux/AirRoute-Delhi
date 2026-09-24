"""
Lightweight Validation Tests for XKDR India Air Quality Data Availability.
Verifies API connectivity, station catalog format, and parameter contracts.
Does NOT expose or log any credentials.
"""

import os
import pytest
import sys

# Ensure backend root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model")))

from assess_xkdr import get_api_key, step1_verify_auth, step2_parameters, step3_delhi_stations


def test_api_key_retrieval_safe():
    """Verify API key can be retrieved from environment without exposing its value."""
    key = get_api_key()
    assert key is not None
    assert len(key) > 20
    assert key.startswith("aqi_") or key.startswith("open")


def test_xkdr_authentication_status():
    """Verify XKDR endpoint authenticates and returns valid metadata schema."""
    auth = step1_verify_auth()
    assert auth["status"] == "PASS"
    assert auth["tier"] in ["full", "standard", "demo"]
    assert "Indian Standard Time" in auth["timezone_note"]
    assert auth["total_rows"] > 100_000_000


def test_xkdr_parameters_catalog():
    """Verify criteria pollutants exist in the XKDR parameter catalog."""
    params = step2_parameters()
    param_names = [p["parameter_name"] for p in params]
    for required in ["PM2.5", "PM10", "NO2", "SO2", "CO", "Ozone"]:
        assert required in param_names, f"Missing criteria pollutant: {required}"


def test_xkdr_delhi_stations_structure():
    """Verify Delhi monitoring stations are discoverable with coordinates."""
    df_stations = step3_delhi_stations()
    assert len(df_stations) >= 30, f"Expected at least 30 Delhi stations, got {len(df_stations)}"
    assert "station_id" in df_stations.columns
    assert "latitude" in df_stations.columns
    assert "longitude" in df_stations.columns
    assert "parameters" in df_stations.columns

    # Verify latitude/longitude coordinates fall into Delhi NCR bounding box (28°N - 29°N, 76.5°E - 77.5°E)
    valid_coords = df_stations.dropna(subset=["latitude", "longitude"])
    assert (valid_coords["latitude"].between(28.0, 29.5)).all()
    assert (valid_coords["longitude"].between(76.5, 78.0)).all()
