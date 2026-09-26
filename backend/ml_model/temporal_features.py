"""Phase 3C: Temporal Feature Engineering & Contiguous Lag Pipeline.

Computes exact backward-looking causal lag features, causal rolling means,
and cyclical calendar features on observational monitoring data.
Strictly enforces no future data leakage and zero nearest-time substitution.
"""

import math
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
import numpy as np

LAG_HOURS = [1, 2, 3, 6, 12, 24]
ROLLING_WINDOWS_HOURS = [3, 6, 12, 24]

# Minimum required observation fractions for causal rolling means
MIN_PERIOD_FRACTION = 0.50


def compute_station_temporal_features(df_station: pd.DataFrame, station_id: str) -> pd.DataFrame:
    """Compute causal temporal features for a single monitoring station.
    
    CRITICAL SCIENTIFIC REQUIREMENTS:
    1. Exact Contiguous-Lag Matching:
       pm25_lag_1h MUST correspond to exactly (t - 1h). If (t - 1h) observation is missing,
       lag MUST be NaN. Nearest-time substitution is strictly prohibited.
    2. Causal Rolling Windows:
       Rolling features at time t use observations strictly in [t - window + 1h, t].
       No centered or future-looking windows are allowed.
    3. Strict Zero Imputation:
       Missing lag and rolling values remain NaN.
    """
    if df_station.empty:
        return pd.DataFrame()

    df = df_station.copy()

    # Ensure timestamp_utc is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp_utc"]):
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    # Sort strictly chronologically
    df = df.sort_values("timestamp_utc").drop_duplicates(subset=["timestamp_utc"])

    # Reindex onto a complete continuous 1-hour grid to guarantee exact physical-hour lags
    min_time = df["timestamp_utc"].min()
    max_time = df["timestamp_utc"].max()

    full_grid = pd.date_range(start=min_time, end=max_time, freq="1h", tz="UTC", name="timestamp_utc")
    df_indexed = df.set_index("timestamp_utc").reindex(full_grid)
    df_indexed["station_id"] = station_id

    # 1. Exact Contiguous Lags for PM2.5
    pm25_series = df_indexed["pm25"]

    for lag in LAG_HOURS:
        # shift(lag) on a 1-hour regular grid shifts by EXACTLY 'lag' physical hours
        df_indexed[f"pm25_lag_{lag}h"] = pm25_series.shift(lag)

    # 2. Causal Rolling Historical Means (closed on right = includes t, looks backward)
    for window in ROLLING_WINDOWS_HOURS:
        min_periods = max(1, int(math.ceil(window * MIN_PERIOD_FRACTION)))
        # rolling(window) on right-closed backward window
        df_indexed[f"pm25_rolling_mean_{window}h"] = (
            pm25_series.rolling(window=window, min_periods=min_periods).mean()
        )

    # 3. Cyclical and Calendar Time Features (derived from timestamp)
    hours = df_indexed.index.hour
    df_indexed["hour_of_day_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
    df_indexed["hour_of_day_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
    df_indexed["day_of_week"] = df_indexed.index.dayofweek

    # Reset index to return timestamp_utc as a standard column
    df_features = df_indexed.reset_index()

    # Retain only timestamps that were in the original observation set (or keep all if needed)
    # Keeping only original observed timestamps maintains 1-to-1 correspondence with Phase 3B rows
    orig_timestamps = set(df["timestamp_utc"])
    df_features = df_features[df_features["timestamp_utc"].isin(orig_timestamps)].copy()

    # Generate timestamp_ist
    df_features["timestamp_ist"] = df_features["timestamp_utc"].dt.tz_convert("Asia/Kolkata")

    # Reorder columns logically
    feature_cols = (
        ["station_id", "timestamp_utc", "timestamp_ist", "pm25"] +
        [f"pm25_lag_{lag}h" for lag in LAG_HOURS] +
        [f"pm25_rolling_mean_{w}h" for w in ROLLING_WINDOWS_HOURS] +
        ["hour_of_day_sin", "hour_of_day_cos", "day_of_week"]
    )

    # Also keep other pollutant columns if present
    for p in ["pm10", "no2", "so2", "co", "o3"]:
        if p in df.columns and p not in feature_cols:
            feature_cols.append(p)

    existing_cols = [c for c in feature_cols if c in df_features.columns]
    return df_features[existing_cols]


def build_full_temporal_feature_dataset(parquet_path: Path) -> pd.DataFrame:
    """Build temporal features across all 42 stations in the Phase 3B dataset."""
    df_raw = pd.read_parquet(parquet_path)
    stations = sorted(df_raw["station_id"].unique())

    all_station_features = []
    for st_id in stations:
        df_st = df_raw[df_raw["station_id"] == st_id]
        feat_st = compute_station_temporal_features(df_st, st_id)
        all_station_features.append(feat_st)

    full_features = pd.concat(all_station_features, ignore_index=True)
    return full_features


def get_feature_metadata_catalog() -> Dict[str, Any]:
    """Return formal feature metadata catalog for all generated Phase 3C features."""
    return {
        "pm25_lag_1h": {
            "name": "pm25_lag_1h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "XKDR observational data",
            "formula": "PM2.5(t - 1h)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if exact (t - 1h) timestamp is unobserved in hourly grid",
            "description": "Observed PM2.5 concentration exactly 1 hour prior to prediction reference timestamp."
        },
        "pm25_lag_2h": {
            "name": "pm25_lag_2h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "XKDR observational data",
            "formula": "PM2.5(t - 2h)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if exact (t - 2h) timestamp is unobserved in hourly grid",
            "description": "Observed PM2.5 concentration exactly 2 hours prior to prediction reference timestamp."
        },
        "pm25_lag_3h": {
            "name": "pm25_lag_3h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "XKDR observational data",
            "formula": "PM2.5(t - 3h)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if exact (t - 3h) timestamp is unobserved in hourly grid",
            "description": "Observed PM2.5 concentration exactly 3 hours prior to prediction reference timestamp."
        },
        "pm25_lag_6h": {
            "name": "pm25_lag_6h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "XKDR observational data",
            "formula": "PM2.5(t - 6h)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if exact (t - 6h) timestamp is unobserved in hourly grid",
            "description": "Observed PM2.5 concentration exactly 6 hours prior to prediction reference timestamp."
        },
        "pm25_lag_12h": {
            "name": "pm25_lag_12h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "XKDR observational data",
            "formula": "PM2.5(t - 12h)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if exact (t - 12h) timestamp is unobserved in hourly grid",
            "description": "Observed PM2.5 concentration exactly 12 hours prior to prediction reference timestamp."
        },
        "pm25_lag_24h": {
            "name": "pm25_lag_24h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "XKDR observational data",
            "formula": "PM2.5(t - 24h)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if exact (t - 24h) timestamp is unobserved in hourly grid",
            "description": "Observed PM2.5 concentration exactly 24 hours prior to prediction reference timestamp."
        },
        "pm25_rolling_mean_3h": {
            "name": "pm25_rolling_mean_3h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "Derived from XKDR observations",
            "formula": "mean(PM2.5(tau) for tau in [t - 2h, t])",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if < 2 valid observations in the 3-hour backward window",
            "description": "Causal 3-hour backward rolling mean of PM2.5."
        },
        "pm25_rolling_mean_6h": {
            "name": "pm25_rolling_mean_6h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "Derived from XKDR observations",
            "formula": "mean(PM2.5(tau) for tau in [t - 5h, t])",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if < 3 valid observations in the 6-hour backward window",
            "description": "Causal 6-hour backward rolling mean of PM2.5."
        },
        "pm25_rolling_mean_12h": {
            "name": "pm25_rolling_mean_12h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "Derived from XKDR observations",
            "formula": "mean(PM2.5(tau) for tau in [t - 11h, t])",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if < 6 valid observations in the 12-hour backward window",
            "description": "Causal 12-hour backward rolling mean of PM2.5."
        },
        "pm25_rolling_mean_24h": {
            "name": "pm25_rolling_mean_24h",
            "type": "float64",
            "unit": "ug/m3",
            "source": "Derived from XKDR observations",
            "formula": "mean(PM2.5(tau) for tau in [t - 23h, t])",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "NaN if < 12 valid observations in the 24-hour backward window",
            "description": "Causal 24-hour backward rolling mean of PM2.5."
        },
        "hour_of_day_sin": {
            "name": "hour_of_day_sin",
            "type": "float64",
            "unit": "dimensionless",
            "source": "Timestamp",
            "formula": "sin(2 * pi * hour / 24)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Deterministic, never NaN",
            "description": "Cyclical sine component of the observation hour."
        },
        "hour_of_day_cos": {
            "name": "hour_of_day_cos",
            "type": "float64",
            "unit": "dimensionless",
            "source": "Timestamp",
            "formula": "cos(2 * pi * hour / 24)",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Deterministic, never NaN",
            "description": "Cyclical cosine component of the observation hour."
        },
        "day_of_week": {
            "name": "day_of_week",
            "type": "int64",
            "unit": "integer (0=Mon, 6=Sun)",
            "source": "Timestamp",
            "formula": "timestamp.dayofweek",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Deterministic, never NaN",
            "description": "Day of week index."
        },
        # Future Weather Feature Interface Contract Placeholders (To be fused in Phase 3D)
        "temperature_t_plus_1h": {
            "name": "temperature_t_plus_1h",
            "type": "float64",
            "unit": "celsius",
            "source": "Open-Meteo NWP Forecast (Phase 3D)",
            "formula": "Temperature at t + 1h",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Pending Phase 3D NWP fusion",
            "description": "INTERFACE PLACEHOLDER: Numerical Weather Prediction temperature forecast for lead time +1h."
        },
        "wind_speed_t_plus_1h": {
            "name": "wind_speed_t_plus_1h",
            "type": "float64",
            "unit": "km/h",
            "source": "Open-Meteo NWP Forecast (Phase 3D)",
            "formula": "Wind speed at t + 1h",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Pending Phase 3D NWP fusion",
            "description": "INTERFACE PLACEHOLDER: Numerical Weather Prediction wind speed forecast for lead time +1h."
        },
        "wind_direction_t_plus_1h": {
            "name": "wind_direction_t_plus_1h",
            "type": "float64",
            "unit": "degrees",
            "source": "Open-Meteo NWP Forecast (Phase 3D)",
            "formula": "Wind direction at t + 1h",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Pending Phase 3D NWP fusion",
            "description": "INTERFACE PLACEHOLDER: Numerical Weather Prediction wind direction forecast for lead time +1h."
        },
        "boundary_layer_height_t_plus_1h": {
            "name": "boundary_layer_height_t_plus_1h",
            "type": "float64",
            "unit": "meters",
            "source": "Open-Meteo NWP Forecast (Phase 3D)",
            "formula": "Planetary boundary layer height at t + 1h",
            "available_at_prediction_time": True,
            "future_leakage_risk": False,
            "missingness_behavior": "Pending Phase 3D NWP fusion",
            "description": "INTERFACE PLACEHOLDER: Numerical Weather Prediction planetary boundary layer height forecast."
        }
    }
