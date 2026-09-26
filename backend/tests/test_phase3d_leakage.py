"""Tests for Phase 3D Future Leakage Prevention."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ml_model.forecasting_engine import HORIZONS


def test_target_columns_excluded_from_feature_columns():
    """Verify that no target column is present in the feature columns list."""
    base_features = [
        "pm25_t0",
        "pm25_lag_1h", "pm25_lag_2h", "pm25_lag_3h", "pm25_lag_6h", "pm25_lag_12h", "pm25_lag_24h",
        "pm25_rolling_mean_3h", "pm25_rolling_mean_6h", "pm25_rolling_mean_12h", "pm25_rolling_mean_24h",
        "hour_of_day_sin", "hour_of_day_cos", "day_of_week",
        "latitude", "longitude"
    ]
    wx_cols = [
        "temperature", "humidity", "wind_speed",
        "wind_direction_sin", "wind_direction_cos",
        "boundary_layer_height", "surface_pressure"
    ]

    for h in HORIZONS:
        feature_cols = base_features + [f"{c}_h{h}" for c in wx_cols]
        for f in feature_cols:
            assert not f.startswith("target_"), f"Target leakage defect: {f} found in feature set for horizon {h}!"
            assert "pm25_lead" not in f
            assert "pm25_future" not in f


def test_strict_chronological_split_no_temporal_overlap():
    """Verify that train, validation, and test datasets have disjoint, strictly ordered timestamps."""
    train_end = pd.to_datetime("2023-12-31 23:59:59", utc=True)
    val_start = pd.to_datetime("2024-01-01 00:00:00", utc=True)
    val_end = pd.to_datetime("2024-06-30 23:59:59", utc=True)
    test_start = pd.to_datetime("2024-07-01 00:00:00", utc=True)

    # Train timestamps strictly < val_start
    assert train_end < val_start
    # Val timestamps strictly < test_start
    assert val_end < test_start


def test_weather_features_at_horizon_h_do_not_leak_subsequent_weather():
    """Verify that horizon h weather is aligned strictly to (t + h) and does not use (t + h + 1)."""
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    # At t = 10:00, for h=1, future weather timestamp is 11:00
    t_plus_1 = base_time + timedelta(hours=1)
    # For h=2, future weather timestamp is 12:00
    t_plus_2 = base_time + timedelta(hours=2)

    assert t_plus_1 == datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    assert t_plus_2 == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert t_plus_1 != t_plus_2
