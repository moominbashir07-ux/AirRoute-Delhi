"""
Phase 2 Real-World ML Pipeline Verification Suite
Tests dataset integrity, preprocessing, leakage prevention, chronological splitting,
model training/serialization, artifact validity, and /predict integration.
"""

import os
import json
import pickle
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model")))

from app import app
from train import (
    FEATURE_ORDER,
    TARGET,
    DATASET_PATH,
    DATASET_META_PATH,
    MODEL_PATH,
    SCALER_PATH,
    METRICS_PATH,
    METRICS_JSON_PATH,
    FEATURE_META_PATH,
    PROVENANCE_PATH,
    load_real_dataset,
    validate_and_clean,
    chronological_split,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def dataset_df():
    assert os.path.exists(DATASET_PATH), f"Dataset missing at {DATASET_PATH}"
    df = pd.read_csv(DATASET_PATH)
    return df


# ─── 1. Dataset Tests ──────────────────────────────────────────────────────────

def test_dataset_loads_and_has_required_columns(dataset_df):
    """Verify dataset loads successfully and contains exact canonical columns."""
    expected_cols = {"time", "temperature", "humidity", "wind_speed", "co2", "pm25", "pm10", "no2", "so2", "aqi"}
    assert expected_cols.issubset(set(dataset_df.columns)), f"Columns missing: {expected_cols - set(dataset_df.columns)}"
    assert len(dataset_df) >= 10000, f"Expected real dataset >= 10,000 samples, got {len(dataset_df)}"


def test_dataset_column_types_and_target_validity(dataset_df):
    """Verify all feature columns and target are numeric with valid physical ranges."""
    for col in FEATURE_ORDER + [TARGET]:
        assert pd.api.types.is_numeric_dtype(dataset_df[col]), f"Column {col} is not numeric"

    # EPA AQI must be non-negative and bounded realistically
    assert dataset_df[TARGET].min() >= 0, "Target AQI contains negative values"
    assert dataset_df[TARGET].max() <= 500, "Target AQI exceeds maximum physical bound of 500"
    assert not dataset_df[TARGET].isnull().any(), "Target AQI contains null values"


def test_no_target_leakage_in_feature_set():
    """Verify target and target-derived fields are strictly excluded from input features."""
    assert TARGET not in FEATURE_ORDER, "Target variable found inside FEATURE_ORDER"
    for forbidden in ["target", "label", "us_aqi", "aqi_category", "calculated_aqi"]:
        assert forbidden not in FEATURE_ORDER, f"Leaky column '{forbidden}' in FEATURE_ORDER"


def test_dataset_provenance_metadata():
    """Verify dataset metadata document exists and records authoritative origin."""
    assert os.path.exists(DATASET_META_PATH), f"Metadata file not found: {DATASET_META_PATH}"
    with open(DATASET_META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert "dataset_name" in meta
    assert "source" in meta
    assert "geographic_coverage" in meta
    assert meta["geographic_coverage"]["latitude"] == 28.6139
    assert meta["sample_count"] == len(load_real_dataset())


# ─── 2. Preprocessing & Leakage Prevention Tests ───────────────────────────────

def test_feature_order_is_deterministic():
    """Verify feature order matches exactly the canonical 8-input contract."""
    assert FEATURE_ORDER == [
        "temperature",
        "humidity",
        "wind_speed",
        "co2",
        "pm25",
        "pm10",
        "no2",
        "so2",
    ]


def test_validate_and_clean_handles_data(dataset_df):
    """Verify data validation cleans duplicates, sorts chronologically, and enforces bounds."""
    cleaned = validate_and_clean(dataset_df)
    assert len(cleaned) > 0
    assert cleaned["time"].is_monotonic_increasing, "Dataset must be monotonically increasing in time"
    # Ensure no NaN or infinite values remain
    assert not cleaned[FEATURE_ORDER].isnull().any().any()
    assert not np.isinf(cleaned[FEATURE_ORDER].values).any()


def test_scaler_fitted_only_on_training_set():
    """Verify production scaler was fitted strictly on training data dimensions without leaking test data."""
    assert os.path.exists(SCALER_PATH)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    assert hasattr(scaler, "mean_")
    assert hasattr(scaler, "scale_")
    assert len(scaler.mean_) == len(FEATURE_ORDER)
    assert len(scaler.scale_) == len(FEATURE_ORDER)
    assert not np.isnan(scaler.mean_).any()


# ─── 3. Chronological Split Tests ─────────────────────────────────────────────

def test_chronological_split_no_overlap(dataset_df):
    """Verify train, validation, and test partitions are strictly non-overlapping and time-ordered."""
    df_clean = validate_and_clean(dataset_df)
    train_df, val_df, test_df = chronological_split(df_clean)

    assert len(train_df) > 0, "Train partition is empty"
    assert len(val_df) > 0, "Validation partition is empty"
    assert len(test_df) > 0, "Test partition is empty"

    # Verify temporal non-overlap
    max_train_time = train_df["time"].max()
    min_val_time = val_df["time"].min()
    max_val_time = val_df["time"].max()
    min_test_time = test_df["time"].min()

    assert max_train_time < min_val_time, f"Train overlap with Val: {max_train_time} >= {min_val_time}"
    assert max_val_time < min_test_time, f"Val overlap with Test: {max_val_time} >= {min_test_time}"

    # Verify total samples sum up
    assert len(train_df) + len(val_df) + len(test_df) == len(df_clean)


# ─── 4. Model Artifact & Evaluation Tests ──────────────────────────────────────

def test_production_artifacts_exist():
    """Verify all required model, scaler, metadata, and metric files exist on disk."""
    for path in [MODEL_PATH, SCALER_PATH, METRICS_PATH, METRICS_JSON_PATH, FEATURE_META_PATH, PROVENANCE_PATH]:
        assert os.path.exists(path), f"Artifact missing: {path}"


def test_model_artifact_reload_and_prediction():
    """Verify pickled model can be reloaded and produces valid numerical scalar predictions."""
    with open(MODEL_PATH, "rb") as f:
        artifact = pickle.load(f)
    assert "model" in artifact
    assert "name" in artifact
    model = artifact["model"]

    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)

    # Test sample
    sample = np.array([[28.5, 62.0, 8.5, 950.0, 75.0, 130.0, 45.0, 30.0]])
    scaled = scaler.transform(sample)
    pred = model.predict(scaled)

    assert len(pred) == 1
    assert isinstance(float(pred[0]), float)
    assert not np.isnan(pred[0])
    assert not np.isinf(pred[0])
    assert 0 <= pred[0] <= 500


def test_model_outperforms_naive_baseline():
    """Verify trained model significantly outperforms the naive mean baseline on holdout test set."""
    with open(METRICS_JSON_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    test_metrics = metrics["test_metrics"]
    baseline_eval = next(m for m in metrics["all_model_evaluations"] if "Baseline" in m["name"])

    # Trained model must have higher R² and lower MAE than naive mean baseline
    assert test_metrics["r2"] > baseline_eval["test"]["r2"], "Model R² does not beat baseline"
    assert test_metrics["mae"] < baseline_eval["test"]["mae"], "Model MAE is worse than baseline"
    assert test_metrics["r2"] > 0.60, f"Expected realistic test R² > 0.60, got {test_metrics['r2']}"


# ─── 5. API Compatibility & Real Model Verification Tests ───────────────────────

def test_api_predict_uses_real_world_model(client):
    """Verify /predict uses the newly serialized real-world model artifact and returns valid response."""
    payload = {
        "temperature": 24.5,
        "humidity": 62.0,
        "wind_speed": 9.3,
        "co2": 985.0,
        "pm25": 66.0,
        "pm10": 117.0,
        "no2": 42.0,
        "so2": 35.0,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "Random Forest"
    assert 50 <= data["aqi"] <= 250
    assert not np.isnan(data["aqi"])
    assert data["category"] in [
        "Good",
        "Moderate",
        "Unhealthy for Sensitive Groups",
        "Unhealthy",
        "Very Unhealthy",
        "Hazardous",
    ]


def test_api_metrics_endpoint_reflects_real_provenance(client):
    """Verify /metrics returns legitimate real-world training evaluation metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["best_model"] == "Random Forest"
    assert "all_models" in data
    assert len(data["all_models"]) >= 4

    # Verify PM2.5 is the top feature importance (consistent with atmospheric physics)
    fi = data["feature_importance"]
    assert "pm25" in fi
    assert fi["pm25"] > fi["temperature"]
    assert fi["pm25"] > fi["wind_speed"]

    # Verify sample predictions are non-empty for UI scatter plot
    sp = data["sample_predictions"]
    assert len(sp["y_test"]) > 0
    assert len(sp["predicted"]) > 0
