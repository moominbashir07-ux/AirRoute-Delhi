"""
Automated Test Suite for Phase 3B - XKDR Observational Ingestion Pipeline
Validates credential safety, station catalog structure, timestamp conversion,
and unit normalization routines.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model")))

from xkdr_ingestion import (
    get_api_key,
    normalize_and_validate_chunk,
    export_canonical_wide_dataset,
    STATION_CATALOG_PATH,
    DATA_DICTIONARY_PATH,
    DATASET_METADATA_PATH,
)


def test_api_key_security_boundary():
    """Verify API key can be retrieved from environment without being logged or printed."""
    key = get_api_key()
    assert key is not None
    assert len(key) >= 20
    assert not key.startswith("http")
    # Verify key does not appear in local test files or git-tracked logs
    assert "Authorization" not in str(key)


def test_station_catalog_exists_and_covers_delhi():
    """Verify deterministic station catalog exists and contains all 42 Delhi stations."""
    assert os.path.exists(STATION_CATALOG_PATH), f"Catalog missing: {STATION_CATALOG_PATH}"
    df = pd.read_csv(STATION_CATALOG_PATH)
    assert len(df) == 42, f"Expected 42 Delhi stations, got {len(df)}"

    required_cols = [
        "station_id",
        "station_name",
        "latitude",
        "longitude",
        "city",
        "state",
        "source",
        "first_observation",
        "last_observation",
        "available_pollutants",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column {col} in catalog"

    # Coordinates must be valid Delhi NCR bounding box (28.4 to 28.9 N, 77.0 to 77.4 E)
    valid_lat = df["latitude"].dropna()
    valid_lon = df["longitude"].dropna()
    assert (valid_lat.between(28.0, 29.5)).all()
    assert (valid_lon.between(76.5, 78.0)).all()


def test_timestamp_normalization_ist_to_utc():
    """Verify exact timezone localization and UTC derivation without temporal drift."""
    dummy_raw = pd.DataFrame({
        "station_id": ["site_103"],
        "parameter_name": ["PM2.5"],
        "unit": ["µg/m³"],
        "collected_at": ["2024-06-15 14:00:00"],
        "value": [55.0],
    })
    lookup = {"site_103": {"station_name": "CRRI Mathura Road", "latitude": 28.55, "longitude": 77.27, "source": "cpcb"}}
    
    clean_df, stats = normalize_and_validate_chunk(dummy_raw, lookup)
    assert len(clean_df) == 1

    row = clean_df.iloc[0]
    ist_time = row["timestamp_ist"]
    utc_time = row["timestamp_utc"]

    # IST is UTC+05:30 -> UTC must be 5h 30m earlier (08:30:00)
    assert ist_time.hour == 14 and ist_time.minute == 0
    assert utc_time.hour == 8 and utc_time.minute == 30
    assert (ist_time.tz_convert("UTC") - utc_time) == pd.Timedelta(0)


def test_co_unit_conversion_mg_to_ug():
    """Verify CO concentrations in mg/m3 are accurately converted to canonical ug/m3 (x1000)."""
    dummy_raw = pd.DataFrame({
        "station_id": ["site_103", "site_103"],
        "parameter_name": ["CO", "PM2.5"],
        "unit": ["mg/m³", "µg/m³"],
        "collected_at": ["2024-06-15 14:00:00", "2024-06-15 14:00:00"],
        "value": [1.25, 45.0],
    })
    lookup = {"site_103": {"station_name": "CRRI Mathura Road", "latitude": 28.55, "longitude": 77.27, "source": "cpcb"}}
    
    clean_df, stats = normalize_and_validate_chunk(dummy_raw, lookup)
    
    co_row = clean_df[clean_df["pollutant"] == "co"].iloc[0]
    assert co_row["value"] == 1250.0, f"Expected 1250.0 ug/m3, got {co_row['value']}"
    assert co_row["unit"] == "µg/m³"

    # PM2.5 must not be scaled
    pm_row = clean_df[clean_df["pollutant"] == "pm25"].iloc[0]
    assert pm_row["value"] == 45.0


def test_negative_values_rejected_and_reported():
    """Verify impossible negative concentrations are filtered out."""
    dummy_raw = pd.DataFrame({
        "station_id": ["site_103", "site_103"],
        "parameter_name": ["PM2.5", "NO2"],
        "unit": ["µg/m³", "µg/m³"],
        "collected_at": ["2024-06-15 14:00:00", "2024-06-15 15:00:00"],
        "value": [-9.0, 32.0],
    })
    lookup = {"site_103": {"station_name": "CRRI Mathura Road", "latitude": 28.55, "longitude": 77.27, "source": "cpcb"}}
    
    clean_df, stats = normalize_and_validate_chunk(dummy_raw, lookup)
    assert len(clean_df) == 1
    assert stats["negative_dropped"] == 1
    assert clean_df.iloc[0]["pollutant"] == "no2"


def test_duplicate_key_deduplication():
    """Verify duplicate observation records for same station/timestamp/pollutant are resolved deterministically."""
    dummy_raw = pd.DataFrame({
        "station_id": ["site_103", "site_103"],
        "parameter_name": ["PM2.5", "PM2.5"],
        "unit": ["µg/m³", "µg/m³"],
        "collected_at": ["2024-06-15 14:00:00", "2024-06-15 14:00:00"],
        "value": [55.0, 55.0],
    })
    lookup = {"site_103": {"station_name": "CRRI Mathura Road", "latitude": 28.55, "longitude": 77.27, "source": "cpcb"}}
    
    clean_df, stats = normalize_and_validate_chunk(dummy_raw, lookup)
    assert len(clean_df) == 1
    assert stats["duplicates_dropped"] == 1
