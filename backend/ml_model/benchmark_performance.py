"""Phase 5: Performance Benchmarking Script.

Measures actual cold-start, warm, average, and peak latencies across all production endpoints:
- GET /health
- GET /stations/delhi
- POST /predict
- POST /forecast
- POST /api/commute/optimize
"""

import time
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


def benchmark_endpoints():
    results = {}
    
    with TestClient(app) as client:
        # 1. GET /health
        t0 = time.perf_counter()
        r = client.get("/health")
        cold_health = (time.perf_counter() - t0) * 1000.0
        health_times = []
        for _ in range(20):
            t = time.perf_counter()
            client.get("/health")
            health_times.append((time.perf_counter() - t) * 1000.0)
        results["GET /health"] = {
            "cold_start_ms": round(cold_health, 2),
            "warm_ms": round(health_times[0], 2),
            "avg_ms": round(float(np.mean(health_times)), 2),
            "peak_ms": round(float(np.max(health_times)), 2),
            "status": r.status_code
        }

        # 2. GET /stations/delhi
        t0 = time.perf_counter()
        r = client.get("/stations/delhi")
        cold_stations = (time.perf_counter() - t0) * 1000.0
        st_times = []
        for _ in range(20):
            t = time.perf_counter()
            client.get("/stations/delhi")
            st_times.append((time.perf_counter() - t) * 1000.0)
        results["GET /stations/delhi"] = {
            "cold_start_ms": round(cold_stations, 2),
            "warm_ms": round(st_times[0], 2),
            "avg_ms": round(float(np.mean(st_times)), 2),
            "peak_ms": round(float(np.max(st_times)), 2),
            "status": r.status_code
        }

        # 3. POST /predict
        payload_predict = {
            "temperature": 28.5,
            "humidity": 55.0,
            "wind_speed": 12.0,
            "co2": 450.0,
            "pm25": 65.0,
            "pm10": 110.0,
            "no2": 35.0,
            "so2": 18.0
        }
        t0 = time.perf_counter()
        r = client.post("/predict", json=payload_predict)
        cold_predict = (time.perf_counter() - t0) * 1000.0
        pred_times = []
        for _ in range(20):
            t = time.perf_counter()
            client.post("/predict", json=payload_predict)
            pred_times.append((time.perf_counter() - t) * 1000.0)
        results["POST /predict"] = {
            "cold_start_ms": round(cold_predict, 2),
            "warm_ms": round(pred_times[0], 2),
            "avg_ms": round(float(np.mean(pred_times)), 2),
            "peak_ms": round(float(np.max(pred_times)), 2),
            "status": r.status_code
        }

        # 4. POST /forecast
        t0 = time.perf_counter()
        r = client.get("/forecast?days=7")
        cold_forecast = (time.perf_counter() - t0) * 1000.0
        fc_times = []
        for _ in range(20):
            t = time.perf_counter()
            client.get("/forecast?days=7")
            fc_times.append((time.perf_counter() - t) * 1000.0)
        results["POST /forecast"] = {
            "cold_start_ms": round(cold_forecast, 2),
            "warm_ms": round(fc_times[0], 2),
            "avg_ms": round(float(np.mean(fc_times)), 2),
            "peak_ms": round(float(np.max(fc_times)), 2),
            "status": r.status_code
        }

        # 5. POST /api/commute/optimize
        now = datetime.now(timezone.utc)
        payload_commute = {
            "origin": {"latitude": 28.6315, "longitude": 77.2167},
            "destination": {"latitude": 28.5355, "longitude": 77.3910},
            "mode": "cycling",
            "departure_window": {
                "start": (now + timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
                "interval_minutes": 15
            }
        }
        t0 = time.perf_counter()
        r = client.post("/api/commute/optimize", json=payload_commute)
        cold_commute = (time.perf_counter() - t0) * 1000.0
        commute_times = []
        for _ in range(5):
            t = time.perf_counter()
            client.post("/api/commute/optimize", json=payload_commute)
            commute_times.append((time.perf_counter() - t) * 1000.0)
        results["POST /api/commute/optimize"] = {
            "cold_start_ms": round(cold_commute, 2),
            "warm_ms": round(commute_times[0], 2),
            "avg_ms": round(float(np.mean(commute_times)), 2),
            "peak_ms": round(float(np.max(commute_times)), 2),
            "status": r.status_code
        }

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    benchmark_endpoints()
