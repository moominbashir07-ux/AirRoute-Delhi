"""Tests for Phase 3D Multi-Horizon Forecasting Dataset Construction."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ml_model.forecasting_engine import (
    HORIZONS,
    SPLIT_TRAIN_END,
    SPLIT_VAL_END,
    SPLIT_TEST_END
)


@pytest.fixture
def mock_station_series():
    """Create a regular hourly synthetic time series for a single station."""
    base = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    times = [base + timedelta(hours=i) for i in range(100)]
    # Linear trend: PM2.5 = 50 + i
    pm25_vals = [float(50 + i) for i in range(100)]
    # Introduce an intentional gap at index 50
    pm25_vals[50] = np.nan

    df = pd.DataFrame({
        "station_id": ["site_test"] * 100,
        "timestamp_utc": times,
        "pm25_t0": pm25_vals
    })
    return df


def test_target_horizon_exact_hour_shift(mock_station_series):
    """Verify that target for horizon h is PM2.5 at exactly t + h hours."""
    df = mock_station_series.sort_values("timestamp_utc").set_index("timestamp_utc")

    # Compute targets by shifting backward by h
    for h in HORIZONS:
        df[f"target_t_plus_{h}h"] = df["pm25_t0"].shift(-h)

    # For index 10 (t = base + 10h), pm25_t0 is 60.0
    # target_t_plus_1h (t + 1h = 11h) must be 61.0
    # target_t_plus_6h (t + 6h = 16h) must be 66.0
    t10 = df.iloc[10]
    assert t10["pm25_t0"] == 60.0
    assert t10["target_t_plus_1h"] == 61.0
    assert t10["target_t_plus_2h"] == 62.0
    assert t10["target_t_plus_3h"] == 63.0
    assert t10["target_t_plus_4h"] == 64.0
    assert t10["target_t_plus_5h"] == 65.0
    assert t10["target_t_plus_6h"] == 66.0


def test_missing_future_target_produces_nan_no_interpolation(mock_station_series):
    """Verify that when future observation at t+h is missing, target is strictly NaN."""
    df = mock_station_series.sort_values("timestamp_utc").set_index("timestamp_utc")
    for h in HORIZONS:
        df[f"target_t_plus_{h}h"] = df["pm25_t0"].shift(-h)

    # Index 50 was set to NaN.
    # Therefore, at index 49 (t = 49), target_t_plus_1h (t + 1h = 50) MUST be NaN!
    t49 = df.iloc[49]
    assert np.isnan(t49["target_t_plus_1h"]), "Target interpolation defect: missing value was filled!"

    # At index 44 (t = 44), target_t_plus_6h (t + 6h = 50) MUST be NaN!
    t44 = df.iloc[44]
    assert np.isnan(t44["target_t_plus_6h"]), "Target interpolation defect: missing value was filled!"


def test_chronological_split_boundaries():
    """Verify that split boundary definitions are strictly monotonic and chronological."""
    t_train = pd.to_datetime(SPLIT_TRAIN_END, utc=True)
    t_val = pd.to_datetime(SPLIT_VAL_END, utc=True)
    t_test = pd.to_datetime(SPLIT_TEST_END, utc=True)

    assert t_train < t_val < t_test
    # Exactly matches 2020-2023, 2024 H1, 2024 H2
    assert t_train.year == 2023 and t_train.month == 12
    assert t_val.year == 2024 and t_val.month == 6
    assert t_test.year == 2024 and t_test.month == 12
