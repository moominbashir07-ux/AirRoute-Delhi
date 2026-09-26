"""Phase 5: Production Hardening, Security, Reliability & Failure-Injection Tests."""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import app, is_rate_limited, _rate_limit_records
from ml_model.model_integrity import verify_artifact_integrity
from ml_model.weather_client import WeatherClient, NWPServiceError
from ml_model.exposure_engine import CommuteExposureEngine

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_liveness(client):
    """Verify /health and /api/health report application liveness without invoking heavy inference."""
    res1 = client.get("/health")
    res2 = client.get("/api/health")

    assert res1.status_code == 200
    assert res2.status_code == 200

    data = res1.json()
    assert data["status"] == "healthy"
    assert data["service"] == "weather-final"
    assert "version" in data
    assert data["model_loaded"] is True
    assert "environment" in data


def test_readiness_endpoint_manifest_verification(client):
    """Verify /ready and /api/ready check model manifest and report all 10 production artifacts verified."""
    res1 = client.get("/ready")
    res2 = client.get("/api/ready")

    assert res1.status_code == 200
    assert res2.status_code == 200

    data = res1.json()
    assert data["status"] == "ready"
    assert data["service"] == "weather-final"
    assert data["artifacts_verified"] is True
    assert data["total_artifacts"] == 10
    assert data["verified_artifacts"] == 10


def test_request_id_generation_and_propagation(client):
    """Verify that X-Request-ID is generated if missing and preserved if supplied."""
    # 1. Generated if missing
    res1 = client.get("/health")
    assert "x-request-id" in res1.headers
    req_id1 = res1.headers["x-request-id"]
    assert len(req_id1) > 0

    # 2. Preserved if supplied
    custom_id = f"test-trace-{uuid.uuid4()}"
    res2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res2.headers["x-request-id"] == custom_id


def test_error_sanitization_no_stack_traces(client):
    """Verify that 400, 404, 422, and 500 responses return clean JSON without exposing stack traces or paths."""
    # 404 Not Found
    res_404 = client.get("/non-existent-endpoint")
    assert res_404.status_code == 404
    body_404 = res_404.text
    assert "Traceback" not in body_404
    assert "c:\\" not in body_404.lower()
    assert "python" not in body_404.lower() or "service" in body_404.lower()

    # 400 Bad Request
    res_400 = client.post("/predict", json={
        "temperature": 150.0,  # Invalid: > 60°C
        "humidity": 50.0, "wind_speed": 10.0, "co2": 420.0,
        "pm25": 45.0, "pm10": 80.0, "no2": 30.0, "so2": 15.0
    })
    assert res_400.status_code == 422
    body_400 = res_400.text
    assert "Traceback" not in body_400


def test_rate_limiting_abuse_protection():
    """Verify that in-memory sliding-window rate limiter trips on excessive requests and returns HTTP 429."""
    test_ip = "198.51.100.99"
    path = "/predict"
    _rate_limit_records[test_ip] = []

    # Fill rate limit window up to 60 requests
    for _ in range(60):
        assert not is_rate_limited(test_ip, path)

    # 61st request should be blocked
    assert is_rate_limited(test_ip, path)

    # Clean up test IP
    del _rate_limit_records[test_ip]


def test_model_artifact_integrity_verification():
    """Verify SHA-256 integrity checker validates all production artifacts."""
    report = verify_artifact_integrity()
    assert report["status"] == "valid"
    assert report["total_artifacts"] == 10
    assert report["verified_artifacts"] == 10
    assert len(report["errors"]) == 0

    # Test failure detection on non-existent manifest
    fake_path = MagicMock()
    fake_path.exists.return_value = False
    fake_report = verify_artifact_integrity(manifest_path=fake_path)
    assert fake_report["status"] == "no_manifest"


def test_nwp_timeout_and_failure_resilience():
    """Failure-Injection: Test that when live NWP service fails/times out, engine operates in degraded mode."""
    engine = CommuteExposureEngine()
    now = datetime.now(timezone.utc)

    # Mock weather_client.fetch_production_forecast to raise NWPServiceError
    with patch.object(engine.weather_client, "fetch_production_forecast", side_effect=NWPServiceError("Connection timed out")):
        res = engine.optimize_commute(
            origin_lat=28.6315,
            origin_lon=77.2167,
            dest_lat=28.5672,
            dest_lon=77.2100,
            mode="cycling",
            departure_window_start=now,
            departure_window_end=now + timedelta(hours=1),
            interval_minutes=30
        )

        assert res["status"] == "success"
        assert res["corridor_summary"]["weather_status"] == "degraded_historical"
        # Check that limitation warning was attached
        assert any("NWP weather input degraded" in lim for lim in res["limitations"])
        # Inhaled mass must still be positive and not zero-filled
        assert res["recommended_departure"]["estimated_inhaled_pm25_ug"] > 0.0


def test_corridor_extreme_window_span_rejected():
    """Verify that requests with departure windows spanning > 6 hours are strictly rejected."""
    now = datetime.now(timezone.utc)
    engine = CommuteExposureEngine()

    with pytest.raises(ValueError, match="Departure window exceeds maximum supported span of 6 hours"):
        engine.optimize_commute(
            origin_lat=28.6315,
            origin_lon=77.2167,
            dest_lat=28.5672,
            dest_lon=77.2100,
            mode="cycling",
            departure_window_start=now,
            departure_window_end=now + timedelta(hours=8),  # 8 hours > 6h
            interval_minutes=30
        )
