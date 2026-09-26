# PHASE 4 IMPLEMENTATION PLAN — PRODUCTION INTEGRATION

**Repository:** `https://github.com/moominbashir07-ux/weather-final`  
**Role:** Senior Production Engineer & Systems Architect  
**Status:** PROPOSED ARCHITECTURE & INTEGRATION SPECIFICATION  

---

## 1. REPOSITORY AUDIT SUMMARY

### Tech Stack Identification
* **Backend:** FastAPI (Python 3.13), Uvicorn, Pydantic v2, SQLite (`database.py` with OTP auth), scikit-learn (`HistGradientBoostingRegressor` and Phase 2 `RandomForestRegressor`), pyarrow/pandas for Parquet telemetry.
* **Frontend:** React 19, Vite 6, TailwindCSS, Lucide-React, Recharts, Axios, React Router v7.
* **Proxy Configuration:** Vite proxies `/api/*` to `http://localhost:8000/*` with path rewrite (`/api` stripped) in `vite.config.js`. Direct backend calls use standard paths.
* **Backend Port:** 8000. **Frontend Port:** 3000.
* **CORS Settings:** Configured via `CORS_ORIGINS` environment variable (defaults to `http://localhost:3000,http://127.0.0.1:3000`).

### Preserved Existing Systems
1. **Phase 2 Baseline:**
   * Endpoints: `POST /predict`, `GET /forecast`, `GET /metrics`, `GET /aqi-history`, `GET /health`, `POST /auth/*`.
   * Artifacts: `best_model.pkl`, `scaler.pkl`, `metrics.pkl`, `real_aqi_dataset.csv`.
2. **Phase 3B Observational Layer:**
   * Canonical dataset: `backend/datasets/xkdr/station_observations_2020_2024.parquet`.
   * Station catalog: `backend/datasets/xkdr/station_catalog.csv` (42 Delhi/NCR stations).
   * Quality metadata: `missingness_audit.json`, `temporal_resolution_report.json`.
3. **Phase 3C Geometry & Feature Layer:**
   * Corridor discretization & station indexing: `backend/ml_model/corridor_geometry.py` (`StationSpatialIndex`, `discretize_corridor`, `haversine_distance`).
   * Temporal feature definitions: `backend/ml_model/temporal_features.py`.
4. **Phase 3D Forecasting Engine:**
   * Direct multi-horizon estimators: `backend/ml_model/phase3d/model_h1.pkl` through `model_h6.pkl`.
   * Weather client: `backend/ml_model/weather_client.py` (ECMWF ERA5 reanalysis and real-time NWP forecast).
   * Inference interface: `MultiHorizonForecaster.forecast_pm25()` in `backend/ml_model/forecasting_engine.py`.

---

## 2. INTEGRATION ARCHITECTURE

```
User (Origin, Destination, Mode, Departure Window)
                      │
                      ▼
             Frontend React App
                      │  POST /api/commute/optimize
                      ▼
             FastAPI Production Router
                      │
   ┌──────────────────┴──────────────────┐
   ▼                                     ▼
Request Validation            Geodesic Corridor Discretization
(WGS84, Mode, ISO Window)     (Phase 3C: 1 km segments, bearing)
   │                                     │
   └──────────────────┬──────────────────┘
                      ▼
           Nearest Station Matching
           (Phase 3C: Haversine ≤ 10 km)
                      │
                      ▼
           NWP Weather Forecast
           (Phase 3D: Open-Meteo at t+h)
                      │
                      ▼
           Multi-Horizon PM2.5 Forecast
           (Phase 3D: Models M1..M6)
                      │
                      ▼
        Deterministic Exposure Engine
        - Segment travel duration Δt_i
        - Scenario ventilation V_E (walking, cycling, motorized)
        - Inhaled PM2.5 mass m_i = C_i × V_E × Δt_i
        - Time-weighted concentration
                      │
                      ▼
        Departure Window Comparison
        - Evaluates candidates (e.g. 08:00, 08:15, 08:30)
        - Filters candidates with ≥ 80% coverage
        - Identifies lowest modeled exposure departure
                      │
                      ▼
        Structured, Explainable JSON Response
        - Segment-by-segment trace
        - Coverage metrics
        - Non-medical scientific limitations
                      │
                      ▼
             Frontend Decision Display
```

---

## 3. NEW COMPONENTS & MODULES TO BE ADDED

1. **`backend/ml_model/exposure_engine.py`:**
   * Core deterministic exposure computation ($M = \sum C_i \times V_E \times \Delta t_i$).
   * Transit speed & duration mapping:
     * Walking: $5.0\text{ km/h}$
     * Cycling: $15.0\text{ km/h}$
     * Motorized: $30.0\text{ km/h}$
   * Scenario ventilation rates:
     * Walking: $1.3\text{ m}^3\text{/hour}$
     * Cycling: $2.1\text{ m}^3\text{/hour}$
     * Motorized: $0.6\text{ m}^3\text{/hour}$
   * Departure window evaluation loop with strict 6-hour forecast horizon validation.
   * Coverage calculation (segment, distance, time).
   * Non-medical comparative explanation generation.

2. **Endpoints in `backend/app.py`:**
   * `POST /api/commute/optimize` and `POST /commute/optimize`
   * `GET /api/stations/delhi` and `GET /stations/delhi`

3. **Frontend Integration:**
   * `frontend/src/pages/Commute.jsx`: New Commuter Exposure Advisor page.
   * Update `frontend/src/components/Navbar.jsx`: Add Commute link with navigation icon.
   * Update `frontend/src/App.jsx`: Add route `/commute`.
   * Update `frontend/src/utils/api.js`: Add `optimizeCommute` and `getDelhiStations`.

4. **Testing Suite:**
   * `backend/tests/test_phase4_api_commute.py`: Comprehensive API contract tests.
   * `backend/tests/test_phase4_exposure_engine.py`: Unit tests for exposure calculations and window comparisons.
   * Frontend production build check (`npm run build`).

---

## 4. API CONTRACT SPECIFICATIONS

### `POST /api/commute/optimize`
#### Request Body:
```json
{
  "origin": {
    "latitude": 28.6315,
    "longitude": 77.2167
  },
  "destination": {
    "latitude": 28.4950,
    "longitude": 77.0895
  },
  "mode": "cycling",
  "departure_window": {
    "start": "2026-09-25T08:00:00+05:30",
    "end": "2026-09-25T09:30:00+05:30",
    "interval_minutes": 15
  }
}
```

#### Response Body:
```json
{
  "status": "success",
  "recommended_departure": {
    "departure_time_ist": "2026-09-25T08:15:00+05:30",
    "departure_time_utc": "2026-09-25T02:45:00Z",
    "estimated_inhaled_pm25_ug": 42.15,
    "time_weighted_pm25_ug_m3": 75.3,
    "journey_duration_minutes": 68.2,
    "coverage_percent": 100.0,
    "modeled_exposure_reduction_percent": 14.5
  },
  "corridor_summary": {
    "distance_km": 17.05,
    "total_segments": 18,
    "mode": "cycling",
    "assumed_speed_km_h": 15.0,
    "assumed_ventilation_rate_m3_h": 2.1
  },
  "departure_candidates": [
    {
      "departure_time_ist": "2026-09-25T08:00:00+05:30",
      "estimated_inhaled_pm25_ug": 49.3,
      "time_weighted_pm25_ug_m3": 88.1,
      "coverage_percent": 100.0,
      "is_recommended": false
    },
    {
      "departure_time_ist": "2026-09-25T08:15:00+05:30",
      "estimated_inhaled_pm25_ug": 42.15,
      "time_weighted_pm25_ug_m3": 75.3,
      "coverage_percent": 100.0,
      "is_recommended": true
    }
  ],
  "segment_breakdown": [
    {
      "segment_index": 0,
      "midpoint": {"latitude": 28.6277, "longitude": 77.2132},
      "length_km": 0.95,
      "travel_time_minutes": 3.8,
      "mapped_station_id": "site_119",
      "station_name": "Sirifort, Delhi - CPCB",
      "station_distance_km": 1.42,
      "forecasted_pm25_ug_m3": 72.1,
      "segment_inhaled_dose_ug": 2.38
    }
  ],
  "limitations": [
    "Ambient station forecasts represent neighborhood air masses rather than micro-scale street canyon concentrations.",
    "Forecast horizon is validated up to 6 hours ahead; journeys exceeding 6 hours are not modeled.",
    "Inhaled dose is an environmental exposure index based on scenario ventilation assumptions (walking=1.3, cycling=2.1, motorized=0.6 m³/h), not clinical medical advice.",
    "Predictions rely on numerical weather prediction (NWP) telemetry; forecast errors in meteorology propagate into PM2.5 estimates."
  ],
  "scientific_disclaimer": "This is an environmental exposure estimate for comparative transit scheduling. It is NOT a medical diagnosis, clinical health assessment, or guarantee of health safety."
}
```

---

## 5. RISK ANALYSIS & MITIGATIONS

1. **Risk:** NWP external API rate-limiting or downtime.  
   *Mitigation:* Local in-memory caching of NWP weather per hourly window and graceful degraded status if Open-Meteo times out.
2. **Risk:** Excessive journey duration exceeding the 6-hour forecast window.  
   *Mitigation:* Strict validation rejecting trips whose arrival time exceeds $T_0 + 6\text{h}$.
3. **Risk:** High API latency from reloading ML models per request.  
   *Mitigation:* Singleton model cache loaded during FastAPI lifespan startup, enabling sub-50ms inference.
4. **Risk:** Misinterpretation of exposure scores as medical claims.  
   *Mitigation:* Prominent disclaimer banners on both frontend UI and API payload.
