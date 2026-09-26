"""Mandatory Leakage Prevention Tests for Phase 3C Feature Engineering.

Explicitly verifies that future observations (t+1, t+2, ...) have ZERO influence
on features generated at time t.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ml_model.temporal_features import compute_station_temporal_features


def test_mandatory_future_observation_invariance():
    """MANDATORY AUDIT TEST:
    Construct two datasets identical up to time t.
    At time t+1, introduce a radical, catastrophic difference in PM2.5 (e.g., 50.0 vs 999.0).
    Verify that ALL generated features at time t remain EXACTLY IDENTICAL down to float bit precision.
    """
    base_time = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    timestamps = [base_time + timedelta(hours=i) for i in range(24)]

    # Historical values up to t = 22 (index 0 to 22)
    historical_pm25 = [float(50 + (i % 10)) for i in range(23)]

    # Dataset A: normal future value at t=23 (t+1)
    rows_a = [{"station_id": "site_leakage_test", "timestamp_utc": ts, "pm25": val}
              for ts, val in zip(timestamps[:23], historical_pm25)]
    rows_a.append({"station_id": "site_leakage_test", "timestamp_utc": timestamps[23], "pm25": 55.0})
    df_a = pd.DataFrame(rows_a)

    # Dataset B: radical, extreme anomaly at t=23 (t+1)
    rows_b = [{"station_id": "site_leakage_test", "timestamp_utc": ts, "pm25": val}
              for ts, val in zip(timestamps[:23], historical_pm25)]
    rows_b.append({"station_id": "site_leakage_test", "timestamp_utc": timestamps[23], "pm25": 999.0})
    df_b = pd.DataFrame(rows_b)

    features_a = compute_station_temporal_features(df_a, "site_leakage_test")
    features_b = compute_station_temporal_features(df_b, "site_leakage_test")

    # Sort strictly by timestamp
    features_a = features_a.sort_values("timestamp_utc").reset_index(drop=True)
    features_b = features_b.sort_values("timestamp_utc").reset_index(drop=True)

    # Check time t = 22 (the hour immediately preceding the divergence at t+1 = 23)
    t_idx = 22
    row_a_at_t = features_a.loc[t_idx]
    row_b_at_t = features_b.loc[t_idx]

    assert row_a_at_t["timestamp_utc"] == timestamps[22]
    assert row_b_at_t["timestamp_utc"] == timestamps[22]

    feature_cols = [
        "pm25_lag_1h", "pm25_lag_2h", "pm25_lag_3h", "pm25_lag_6h", "pm25_lag_12h",
        "pm25_rolling_mean_3h", "pm25_rolling_mean_6h", "pm25_rolling_mean_12h",
        "hour_of_day_sin", "hour_of_day_cos", "day_of_week"
    ]

    for col in feature_cols:
        val_a = row_a_at_t[col]
        val_b = row_b_at_t[col]
        if np.isnan(val_a):
            assert np.isnan(val_b), f"Leakage failure on {col}: NaN mismatch at time t."
        else:
            assert val_a == val_b, (
                f"DATA LEAKAGE DETECTED in {col}! Feature at time t changed from {val_a} to {val_b} "
                f"when future value at t+1 was modified."
            )


def test_no_future_leakage_across_entire_historical_prefix():
    """Verify that truncating the future entirely does not alter features at any historical timestamp."""
    base_time = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    full_times = [base_time + timedelta(hours=i) for i in range(48)]
    full_pm25 = [float(100 + i * 2) for i in range(48)]

    df_full = pd.DataFrame([
        {"station_id": "test_leak", "timestamp_utc": ts, "pm25": val}
        for ts, val in zip(full_times, full_pm25)
    ])

    # Truncated dataset containing only the first 24 hours
    df_truncated = df_full.iloc[:24].copy()

    features_full = compute_station_temporal_features(df_full, "test_leak").sort_values("timestamp_utc").reset_index(drop=True)
    features_trunc = compute_station_temporal_features(df_truncated, "test_leak").sort_values("timestamp_utc").reset_index(drop=True)

    # For the first 24 rows, features MUST match identically between full and truncated
    feature_cols = [
        "pm25_lag_1h", "pm25_lag_2h", "pm25_lag_3h", "pm25_lag_6h",
        "pm25_rolling_mean_3h", "pm25_rolling_mean_6h", "pm25_rolling_mean_12h"
    ]

    for i in range(24):
        for col in feature_cols:
            val_full = features_full.loc[i, col]
            val_trunc = features_trunc.loc[i, col]
            if np.isnan(val_full):
                assert np.isnan(val_trunc)
            else:
                assert val_full == val_trunc, f"Mismatch at hour {i} on {col}: {val_full} vs {val_trunc}"
