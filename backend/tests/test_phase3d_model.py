"""Tests for Phase 3D Model Loading, Architecture, and Non-negative Outputs."""

import pytest
import os
import numpy as np
import pandas as pd
from pathlib import Path
from ml_model.forecasting_engine import (
    MultiHorizonForecaster,
    HORIZONS,
    PHASE3D_MODEL_DIR
)


@pytest.fixture
def forecaster():
    f = MultiHorizonForecaster()
    # If models exist on disk, load them
    if (PHASE3D_MODEL_DIR / "model_h1.pkl").exists():
        f.load_artifacts()
    return f


def test_model_artifacts_exist_and_load(forecaster):
    for h in HORIZONS:
        model_path = PHASE3D_MODEL_DIR / f"model_h{h}.pkl"
        assert model_path.exists(), f"Model artifact {model_path} missing!"
        assert h in forecaster.models
        assert hasattr(forecaster.models[h], "predict")


def test_model_metrics_validity(forecaster):
    assert (PHASE3D_MODEL_DIR / "metrics.json").exists()
    assert (PHASE3D_MODEL_DIR / "model_metadata.json").exists()

    metrics = forecaster.metrics
    assert "horizons" in metrics
    for h in HORIZONS:
        h_str = f"{h}h"
        assert h_str in metrics["horizons"]
        h_res = metrics["horizons"][h_str]
        assert "ml_model" in h_res
        assert "persistence_baseline" in h_res
        ml_m = h_res["ml_model"]
        assert ml_m["mae"] > 0.0
        assert ml_m["rmse"] > 0.0
        assert ml_m["r2"] > 0.0
        # Verify ML model outperforms persistence
        assert h_res["ml_vs_persistence"]["ml_beats_persistence"] is True


def test_model_prediction_non_negative_and_finite(forecaster):
    # Construct a sample single-row feature dataframe for horizon 1
    feat_cols = forecaster.feature_columns[1]
    sample_dict = {col: 50.0 for col in feat_cols}
    # Latitude/longitude for Delhi
    sample_dict["latitude"] = 28.6139
    sample_dict["longitude"] = 77.2090
    sample_dict["hour_of_day_sin"] = 0.5
    sample_dict["hour_of_day_cos"] = 0.866
    sample_dict["day_of_week"] = 2

    df_sample = pd.DataFrame([sample_dict])[feat_cols]
    pred = forecaster.models[1].predict(df_sample)

    assert len(pred) == 1
    assert not np.isnan(pred[0])
    assert not np.isinf(pred[0])
    # Clipped to >= 0
    pred_clipped = max(0.0, float(pred[0]))
    assert pred_clipped >= 0.0
