"""
Foundation Smoke Tests - AQI Predictor Backend
Validates core endpoints, security controls, and input validation.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """Verify system health endpoint and model initialization."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "model" in data


def test_predict_valid_payload(client):
    """Verify /predict returns valid AQI classification with 8 valid features."""
    payload = {
        "temperature": 25.0,
        "humidity": 55.0,
        "wind_speed": 12.0,
        "co2": 450.0,
        "pm25": 35.0,
        "pm10": 70.0,
        "no2": 40.0,
        "so2": 20.0,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "aqi" in data
    assert isinstance(data["aqi"], (int, float))
    assert data["category"] in [
        "Good",
        "Moderate",
        "Unhealthy for Sensitive Groups",
        "Unhealthy",
        "Very Unhealthy",
        "Hazardous",
    ]
    assert "health_message" in data


def test_predict_invalid_payload_rejected(client):
    """Verify /predict rejects out-of-bounds or missing parameters."""
    # Missing required features
    incomplete_payload = {"temperature": 25.0, "humidity": 55.0}
    response = client.post("/predict", json=incomplete_payload)
    assert response.status_code == 422

    # Negative humidity (out of ge=0 bound)
    invalid_bound_payload = {
        "temperature": 25.0,
        "humidity": -10.0,
        "wind_speed": 10.0,
        "co2": 400.0,
        "pm25": 20.0,
        "pm10": 40.0,
        "no2": 15.0,
        "so2": 10.0,
    }
    response_bound = client.post("/predict", json=invalid_bound_payload)
    assert response_bound.status_code == 422


def test_auth_send_otp_no_leakage(client):
    """Verify /auth/send-otp does NOT return plaintext dev_otp in default configuration."""
    response = client.post("/auth/send-otp", json={"email": "smoke_tester@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    # Security requirement: dev_otp must NOT be present
    assert "dev_otp" not in data


def test_model_retraining_protected(client):
    """Verify /train cannot be triggered without explicit authorization/flag."""
    response = client.post("/train")
    # Must be rejected (403 when disabled or 401 when unauthenticated)
    assert response.status_code in (401, 403)


def test_aqi_history_endpoint(client):
    """Verify historical simulated series returns valid format."""
    response = client.get("/aqi-history?days=5")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 5


def test_forecast_endpoint(client):
    """Verify forecast returns multi-day structure."""
    response = client.get("/forecast?days=3")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["forecast"]) == 3
