"""
Automated Test Suite for Phase 3B - Observational Data Quality & Schema Integrity
Audits the serialized Parquet dataset on disk, verifying schema contracts,
missingness preservation (no synthetic interpolation), and data consistency.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model")))

from xkdr_ingestion import (
    PARQUET_DATASET_PATH,
    QUALITY_REPORT_PATH,
    DATASET_METADATA_PATH,
    DATA_DICTIONARY_PATH,
    COVERAGE_REPORT_PATH,
)


@pytest.fixture(scope="module")
def dataset_df():
    assert os.path.exists(PARQUET_DATASET_PATH), f"Missing dataset: {PARQUET_DATASET_PATH}"
    df = pd.read_parquet(PARQUET_DATASET_PATH)
    return df


@pytest.fixture(scope="module")
def quality_metadata():
    assert os.path.exists(QUALITY_REPORT_PATH)
    with open(QUALITY_REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_parquet_dataset_exists_and_is_substantial(dataset_df):
    """Verify serialized observational dataset contains comprehensive 5-year coverage (>1,500,000 station hours)."""
    assert len(dataset_df) >= 1_500_000, f"Expected >= 1.5M station hours, got {len(dataset_df)}"
    assert dataset_df["station_id"].nunique() == 42, f"Expected 42 stations, got {dataset_df['station_id'].nunique()}"


def test_canonical_wide_schema_and_types(dataset_df):
    """Verify canonical column order, presence, and types."""
    expected_cols = [
        "timestamp_utc",
        "timestamp_ist",
        "station_id",
        "station_name",
        "latitude",
        "longitude",
        "pm25",
        "pm10",
        "no2",
        "so2",
        "co",
        "o3",
    ]
    assert dataset_df.columns.tolist() == expected_cols

    # Verify timestamp awareness
    assert dataset_df["timestamp_utc"].dt.tz is not None
    assert dataset_df["timestamp_ist"].dt.tz is not None


def test_strict_zero_interpolation_missingness_preserved(dataset_df):
    """Verify that missing observations remain NaN and were never artificially interpolated."""
    pollutants = ["pm25", "pm10", "no2", "so2", "co", "o3"]
    for p in pollutants:
        null_count = dataset_df[p].isnull().sum()
        # In physical monitoring networks, missing values naturally exist due to calibrations and maintenance
        assert null_count > 0, f"Pollutant {p} unexpectedly has zero null values (possible interpolation leakage)"
        assert null_count < len(dataset_df), f"Pollutant {p} is entirely null"


def test_zero_duplicates_on_canonical_key(dataset_df):
    """Verify that no duplicate (station_id, timestamp_utc) observations exist."""
    dups = dataset_df.duplicated(subset=["station_id", "timestamp_utc"]).sum()
    assert dups == 0, f"Found {dups} duplicate timestamp records per station"


def test_zero_impossible_negative_values(dataset_df):
    """Verify that no negative pollutant concentrations exist in analytical cache."""
    pollutants = ["pm25", "pm10", "no2", "so2", "co", "o3"]
    for p in pollutants:
        negatives = (dataset_df[p] < 0).sum()
        assert negatives == 0, f"Found {negatives} negative values in {p}"


def test_co_concentration_scaling(dataset_df):
    """Verify CO values reflect canonical micrograms per cubic meter (mean between 500 and 3000 ug/m3)."""
    co_vals = dataset_df["co"].dropna()
    assert 500.0 < co_vals.mean() < 3000.0, f"CO mean {co_vals.mean()} indicates incorrect unit normalization"


def test_provenance_and_dictionary_metadata(quality_metadata):
    """Verify provenance metadata, data dictionary, and quality reports match dataset."""
    assert os.path.exists(DATASET_METADATA_PATH)
    assert os.path.exists(DATA_DICTIONARY_PATH)
    assert os.path.exists(COVERAGE_REPORT_PATH)

    with open(DATASET_METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["dataset_version"] == "xkdr_delhi_2020_2024_v1"
    assert meta["station_count"] == 42
    assert "Authorization" not in str(meta)
    assert "aqi_" not in str(meta)

    # Cross-verify row count with quality report
    assert quality_metadata["total_wide_rows"] == 1_732_402
    assert quality_metadata["station_count"] == 42
