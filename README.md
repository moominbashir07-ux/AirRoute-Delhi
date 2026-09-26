# 🚴 AirRoute Delhi

> **A commuter PM2.5 exposure advisor that forecasts PM2.5 along Delhi/NCR commute corridors and estimates inhaled exposure across departure windows.**

[![Production Hardened](https://img.shields.io/badge/Release-Hardened_Production-22d3ee?style=for-the-badge)](https://air-route-delhi.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.11.9-3776ab?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react)](https://react.dev/)
[![Tests](https://img.shields.io/badge/Tests-108_Passing-10b981?style=for-the-badge)](https://github.com/moominbashir07-ux/weather-final)

---

## 🌐 Live Application & API Links

> 🔗 **Live Web Application:** [https://air-route-delhi.vercel.app](https://air-route-delhi.vercel.app)  
> ⚡ **Live Backend API:** [https://airroute-delhi.onrender.com](https://airroute-delhi.onrender.com)  
> 📖 **Interactive Swagger / OpenAPI Docs:** [https://airroute-delhi.onrender.com/docs](https://airroute-delhi.onrender.com/docs)

| Service | Platform | Direct Link | Status |
|---|---|---|:---:|
| **AirRoute Delhi Web App** | Vercel | [https://air-route-delhi.vercel.app](https://air-route-delhi.vercel.app) | 🟢 Online |
| **Production FastAPI Backend** | Render | [https://airroute-delhi.onrender.com](https://airroute-delhi.onrender.com) | 🟢 Online |
| **Interactive API Documentation** | Swagger UI | [https://airroute-delhi.onrender.com/docs](https://airroute-delhi.onrender.com/docs) | 🟢 Online |

---

## 💡 What is AirRoute Delhi?

During peak pollution episodes in Delhi/NCR, particulate matter ($\text{PM}_{2.5}$) levels routinely reach hazardous thresholds. Traditional air quality applications only provide static regional averages or warn commuters after the air has deteriorated.

**AirRoute Delhi transforms passive air quality monitoring into actionable commuter protection.** Given an origin, destination, desired departure time, and mode of travel, AirRoute Delhi:

1. **Calculates Corridor Geometry:** Breaks transit routes into 1 km geodesic spatial segments across Delhi/NCR.
2. **Maps Real-Time Monitoring:** Associates each segment with the nearest of 42 official Continuous Ambient Air Quality Monitoring (CAAQM) stations.
3. **Forecasts Multi-Horizon PM2.5:** Uses trained direct gradient boosted tree models to project $\text{PM}_{2.5}$ concentrations for lead times $t+1\text{h}$ through $t+6\text{h}$ ahead of departure.
4. **Estimates Cumulative Inhaled Dose:** Applies physiological minute ventilation factors ($V_E$) and mode-specific transit durations:
   $$M = \sum_{i=1}^{N} C_i \times V_E \times \Delta t_i$$
5. **Recommends Departure Windows:** Compares the chosen departure with alternative shifts (e.g. Leave Now vs. $+30\text{m}$, $+1\text{h}$, $+2\text{h}$), identifying windows that cut inhaled exposure by up to $30\text{--}50\%$.

---

## 🏗️ System Architecture

```text
                                 ┌─────────────────────────────────────────┐
                                 │           Commuter Web Client           │
                                 │       React 18 + Vite + DM Sans/Syne    │
                                 │   https://air-route-delhi.vercel.app    │
                                 └────────────────────┬────────────────────┘
                                                      │
                                                      │ HTTPS / JSON
                                                      ▼
                                 ┌─────────────────────────────────────────┐
                                 │          FastAPI Gateway API            │
                                 │         Uvicorn / Python 3.11.9         │
                                 │   https://airroute-delhi.onrender.com   │
                                 └────────────────────┬────────────────────┘
                                                      │
                ┌─────────────────────────────────────┼─────────────────────────────────────┐
                │                                     │                                     │
                ▼                                     ▼                                     ▼
 ┌─────────────────────────┐           ┌─────────────────────────┐           ┌─────────────────────────┐
 │     Corridor Engine     │           │  Station Spatial Index  │           │   Hardened Security     │
 │  - Geodesic 1km steps   │           │  - 42 Delhi CAAQM sites │           │  - Salted SHA-256 OTP   │
 │  - Great-circle WGS84   │           │  - Haversine KD-Tree    │           │  - EmailJS integration  │
 │  - Boundary validation  │           │  - Catalog fallback     │           │  - Sliding-window rate  │
 └────────────┬────────────┘           └────────────┬────────────┘           └─────────────────────────┘
                │                                     │
                └──────────────────┬──────────────────┘
                                   │ Mapped Corridor Segments
                                   ▼
                ┌──────────────────────────────────────────────────────────┐
                │             Multi-Horizon Forecasting Engine             │
                │        - HistGradientBoostingRegressor (scikit-learn)    │
                │        - Horizons: t+1h through t+6h direct models       │
                │        - Trained on 1.73M canonical CAAQM hourly records │
                └──────────────────────────┬───────────────────────────────┘
                                           │ Segment-level PM2.5
                                           ▼
                ┌──────────────────────────────────────────────────────────┐
                │             Commuter Exposure Estimation                 │
                │           - Inhaled Dose: M = Σ (C_i * V_E * Δt_i)       │
                │           - Mode ventilation (walk, cycle, car, metro)   │
                │           - Multi-window departure minimization          │
                └──────────────────────────────────────────────────────────┘
```

---

## 🔬 Machine Learning & Forecasting Models

AirRoute Delhi avoids recursive error compounding by utilizing **direct multi-horizon forecasting models** ($h \in \{1, 2, 3, 4, 5, 6\}$ hours ahead):

- **Algorithm:** `sklearn.ensemble.HistGradientBoostingRegressor`
- **Training Dataset:** 1,732,402 canonical hourly records (2020–2024) across 42 Delhi CAAQM monitoring stations sourced from XKDR / Central Pollution Control Board (CPCB).
- **Meteorological Predictors:** ECMWF ERA5 reanalysis (training) and Open-Meteo Global NWP Forecasts (live inference), including 2m temperature, relative humidity, 10m wind speed, circular wind direction vectors ($\sin/\cos$), surface pressure, and planetary boundary layer height.
- **Station Spatial Conditioning:** Latitude and longitude coordinates incorporated directly to allow regional spatial transfer.

### Benchmark Evaluation (Holdout Test Set):

| Forecast Horizon | Test MAE ($\mu\text{g/m}^3$) | Test RMSE ($\mu\text{g/m}^3$) | Test $R^2$ | Improvement over Persistence Baseline |
|:---:|:---:|:---:|:---:|:---:|
| **$t+1\text{h}$** | **12.41** | 21.08 | **0.941** | **+21.5%** |
| **$t+2\text{h}$** | **17.89** | 29.54 | **0.884** | **+25.8%** |
| **$t+3\text{h}$** | **22.15** | 36.20 | **0.826** | **+27.7%** |
| **$t+4\text{h}$** | **25.72** | 41.65 | **0.770** | **+28.8%** |
| **$t+5\text{h}$** | **28.64** | 46.18 | **0.718** | **+29.8%** |
| **$t+6\text{h}$** | **31.12** | 49.92 | **0.672** | **+30.2%** |

*For complete training methodology, data provenance, and hyperparameter specifications, see [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).*

---

## 🔌 API Endpoints

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/` | API status greeting and documentation link | Public |
| `GET` | `/health` | Liveness probe (verifies app status and model cache) | Public |
| `GET` | `/ready` | Readiness probe (verifies integrity of all 10 model artifacts) | Public |
| `POST` | `/api/commute` | Plan commute route, forecast segment PM2.5, and minimize exposure | Public |
| `GET` | `/api/corridors` | Retrieve predefined popular Delhi/NCR commute corridors | Public |
| `POST` | `/auth/send-otp` | Securely dispatch 6-digit OTP via EmailJS | Public |
| `POST` | `/auth/signup` | Register new user with validated OTP | Public |
| `POST` | `/auth/login` | Authenticate user credentials | Public |
| `GET` | `/metrics` | Production model benchmark metrics & holdout scores | Public |
| `GET` | `/docs` | Interactive Swagger UI API documentation | Public |

---

## 🚀 Local Development Setup

### 1. Prerequisites
- **Python 3.11** (`python --version`)
- **Node.js 18+** & **npm** (`node -v`, `npm -v`)

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run the 108 automated test suite
python -m pytest tests/ -v

# Start the development server
python app.py
# Backend runs at http://localhost:8000
# OpenAPI Docs at http://localhost:8000/docs
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
# Frontend runs at http://localhost:3000

# Validate production build
npm run build
```

---

## 🛡️ Limitations & Scientific Boundaries

1. **NWP Weather Forecast Uncertainty:** In live production, forward predictions consume Numerical Weather Prediction (NWP) forecast models. Forecast errors in predicted boundary layer height or wind speed introduce additional variance not present in retrospective benchmarks.
2. **Station Placement vs. Micro-Environments:** Official CAAQM stations sample regional urban background concentrations at elevated monitoring locations. They do not capture micro-scale vehicle tailpipe plumes or street-canyon turbulence.
3. **Extreme Episodic Spikes:** Tree-based ensemble regressors tend to regress toward intermediate conditional means and may underestimate sudden, extreme pollution spikes (e.g. episodic post-harvest stubble burning or fireworks).
4. **Horizon Ceiling:** Model accuracy degrades past lead times of 6 hours; forecast requests beyond 6 hours are intentionally rejected by the system.

---

## 📜 License

Open Academic & Non-Commercial Research License. Developed for Delhi/NCR commuter exposure mitigation.
