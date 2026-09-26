"""Tests for Phase 4 Commuter Decision API Endpoints and Phase 2 Regression."""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_api_commute_optimize_valid_request():
    """Verify that POST /api/commute/optimize succeeds and returns structured exposure response."""
    now = datetime.now(timezone.utc)
    t_start = (now + timedelta(hours=1)).isoformat()
    t_end = (now + timedelta(hours=2)).isoformat()

    payload = {
        "origin": {"latitude": 28.6315, "longitude": 77.2167},
        "destination": {"latitude": 28.5355, "longitude": 77.3910},
        "mode": "cycling",
        "departure_window": {
            "start": t_start,
            "end": t_end,
            "interval_minutes": 15
        }
    }

    res = client.post("/api/commute/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert "corridor_summary" in data
    assert "recommended_departure" in data
    assert "departure_candidates" in data
    assert "segment_breakdown" in data
    assert "limitations" in data

    rec = data["recommended_departure"]
    assert rec["estimated_inhaled_pm25_ug"] > 0
    assert rec["time_weighted_pm25_ug_m3"] > 0
    assert rec["coverage_percent"] >= 80.0


def test_commute_optimize_aliased_route():
    """Verify that both /commute/optimize and /api/commute/optimize function identically."""
    now = datetime.now(timezone.utc)
    payload = {
        "origin": {"latitude": 28.6315, "longitude": 77.2167},
        "destination": {"latitude": 28.5672, "longitude": 77.2100},
        "mode": "motorized",
        "departure_window": {
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=1, minutes=30)).isoformat(),
            "interval_minutes": 15
        }
    }

    res = client.post("/commute/optimize", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_commute_optimize_invalid_mode_rejected():
    """Verify that an unsupported mode returns 400 Bad Request."""
    now = datetime.now(timezone.utc)
    payload = {
        "origin": {"latitude": 28.6315, "longitude": 77.2167},
        "destination": {"latitude": 28.5672, "longitude": 77.2100},
        "mode": "scooter_invalid",
        "departure_window": {
            "start": now.isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
            "interval_minutes": 15
        }
    }
    res = client.post("/api/commute/optimize", json=payload)
    assert res.status_code == 400
    assert "Unsupported mode" in res.json()["detail"]


def test_commute_optimize_out_of_ncr_bounds_rejected():
    """Verify that coordinates outside Delhi/NCR operational boundaries return 400 Bad Request."""
    now = datetime.now(timezone.utc)
    # Bangalore coordinates
    payload = {
        "origin": {"latitude": 12.9716, "longitude": 77.5946},
        "destination": {"latitude": 28.6315, "longitude": 77.2167},
        "mode": "walking",
        "departure_window": {
            "start": now.isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
            "interval_minutes": 15
        }
    }
    res = client.post("/api/commute/optimize", json=payload)
    assert res.status_code == 400
    assert "outside the Delhi NCR operational envelope" in res.json()["detail"]


def test_commute_optimize_reversed_departure_window_rejected():
    """Verify that end <= start returns 400 Bad Request."""
    now = datetime.now(timezone.utc)
    payload = {
        "origin": {"latitude": 28.6315, "longitude": 77.2167},
        "destination": {"latitude": 28.5672, "longitude": 77.2100},
        "mode": "cycling",
        "departure_window": {
            "start": (now + timedelta(hours=2)).isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
            "interval_minutes": 15
        }
    }
    res = client.post("/api/commute/optimize", json=payload)
    assert res.status_code == 400
    assert "strictly greater" in res.json()["detail"]


def test_commute_optimize_excessive_horizon_rejected():
    """Verify that journeys exceeding the validated 6h horizon return 400."""
    now = datetime.now(timezone.utc)
    payload = {
        "origin": {"latitude": 28.4089, "longitude": 77.3178},
        "destination": {"latitude": 28.7325, "longitude": 77.1189},
        "mode": "walking",  # 35 km walking takes ~7 hours
        "departure_window": {
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "interval_minutes": 15
        }
    }
    res = client.post("/api/commute/optimize", json=payload)
    assert res.status_code == 400
    assert "exceeds the validated 6-hour forecast horizon" in res.json()["detail"]


def test_commute_optimize_deterministic_repeated_requests():
    """Verify that repeated identical requests produce identical recommendations and doses."""
    now = datetime.now(timezone.utc)
    payload = {
        "origin": {"latitude": 28.6315, "longitude": 77.2167},
        "destination": {"latitude": 28.5355, "longitude": 77.3910},
        "mode": "motorized",
        "departure_window": {
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "interval_minutes": 15
        }
    }
    res1 = client.post("/api/commute/optimize", json=payload)
    res2 = client.post("/api/commute/optimize", json=payload)

    assert res1.status_code == 200
    assert res2.status_code == 200

    dose1 = res1.json()["recommended_departure"]["estimated_inhaled_pm25_ug"]
    dose2 = res2.json()["recommended_departure"]["estimated_inhaled_pm25_ug"]
    assert dose1 == dose2


def test_delhi_stations_endpoints():
    """Verify that both /stations/delhi and /api/stations/delhi return the 42 official stations."""
    res1 = client.get("/stations/delhi")
    res2 = client.get("/api/stations/delhi")

    assert res1.status_code == 200
    assert res2.status_code == 200

    data = res1.json()
    assert data["status"] == "success"
    assert data["total_stations"] == 42
    assert len(data["stations"]) == 42

    st0 = data["stations"][0]
    assert "station_id" in st0
    assert "station_name" in st0
    assert "latitude" in st0
    assert "longitude" in st0
    assert "source" in st0
    assert "available_pollutants" in st0


def test_phase2_endpoints_backward_compatibility():
    """REGRESSION TEST: Verify that Phase 2 /predict, /forecast, /metrics, /health remain intact."""
    # /health
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    # /predict
    p_res = client.post("/predict", json={
        "temperature": 25.0,
        "humidity": 50.0,
        "wind_speed": 10.0,
        "co2": 420.0,
        "pm25": 45.0,
        "pm10": 80.0,
        "no2": 30.0,
        "so2": 15.0
    })
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert "aqi" in p_data
    assert "category" in p_data

    # /forecast
    f_res = client.get("/forecast?days=3")
    assert f_res.status_code == 200
    f_data = f_res.json()
    assert len(f_data["forecast"]) == 3

    # /metrics
    m_res = client.get("/metrics")
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert "best_model" in m_data
