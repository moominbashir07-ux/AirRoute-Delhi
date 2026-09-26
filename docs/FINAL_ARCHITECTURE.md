# FINAL PRODUCTION ARCHITECTURE

**System:** Air Quality Index (AQI) Predictor & Commuter Environmental Exposure Advisor (`weather-final`)  
**Phase:** Phase 5 — Production Hardening & Final Release  
**Operating Environment:** Zero-Cost / Self-Hosted / Free-Tier-Compatible  

---

## 1. System Topology & Data Flow

```text
                               ┌─────────────────────────────────────────┐
                               │           Commuter Web Client           │
                               │        React 18 + Vite + Tailwind       │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    │ HTTPS / JSON
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │          FastAPI Gateway API            │
                               │        Uvicorn / Asgi Container         │
                               └────────────────────┬────────────────────┘
                                                    │
             ┌──────────────────────────────────────┼──────────────────────────────────────┐
             │                                      │                                      │
             ▼                                      ▼                                      ▼
┌─────────────────────────┐            ┌─────────────────────────┐            ┌─────────────────────────┐
│     Corridor Engine     │            │  Station Spatial Index  │            │ Rate Limiting & Auth    │
│  - Geodesic 1km steps   │            │  - 42 Delhi CAAQM sites │            │  - In-memory sliding win│
│  - WGS84 haversine      │            │  - KD-Tree / Haversine  │            │  - X-Request-ID headers │
│  - Boundary validation  │            │  - 10km spatial horizon │            │  - Structured logging   │
└────────────┬────────────┘            └────────────┬────────────┘            └─────────────────────────┘
             │                                      │
             └──────────────────┬───────────────────┘
                                │ Mapped Corridor Segments
                                ▼
             ┌──────────────────────────────────────────────────────────┐
             │            Multi-Horizon Forecasting Engine              │
             │       - HistGradientBoostingRegressor (scikit-learn)     │
             │       - Horizons: t+1h through t+6h direct models        │
             │       - Causal rolling means & lag features              │
             │       - Native missingness support (no zero-fill)        │
             └──────────────────────────┬───────────────────────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
             ┌─────────────────────────┐   ┌───────────────────────────┐
             │   NWP Weather Client    │   │  Phase 3E Exposure Engine │
             │  - Open-Meteo Forecast  │   │  - M = C * V_E * delta_t  │
             │  - 10s finite timeout   │   │  - Walking: 1.3 m3/h      │
             │  - Degraded cache fb    │   │  - Cycling: 2.1 m3/h      │
             │  - Non-negative bounds  │   │  - Motorized: 0.6 m3/h    │
             └─────────────────────────┘   └─────────────┬─────────────┘
                                                         │
                                                         ▼
                                           ┌───────────────────────────┐
                                           │ Departure Window Ranking  │
                                           │  - Strict 80% coverage    │
                                           │  - Inhaled dose compare   │
                                           │  - Scientific limitations │
                                           └───────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 API & Security Gateway (`backend/app.py`)
- **Framework:** FastAPI with Uvicorn ASGI server.
- **Traceability:** Inbound or generated `X-Request-ID` attached to all request state contexts, logs, and response headers.
- **Abuse Protection:** In-memory sliding-window rate limiter protecting heavy compute endpoints (`/predict`, `/forecast`, `/commute/optimize`) without introducing external paid caching layers (e.g. Redis).
- **CORS Protection:** Configurable whitelist via `CORS_ORIGINS` and `FRONTEND_ORIGIN` rejecting permissive wildcards with credentials.
- **Error Sanitization:** Centralized exception handlers ensuring internal Python tracebacks and filesystem paths are never leaked in client payloads.
- **Health & Readiness:** Dual probes (`/health` for liveness, `/ready` for SHA-256 model artifact integrity verification).

### 2.2 Corridor Geometry & Spatial Matcher (`backend/ml_model/corridor_geometry.py`)
- Discretizes commuter paths along WGS84 geodesic arcs into 1.0 km equidistant segments.
- Enforces strict Delhi/NCR bounding box ($28.20^\circ\text{N} \dots 28.95^\circ\text{N}$, $76.80^\circ\text{E} \dots 77.55^\circ\text{E}$).
- Matches each corridor segment to the nearest operational Delhi CAAQM station within a 10.0 km radius threshold.
- Rejects journeys whose transit duration plus departure window exceeds the validated 6-hour forecast ceiling.

### 2.3 Station-Level Multi-Horizon Forecasting Engine (`backend/ml_model/forecasting_engine.py`)
- Direct multi-horizon `HistGradientBoostingRegressor` (scikit-learn) models for horizons $h \in \{1, 2, 3, 4, 5, 6\}$ hours.
- Causal historical feature construction: 1h, 2h, 3h, 6h, 12h, 24h contiguous lags; 3h, 6h, 12h, 24h causal rolling averages.
- Weather integration: Temperature, relative humidity, wind speed, circular wind direction vectors ($\sin$, $\cos$), boundary layer height, surface pressure.
- Native missingness support without artificial synthetic interpolation or zero-filling.

### 2.4 Weather Telemetry & NWP Resilience (`backend/ml_model/weather_client.py`)
- Live atmospheric predictions queried from Open-Meteo NWP Forecast API.
- Configurable timeout (10.0 seconds) with bounded retries and exponential backoff.
- Fail-safe degradation: If external NWP fails, the system transitions to `degraded_historical` mode using recent verified atmospheric cycles, explicitly tagging the output with a disclaimer rather than aborting or substituting zeroes.

### 2.5 Deterministic Exposure Engine (`backend/ml_model/exposure_engine.py`)
- Physical inhalation dose calculation:
  $$M = \sum_{i=1}^{N} C_i \times V_E \times \Delta t_i$$
- Scenario ventilation assumptions:
  - `walking`: $1.3\text{ m}^3\text{/h}$ (speed: $5\text{ km/h}$)
  - `cycling`: $2.1\text{ m}^3\text{/h}$ (speed: $15\text{ km/h}$)
  - `motorized`: $0.6\text{ m}^3\text{/h}$ (speed: $30\text{ km/h}$)
- Strict coverage threshold: Minimum $80.0\%$ spatial-temporal coverage required to qualify for optimal departure recommendation.

---

## 3. Production Boundaries and External Integrations

| Subsystem | External Dependency | Free-Tier / Cost Status | Failure Behavior |
|---|---|---|---|
| Historical Data | XKDR India Air Quality (CPCB/DPCC) | Zero-Cost Open Research Cache | Read from local Parquet archive |
| Production Weather | Open-Meteo NWP Forecast API | Zero-Cost Free Tier (Non-commercial) | 10s timeout, degraded baseline fallback |
| Model Hosting | Local CPU inference | Zero-Cost Local / Free Tier | Loaded in memory at server startup |
| Rate Limiting | In-Memory Sliding Window | Zero-Cost (No external Redis required) | Drops oldest timestamps, returns 429 |
| Static Frontend | GitHub Pages / Local Node / Render Static | Zero-Cost Free Tier | Client-side routing, static assets |

---

## 4. Security Boundaries

1. **Secret Isolation:** Environment variables only; `.env` is ignored by Git, `.env.example` contains placeholders only.
2. **Path & Injection Safety:** Pydantic schema validation restricts all numeric coordinate bounds and mode whitelists.
3. **Traceability:** Uniform `X-Request-ID` attached to all logs and error objects without logging PII or exact user origins.
4. **Model Verification:** Manifest-based SHA-256 hash checking at application startup.
