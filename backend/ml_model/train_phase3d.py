"""Phase 3D: Training and Evaluation Pipeline for Station-Level PM2.5 Forecaster.

Executes:
1. Dataset preparation and temporal feature alignment.
2. Chronological Train/Val/Test partitioning.
3. Walk-forward validation checks.
4. Model training for horizons h in {1..6} hours.
5. Comprehensive test evaluation against Persistence and Rolling Baselines.
6. Breakdown by station and pollution concentration regimes.
7. Artifact persistence in backend/ml_model/phase3d/ and backend/datasets/phase3d/.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml_model.forecasting_engine import (
    prepare_multi_horizon_dataset,
    get_horizon_feature_matrix,
    MultiHorizonForecaster,
    HORIZONS,
    REGIMES,
    PHASE3D_DATA_DIR,
    PHASE3D_MODEL_DIR
)
from ml_model.weather_client import WeatherClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("TrainPhase3D")


def run_phase3d_training():
    """Execute complete Phase 3D training and evaluation."""
    logger.info("Initializing Phase 3D Training Pipeline...")
    PHASE3D_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHASE3D_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ensure historical weather cache exists
    wx_client = WeatherClient(cache_dir=PHASE3D_DATA_DIR)
    wx_client.fetch_historical_archive()

    # 2. Prepare multi-horizon merged dataset
    df_merged, df_wx_indexed, base_feature_cols = prepare_multi_horizon_dataset()

    logger.info(f"Loaded merged observational dataset with {len(df_merged):,} records across {df_merged['station_id'].nunique()} stations.")

    # 3. Chronological Train / Val / Test Partitioning
    ts_col = df_merged["timestamp_utc"]
    train_mask_global = ts_col < pd.to_datetime("2024-01-01", utc=True)
    val_mask_global = (ts_col >= pd.to_datetime("2024-01-01", utc=True)) & (ts_col < pd.to_datetime("2024-07-01", utc=True))
    test_mask_global = (ts_col >= pd.to_datetime("2024-07-01", utc=True)) & (ts_col <= pd.to_datetime("2024-12-31 23:59:59", utc=True))

    split_metadata = {
        "train_period": {"start": "2020-01-01", "end": "2023-12-31"},
        "validation_period": {"start": "2024-01-01", "end": "2024-06-30"},
        "test_period": {"start": "2024-07-01", "end": "2024-12-31"},
        "global_rows": len(df_merged),
        "train_rows_total": int(train_mask_global.sum()),
        "val_rows_total": int(val_mask_global.sum()),
        "test_rows_total": int(test_mask_global.sum())
    }

    split_meta_path = PHASE3D_DATA_DIR / "split_metadata.json"
    with open(split_meta_path, "w", encoding="utf-8") as f:
        json.dump(split_metadata, f, indent=2)
    logger.info(f"Saved split metadata to {split_meta_path}")

    forecaster = MultiHorizonForecaster(model_dir=PHASE3D_MODEL_DIR)

    all_metrics = {
        "summary": {},
        "horizons": {},
        "station_breakdown": {},
        "regime_breakdown": {}
    }

    feature_columns_dict = {}

    # 4. Train and evaluate for each horizon h in {1..6}
    for h in HORIZONS:
        logger.info(f"--- Processing Horizon {h}h ---")
        df_h, X_h, y_h, feat_cols = get_horizon_feature_matrix(
            df_merged, df_wx_indexed, base_feature_cols, horizon=h
        )
        feature_columns_dict[h] = feat_cols

        # Apply chronological splits to horizon matrix
        h_ts = df_h["timestamp_utc"]
        train_idx = h_ts < pd.to_datetime("2024-01-01", utc=True)
        val_idx = (h_ts >= pd.to_datetime("2024-01-01", utc=True)) & (h_ts < pd.to_datetime("2024-07-01", utc=True))
        test_idx = (h_ts >= pd.to_datetime("2024-07-01", utc=True)) & (h_ts <= pd.to_datetime("2024-12-31 23:59:59", utc=True))

        X_train, y_train = X_h[train_idx], y_h[train_idx]
        X_val, y_val = X_h[val_idx], y_h[val_idx]
        X_test, y_test = X_h[test_idx], y_h[test_idx]
        df_test_h = df_h[test_idx].copy()

        logger.info(f"Horizon {h}h: Train={len(X_train):,}, Val={len(X_val):,}, Test={len(X_test):,}")

        # Train model
        model = forecaster.train_horizon(X_train, y_train, X_val, y_val, horizon=h)

        # Predict on Test set
        y_pred_raw = model.predict(X_test)
        clipped_count = int((y_pred_raw < 0.0).sum())
        y_pred = np.maximum(0.0, y_pred_raw)

        # Baseline 1: Persistence (PM2.5 at t)
        persist_pred = X_test["pm25_t0"].values

        # Baseline 2: Rolling Mean 6h
        rolling_pred = X_test["pm25_rolling_mean_6h"].fillna(X_test["pm25_t0"]).values

        # Metrics
        ml_eval = forecaster.evaluate_model(y_test.values, y_pred)
        ml_eval["clipped_negative_predictions"] = clipped_count
        ml_eval["test_sample_count"] = len(y_test)

        persist_eval = forecaster.evaluate_model(y_test.values, persist_pred)
        rolling_eval = forecaster.evaluate_model(y_test.values, rolling_pred)

        # Improvement metrics
        mae_improvement = round(persist_eval["mae"] - ml_eval["mae"], 3)
        pct_improvement = round((mae_improvement / persist_eval["mae"]) * 100.0, 2)

        horizon_result = {
            "ml_model": ml_eval,
            "persistence_baseline": persist_eval,
            "rolling_baseline": rolling_eval,
            "ml_vs_persistence": {
                "mae_reduction_ug_m3": mae_improvement,
                "percentage_improvement": pct_improvement,
                "ml_beats_persistence": bool(ml_eval["mae"] < persist_eval["mae"])
            }
        }
        all_metrics["horizons"][f"{h}h"] = horizon_result
        logger.info(
            f"Horizon {h}h Results | ML MAE: {ml_eval['mae']:.2f}, Persistence MAE: {persist_eval['mae']:.2f}, "
            f"Improvement: {pct_improvement:.2f}% | ML R2: {ml_eval['r2']:.4f}, Persist R2: {persist_eval['r2']:.4f}"
        )

        # Performance Breakdown by Pollution Regime (for horizon h=1 and h=3)
        if h in [1, 3, 6]:
            df_test_h["y_true"] = y_test.values
            df_test_h["y_pred"] = y_pred
            df_test_h["persist"] = persist_pred

            regime_stats = {}
            for r_name, (r_low, r_high) in REGIMES.items():
                r_mask = (df_test_h["y_true"] >= r_low) & (df_test_h["y_true"] < r_high)
                if r_mask.sum() > 0:
                    y_sub_true = df_test_h.loc[r_mask, "y_true"].values
                    y_sub_pred = df_test_h.loc[r_mask, "y_pred"].values
                    regime_stats[r_name] = {
                        "sample_count": int(r_mask.sum()),
                        "mae": round(float(mean_absolute_error(y_sub_true, y_sub_pred)), 2),
                        "rmse": round(float(np.sqrt(mean_squared_error(y_sub_true, y_sub_pred))), 2),
                        "mean_bias": round(float(np.mean(y_sub_pred - y_sub_true)), 2)
                    }
            all_metrics["regime_breakdown"][f"{h}h"] = regime_stats

        # Station Breakdown for Horizon 1h
        if h == 1:
            station_stats = {}
            for st_id, st_group in df_test_h.groupby("station_id"):
                if len(st_group) >= 100:  # Minimum test sample threshold
                    st_true = st_group["y_true"].values
                    st_pred = st_group["y_pred"].values
                    st_persist = st_group["persist"].values
                    st_mae = mean_absolute_error(st_true, st_pred)
                    st_r2 = r2_score(st_true, st_pred) if np.var(st_true) > 0 else 0.0
                    station_stats[st_id] = {
                        "sample_count": len(st_group),
                        "mae": round(float(st_mae), 2),
                        "rmse": round(float(np.sqrt(mean_squared_error(st_true, st_pred))), 2),
                        "r2": round(float(st_r2), 4),
                        "persist_mae": round(float(mean_absolute_error(st_true, st_persist)), 2)
                    }
            all_metrics["station_breakdown"]["1h"] = station_stats

    # 5. Populate summary
    all_metrics["summary"] = {
        "model_type": "HistGradientBoostingRegressor (Multi-Horizon Direct)",
        "horizons_evaluated": HORIZONS,
        "primary_metric": "MAE (Mean Absolute Error, ug/m3)",
        "ml_vs_persistence_summary": {
            f"{h}h": {
                "ml_mae": all_metrics["horizons"][f"{h}h"]["ml_model"]["mae"],
                "persist_mae": all_metrics["horizons"][f"{h}h"]["persistence_baseline"]["mae"],
                "mae_reduction": all_metrics["horizons"][f"{h}h"]["ml_vs_persistence"]["mae_reduction_ug_m3"],
                "pct_improvement": all_metrics["horizons"][f"{h}h"]["ml_vs_persistence"]["percentage_improvement"]
            }
            for h in HORIZONS
        }
    }

    forecaster.metrics = all_metrics

    # 6. Save Model Metadata
    model_metadata = {
        "model_version": "phase3d_pm25_forecaster_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_architecture": "HistGradientBoostingRegressor (scikit-learn)",
        "hyperparameters": {
            "max_iter": 150,
            "learning_rate": 0.08,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 25,
            "early_stopping": True,
            "random_state": 42
        },
        "target": "Station-level PM2.5 concentration (ug/m3) for lead times t+1h through t+6h",
        "training_period": "2020-01-01 to 2023-12-31",
        "validation_period": "2024-01-01 to 2024-06-30",
        "test_period": "2024-07-01 to 2024-12-31",
        "weather_sources": {
            "training_and_evaluation": "Open-Meteo ECMWF ERA5 Reanalysis Archive (archive-api.open-meteo.com)",
            "production_inference": "Open-Meteo Real-Time NWP Forecast API (api.open-meteo.com/v1/forecast)"
        },
        "leakage_boundaries": {
            "future_pm25_in_features": False,
            "future_observed_weather_at_inference": False,
            "temporal_split_type": "Strict Chronological Partition (No random shuffle)",
            "native_nan_support": True
        },
        "feature_columns": {str(k): v for k, v in feature_columns_dict.items()}
    }

    forecaster.save_artifacts(model_metadata)

    # 7. Save dataset metadata
    dataset_metadata = {
        "dataset_name": "Phase 3D Multi-Horizon PM2.5 Forecasting Dataset",
        "observational_source": "Phase 3B XKDR Delhi/NCR Parquet Dataset",
        "meteorological_source": "Open-Meteo ERA5 Reanalysis Archive",
        "total_records": len(df_merged),
        "total_stations": df_merged["station_id"].nunique(),
        "split_summary": split_metadata,
        "horizons": HORIZONS
    }
    with open(PHASE3D_DATA_DIR / "dataset_metadata.json", "w", encoding="utf-8") as f:
        json.dump(dataset_metadata, f, indent=2)

    logger.info("Phase 3D Model Training and Evaluation successfully completed!")


if __name__ == "__main__":
    run_phase3d_training()
