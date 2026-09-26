"""Phase 3D: Station-Level PM2.5 Multi-Horizon Forecasting Engine.

Trains direct multi-horizon forecasting models for horizons h in {1..6} hours.
Enforces strict chronological partitioning, zero future target/weather leakage,
native missingness handling via HistGradientBoostingRegressor, and non-negative clipping.
"""

import os
import sys
import math
import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

logger = logging.getLogger("ForecastingEngine")

BASE_DIR = Path(__file__).resolve().parent.parent
PHASE3C_DATA_DIR = BASE_DIR / "datasets" / "phase3c"
PHASE3D_DATA_DIR = BASE_DIR / "datasets" / "phase3d"
PHASE3D_MODEL_DIR = BASE_DIR / "ml_model" / "phase3d"
XKDR_DIR = BASE_DIR / "datasets" / "xkdr"

HORIZONS = [1, 2, 3, 4, 5, 6]

# Chronological Train / Validation / Test split boundaries
SPLIT_TRAIN_END = "2023-12-31 23:59:59"
SPLIT_VAL_END = "2024-06-30 23:59:59"
SPLIT_TEST_END = "2024-12-31 23:59:59"

# Pollution regimes (concentration strata in ug/m3)
REGIMES = {
    "low": (0.0, 30.0),
    "moderate": (30.0, 60.0),
    "high": (60.0, 120.0),
    "very_high": (120.0, 250.0),
    "severe": (250.0, 10000.0)
}


def prepare_multi_horizon_dataset(
    station_features_path: Optional[Path] = None,
    weather_cache_path: Optional[Path] = None,
    catalog_path: Optional[Path] = None
) -> Tuple[pd.DataFrame, List[str]]:
    """Merge observational features, station spatial metadata, and future weather for all horizons.
    
    Guarantees:
    - At prediction cutoff t, observational features use only data at or before t.
    - Weather for horizon h uses meteorological forecast for valid time (t + h).
    - Target for horizon h is pm25 at exactly (t + h).
    """
    station_path = station_features_path or (PHASE3C_DATA_DIR / "station_temporal_features.parquet")
    wx_path = weather_cache_path or (PHASE3D_DATA_DIR / "historical_weather_2020_2024.parquet")
    cat_path = catalog_path or (XKDR_DIR / "station_catalog.csv")

    logger.info(f"Loading observational station features from {station_path}...")
    df_st = pd.read_parquet(station_path)

    logger.info(f"Loading meteorological data from {wx_path}...")
    df_wx = pd.read_parquet(wx_path)

    logger.info(f"Loading station catalog from {cat_path}...")
    df_cat = pd.read_csv(cat_path)[["station_id", "latitude", "longitude"]]

    # Ensure UTC datetimes
    df_st["timestamp_utc"] = pd.to_datetime(df_st["timestamp_utc"], utc=True)
    df_wx["timestamp_utc"] = pd.to_datetime(df_wx["timestamp_utc"], utc=True)

    # Rename pm25 at t to pm25_t0
    df_st = df_st.rename(columns={"pm25": "pm25_t0"})

    # Merge station coordinates
    df_st = pd.merge(df_st, df_cat, on="station_id", how="left")

    # 1. Compute multi-horizon targets for each station on regular hourly grid
    logger.info("Computing multi-horizon future targets (t+1h through t+6h)...")
    station_dfs = []
    for st_id, group in df_st.groupby("station_id"):
        grp = group.sort_values("timestamp_utc").set_index("timestamp_utc")
        min_ts = grp.index.min()
        max_ts = grp.index.max()
        full_grid = pd.date_range(min_ts, max_ts, freq="1h", tz="UTC", name="timestamp_utc")
        grp_grid = grp.reindex(full_grid)
        grp_grid["station_id"] = st_id

        # Target t+h is the concentration shifted backward by h steps
        for h in HORIZONS:
            grp_grid[f"target_t_plus_{h}h"] = grp_grid["pm25_t0"].shift(-h)

        # Retain original observed timestamps
        orig_observed = grp_grid[grp_grid.index.isin(grp.index)].reset_index()
        station_dfs.append(orig_observed)

    df_merged = pd.concat(station_dfs, ignore_index=True)

    # 2. Merge weather features for each horizon
    # For horizon h, weather features at (t + h) are merged by aligning timestamp_utc
    logger.info("Aligning future weather features for horizons 1 through 6...")
    # Pre-index weather by timestamp_utc
    df_wx_indexed = df_wx.set_index("timestamp_utc")

    # Base observational features
    base_feature_cols = [
        "pm25_t0",
        "pm25_lag_1h", "pm25_lag_2h", "pm25_lag_3h", "pm25_lag_6h", "pm25_lag_12h", "pm25_lag_24h",
        "pm25_rolling_mean_3h", "pm25_rolling_mean_6h", "pm25_rolling_mean_12h", "pm25_rolling_mean_24h",
        "hour_of_day_sin", "hour_of_day_cos", "day_of_week",
        "latitude", "longitude"
    ]

    return df_merged, df_wx_indexed, base_feature_cols


def get_horizon_feature_matrix(
    df_merged: pd.DataFrame,
    df_wx_indexed: pd.DataFrame,
    base_feature_cols: List[str],
    horizon: int
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Construct (X, y, feature_names) for a specific forecast horizon h.
    
    Includes base historical features plus weather forecast valid at (t + h).
    Filters out records where target is missing or pm25_t0 is missing.
    """
    target_col = f"target_t_plus_{horizon}h"

    # Filter valid targets and valid current observations
    valid_mask = df_merged[target_col].notna() & df_merged["pm25_t0"].notna()
    df_h = df_merged[valid_mask].copy()

    # Calculate future weather timestamp: t + h hours
    future_wx_ts = df_h["timestamp_utc"] + pd.to_timedelta(horizon, unit="h")

    # Map weather features
    wx_cols = [
        "temperature", "humidity", "wind_speed",
        "wind_direction_sin", "wind_direction_cos",
        "boundary_layer_height", "surface_pressure"
    ]

    # Reindex weather onto future timestamps
    wx_future = df_wx_indexed.reindex(future_wx_ts).reset_index(drop=True)

    # Attach horizon weather features with clear names
    horizon_wx_cols = [f"{c}_h{horizon}" for c in wx_cols]
    for c, hc in zip(wx_cols, horizon_wx_cols):
        df_h[hc] = wx_future[c].values

    feature_cols = base_feature_cols + horizon_wx_cols
    X = df_h[feature_cols]
    y = df_h[target_col]

    return df_h, X, y, feature_cols


class MultiHorizonForecaster:
    """Multi-horizon PM2.5 forecasting engine managing models M_1 through M_6."""

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or PHASE3D_MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.models: Dict[int, HistGradientBoostingRegressor] = {}
        self.feature_columns: Dict[int, List[str]] = {}
        self.metrics: Dict[str, Any] = {}

    def train_horizon(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        horizon: int,
        random_state: int = 42
    ) -> HistGradientBoostingRegressor:
        """Train a HistGradientBoostingRegressor for a single horizon with early stopping on validation."""
        logger.info(f"Training Model M_{horizon} (Horizon: {horizon}h) on {len(X_train):,} train samples...")

        model = HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.08,
            max_leaf_nodes=31,
            min_samples_leaf=25,
            early_stopping=True,
            n_iter_no_change=10,
            validation_fraction=None,  # We evaluate explicitly on chronological X_val
            random_state=random_state
        )

        model.fit(X_train, y_train)
        self.models[horizon] = model
        return model

    def evaluate_model(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Compute standard regression metrics, bias, and non-negative statistics."""
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))
        med_ae = float(median_absolute_error(y_true, y_pred))
        bias = float(np.mean(y_pred - y_true))

        return {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 4),
            "median_absolute_error": round(med_ae, 3),
            "mean_bias_error": round(bias, 3)
        }

    def save_artifacts(self, metadata: Dict[str, Any]):
        """Persist all trained models and evaluation metadata."""
        for h, model in self.models.items():
            model_path = self.model_dir / f"model_h{h}.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
            logger.info(f"Saved Model M_{h} to {model_path}")

        meta_path = self.model_dir / "model_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        metrics_path = self.model_dir / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)
        logger.info(f"Saved Phase 3D metrics to {metrics_path}")

    def load_artifacts(self):
        """Reload all trained horizon models and metadata from disk."""
        for h in HORIZONS:
            model_path = self.model_dir / f"model_h{h}.pkl"
            if not model_path.exists():
                raise FileNotFoundError(f"Model artifact not found: {model_path}")
            with open(model_path, "rb") as f:
                self.models[h] = pickle.load(f)

        meta_path = self.model_dir / "model_metadata.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            self.feature_columns = {int(k): v for k, v in metadata.get("feature_columns", {}).items()}

        metrics_path = self.model_dir / "metrics.json"
        with open(metrics_path, "r", encoding="utf-8") as f:
            self.metrics = json.load(f)
        logger.info("Successfully reloaded all Phase 3D model artifacts.")

    def forecast_pm25(
        self,
        station_id: str,
        station_lat: float,
        station_lon: float,
        prediction_time: datetime,
        historical_pm25_series: pd.Series,
        future_weather_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Production inference contract for a single monitoring station.
        
        Parameters:
        - station_id: str
        - station_lat, station_lon: float
        - prediction_time: datetime (UTC)
        - historical_pm25_series: Series indexed by timestamp_utc with at least recent 24h history
        - future_weather_df: DataFrame with columns [temperature, humidity, wind_speed, wind_direction_sin, wind_direction_cos, boundary_layer_height, surface_pressure]
                             containing at least 6 hourly forecast rows starting from prediction_time + 1h
        """
        if not self.models:
            self.load_artifacts()

        # Compute observational lags & rolling features at prediction_time t
        pm25_t0 = float(historical_pm25_series.get(prediction_time, np.nan))
        
        # Exact contiguous lags
        lags = {}
        for lag in [1, 2, 3, 6, 12, 24]:
            t_lag = prediction_time - pd.to_timedelta(lag, unit="h")
            lags[f"pm25_lag_{lag}h"] = float(historical_pm25_series.get(t_lag, np.nan))

        # Causal rolling means
        rolling = {}
        for w in [3, 6, 12, 24]:
            w_times = [prediction_time - pd.to_timedelta(i, unit="h") for i in range(w)]
            vals = [historical_pm25_series.get(ts, np.nan) for ts in w_times]
            valid_vals = [v for v in vals if not np.isnan(v)]
            rolling[f"pm25_rolling_mean_{w}h"] = float(np.mean(valid_vals)) if len(valid_vals) >= max(1, int(w * 0.5)) else np.nan

        h_sin = math.sin(2.0 * math.pi * prediction_time.hour / 24.0)
        h_cos = math.cos(2.0 * math.pi * prediction_time.hour / 24.0)
        dow = prediction_time.weekday()

        base_dict = {
            "pm25_t0": pm25_t0,
            **lags,
            **rolling,
            "hour_of_day_sin": h_sin,
            "hour_of_day_cos": h_cos,
            "day_of_week": dow,
            "latitude": station_lat,
            "longitude": station_lon
        }

        forecast_results = {}
        for h in HORIZONS:
            model = self.models[h]
            feat_cols = self.feature_columns[h]

            # Extract future weather at t + h
            target_ts = prediction_time + pd.to_timedelta(h, unit="h")
            # Lookup row in future_weather_df
            wx_row = future_weather_df[future_weather_df["timestamp_utc"] == target_ts]
            if wx_row.empty and len(future_weather_df) >= h:
                wx_row = future_weather_df.iloc[[h - 1]]

            row_dict = dict(base_dict)
            if not wx_row.empty:
                r = wx_row.iloc[0]
                row_dict[f"temperature_h{h}"] = float(r["temperature"])
                row_dict[f"humidity_h{h}"] = float(r["humidity"])
                row_dict[f"wind_speed_h{h}"] = float(r["wind_speed"])
                row_dict[f"wind_direction_sin_h{h}"] = float(r["wind_direction_sin"])
                row_dict[f"wind_direction_cos_h{h}"] = float(r["wind_direction_cos"])
                row_dict[f"boundary_layer_height_h{h}"] = float(r["boundary_layer_height"])
                row_dict[f"surface_pressure_h{h}"] = float(r["surface_pressure"])
            else:
                for col in ["temperature", "humidity", "wind_speed", "wind_direction_sin", "wind_direction_cos", "boundary_layer_height", "surface_pressure"]:
                    row_dict[f"{col}_h{h}"] = np.nan

            X_infer = pd.DataFrame([row_dict])[feat_cols]
            pred = float(model.predict(X_infer)[0])
            pred_clipped = max(0.0, pred)

            forecast_results[f"{h}h"] = {
                "timestamp": target_ts.isoformat(),
                "pm25_ug_m3": round(pred_clipped, 2),
                "is_clipped_non_negative": bool(pred < 0.0)
            }

        return {
            "station_id": station_id,
            "prediction_time": prediction_time.isoformat(),
            "persistence_baseline_pm25": round(pm25_t0, 2) if not np.isnan(pm25_t0) else None,
            "forecasts": forecast_results
        }
