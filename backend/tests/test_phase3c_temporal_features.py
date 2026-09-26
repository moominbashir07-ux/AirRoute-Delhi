"""Tests for Phase 3C Temporal Feature Engineering."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ml_model.temporal_features import (
    compute_station_temporal_features,
    get_feature_metadata_catalog
)


@pytest.fixture
def sample_station_data():
    """Create a controlled station observation series with an intentional 1-hour gap."""
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    # Timestamps: 10:00, 11:00, 12:00, [13:00 missing gap], 14:00, 15:00
    rows = [
        {"station_id": "test_st", "timestamp_utc": base_time, "pm25": 100.0},
        {"station_id": "test_st", "timestamp_utc": base_time + timedelta(hours=1), "pm25": 110.0},
        {"station_id": "test_st", "timestamp_utc": base_time + timedelta(hours=2), "pm25": 120.0},
        # Gap at hours=3 (13:00 UTC is missing)
        {"station_id": "test_st", "timestamp_utc": base_time + timedelta(hours=4), "pm25": 140.0},
        {"station_id": "test_st", "timestamp_utc": base_time + timedelta(hours=5), "pm25": 150.0},
    ]
    return pd.DataFrame(rows)


def test_exact_contiguous_lag_and_gap_handling(sample_station_data):
    features = compute_station_temporal_features(sample_station_data, "test_st")

    # Sort by timestamp_utc
    features = features.sort_values("timestamp_utc").reset_index(drop=True)

    # Row 0: 10:00 -> lag_1h must be NaN (no t-1h in history)
    assert np.isnan(features.loc[0, "pm25_lag_1h"])

    # Row 1: 11:00 -> lag_1h must be 100.0 (from 10:00)
    assert features.loc[1, "pm25_lag_1h"] == 100.0

    # Row 2: 12:00 -> lag_1h = 110.0, lag_2h = 100.0
    assert features.loc[2, "pm25_lag_1h"] == 110.0
    assert features.loc[2, "pm25_lag_2h"] == 100.0

    # Row 3: 14:00 (after the missing 13:00 gap)
    # CRITICAL: pm25_lag_1h must be NaN because 13:00 was MISSING!
    # It must NOT substitute 12:00 (120.0) as lag_1h!
    assert np.isnan(features.loc[3, "pm25_lag_1h"]), "Contiguous-lag requirement failed: 1h gap was filled!"
    # But lag_2h from 14:00 is 12:00 (120.0), which exists!
    assert features.loc[3, "pm25_lag_2h"] == 120.0

    # Row 4: 15:00 -> lag_1h is 14:00 (140.0)
    assert features.loc[4, "pm25_lag_1h"] == 140.0
    # lag_2h is 13:00, which is missing, so must be NaN!
    assert np.isnan(features.loc[4, "pm25_lag_2h"])


def test_causal_rolling_mean_strictly_historical(sample_station_data):
    features = compute_station_temporal_features(sample_station_data, "test_st")
    features = features.sort_values("timestamp_utc").reset_index(drop=True)

    # Row 2: 12:00 (observations at 10:00=100, 11:00=110, 12:00=120)
    # 3-hour backward window: mean(100, 110, 120) = 110.0
    assert pytest.approx(features.loc[2, "pm25_rolling_mean_3h"], 0.01) == 110.0

    # Does not include 14:00 or 15:00
    assert features.loc[2, "pm25_rolling_mean_3h"] < 130.0


def test_cyclical_calendar_features(sample_station_data):
    features = compute_station_temporal_features(sample_station_data, "test_st")
    assert "hour_of_day_sin" in features.columns
    assert "hour_of_day_cos" in features.columns
    assert "day_of_week" in features.columns

    # -1.0 <= sin/cos <= 1.0
    assert (features["hour_of_day_sin"] >= -1.0).all() and (features["hour_of_day_sin"] <= 1.0).all()
    assert (features["hour_of_day_cos"] >= -1.0).all() and (features["hour_of_day_cos"] <= 1.0).all()
    assert (features["day_of_week"] >= 0).all() and (features["day_of_week"] <= 6).all()


def test_feature_metadata_catalog_integrity():
    catalog = get_feature_metadata_catalog()
    assert "pm25_lag_1h" in catalog
    assert "pm25_rolling_mean_6h" in catalog
    assert "hour_of_day_sin" in catalog
    assert "temperature_t_plus_1h" in catalog

    for feat_name, meta in catalog.items():
        assert "name" in meta
        assert "type" in meta
        assert "unit" in meta
        assert "source" in meta
        assert "description" in meta
        assert "future_leakage_risk" in meta
        assert meta["future_leakage_risk"] is False
