# 🌬️ AQI Predictor — Air Quality Forecasting System

An end-to-end full-stack web application for Air Quality Index (AQI) estimation and environmental health awareness. Built with React 18, FastAPI, and scikit-learn.

![AQI Predictor](https://img.shields.io/badge/ML-Production--Grade-22d3ee?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)

> **Phase 2 Status (Complete):** The synthetic generator has been replaced with a real-world, leakage-safe dataset and production ML pipeline. Trained on 17,544 continuous hourly atmospheric observations from Copernicus CAMS and ECMWF ERA5 reanalysis (New Delhi NCR, 2023–2024). Evaluated against an untouched chronological holdout test set (Autumn/Winter 2024) achieving **Test $R^2 = 0.6675$** and **Test $\text{MAE} = 18.42$**.

---

## ✨ Features

- **Interactive AQI Predictor** — Dual-mode input (manual sliders + live Open-Meteo coordinate autofill) with an animated SVG semicircle gauge.
- **7-Day Weather & Air Telemetry** — Interactive multi-day charts powered by Open-Meteo's global weather and atmospheric data feeds.
- **Analytics & Model Metrics** — Real-world feature importance visualizations, predicted-vs-actual scatter views, and multi-model benchmark metrics.
- **Health Advisories** — EPA standard health advisory mappings providing preventative guidance for sensitive and general groups.
- **Dark Cyberpunk Theme** — Responsive dark UI with CSS custom properties, Syne display typography, and smooth transitions.

---

## 🏗️ Project Structure

```
aqi-predictor/
├── backend/
│   ├── app.py                  # FastAPI application with security controls & CORS
│   ├── database.py             # SQLite helper for user credentials and OTPs
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Backend environment template
│   ├── ml_model/
│   │   ├── ingest.py           # Real-world Copernicus CAMS & ERA5 ingestion pipeline
│   │   ├── train.py            # Leakage-safe ML training & evaluation pipeline
│   │   ├── best_model.pkl      # Production Random Forest model artifact
│   │   ├── scaler.pkl          # StandardScaler fitted strictly on training partition
│   │   ├── metrics.pkl         # Serialized training & holdout evaluation metrics
│   │   ├── metrics.json        # Transparent train/val/test metrics report
│   │   ├── feature_metadata.json # Input contract schema, units, and ranges
│   │   └── model_provenance.json # Versioned lineage & training provenance metadata
│   ├── datasets/
│   │   ├── real_aqi_dataset.csv # 17,544 verified hourly observations (2023-2024)
│   │   └── dataset_metadata.json# Ingestion lineage, licenses, and units
│   ├── tests/
│   │   ├── test_api_smoke.py   # Foundation security & endpoint smoke tests
│   │   └── test_ml_pipeline.py # ML dataset, leakage, split, and model test suite
│   └── logs/                   # Local runtime logs (git-ignored)
│
└── frontend/
    ├── src/
    │   ├── App.jsx             # React Router (5 routes)
    │   ├── main.jsx            # Entry point (basename configured)
    │   ├── index.css           # Global tokens & Tailwind utilities
    │   ├── components/
    │   │   ├── Navbar.jsx      # Navigation, dynamic health polling, auth modal toggle
    │   │   ├── AQIGauge.jsx    # SVG semicircle gauge with animated needle
    │   │   ├── ParamInput.jsx  # Dual slider + number input
    │   │   ├── StatCard.jsx    # Metric KPI card
    │   │   └── AuthModal.jsx   # Authentication popup (Canvas captcha + OTP)
    │   ├── pages/
    │   │   ├── Home.jsx        # Landing page with authentic dashboard preview
    │   │   ├── Predictor.jsx   # Form with Open-Meteo geolocation
    │   │   ├── Forecast.jsx    # 7-day weather & air telemetry dashboard
    │   │   ├── Analytics.jsx   # Charts & model comparison metrics
    │   │   └── Settings.jsx    # Responsive configuration panel
    │   ├── context/
    │   │   └── SettingsContext.jsx # LocalStorage persistence provider
    │   └── utils/
    │       ├── api.js          # Centralized Axios client
    │       └── aqi.js          # EPA thresholds and helpers
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

---

## 🔬 Machine Learning Pipeline & Data Provenance

### 1. Data Provenance & Ingestion
- **Source:** Copernicus Atmosphere Monitoring Service (CAMS) & European Centre for Medium-Range Weather Forecasts (ECMWF) ERA5 reanalysis archive via Open-Meteo Open Data API.
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Geographic Coverage:** New Delhi NCR, India ($28.6139^\circ\text{ N}, 77.2090^\circ\text{ E}$).
- **Time Period:** January 1, 2023 00:00 to December 31, 2024 23:00 ($17,544$ continuous hourly samples).
- **Target Variable:** US EPA Air Quality Index ($0\text{--}500$ scale, continuous calculation per EPA-454/B-18-007).

### 2. Input Features & Canonical Order

```python
FEATURE_ORDER = [
    "temperature",  # Ambient 2m temperature (°C)
    "humidity",     # Relative humidity (%)
    "wind_speed",   # 10m wind speed (km/h)
    "co2",          # Ambient Carbon Monoxide (µg/m³)
    "pm25",         # Particulate matter <= 2.5 µm (µg/m³)
    "pm10",         # Particulate matter <= 10 µm (µg/m³)
    "no2",          # Nitrogen dioxide (µg/m³)
    "so2",          # Sulfur dioxide (µg/m³)
]
```

### 3. Leakage Prevention & Chronological Splitting
To avoid temporal autocorrelation and lookahead leakage, splitting is strictly chronological:
- **Train Set:** `2023-01-01 00:00` to `2024-04-30 23:00` ($11,664$ samples, $66.5\%$)
- **Validation Set:** `2024-05-01 00:00` to `2024-08-31 23:00` ($2,952$ samples, $16.8\%$)
- **Holdout Test Set:** `2024-09-01 00:00` to `2024-12-31 23:00` ($2,928$ samples, $16.7\%$) — covers the critical autumn/winter smog season.

**Leakage Controls:**
- `StandardScaler` is fitted strictly on `X_train`. Validation and Test partitions are transformed using training parameters.
- No target-derived features or post-event signals are provided to the model.
- Test partition was completely isolated during model selection.

### 4. Benchmark Model Evaluation (Chronological Test Holdout)

| Model | Test $R^2$ | Test MAE | Test RMSE | Status |
|---|---|---|---|---|
| **Mean Predictor Baseline** | $-0.1507$ | $36.77$ | $44.85$ | Reference Baseline |
| **Linear Regression** | $0.5384$ | $22.08$ | $28.40$ | Linear Baseline |
| **Decision Tree** ($\text{depth}=10$) | $0.5102$ | $22.35$ | $29.26$ | Tree Baseline |
| **HistGradientBoosting** | $0.6636$ | $18.51$ | $24.25$ | Gradient Boosted |
| **Random Forest** ($n=100$) | **$0.6675$** | **$18.42$** | **$24.11$** | **Production Model** |

### 5. Feature Importance
- $\text{PM}_{2.5}$: **$65.1\%$** (Primary driver of severe AQI events)
- $\text{PM}_{10}$: **$5.7\%$**
- $\text{NO}_2$: **$5.7\%$**
- $\text{Temperature}$: **$5.5\%$**
- $\text{CO}$: **$4.9\%$**
- $\text{SO}_2$: **$4.8\%$**
- $\text{Humidity}$: **$4.7\%$**
- $\text{Wind Speed}$: **$3.7\%$**

### 6. Limitations & Scientific Boundaries
- **Geographic Generalization:** The model is trained on atmospheric data from New Delhi NCR. Atmospheric chemistry, boundary-layer dynamics, and local emission sources vary by climate zone; applying this model to coastal or temperate regions without localized fine-tuning may reduce accuracy.
- **Sensor vs Satellite Reanalysis:** CAMS combines satellite retrievals with ECMWF integrated forecasting; local micro-climates (e.g. street canyons) may differ from regional grid cells.

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create local environment config
cp .env.example .env

# Ingest dataset & train ML pipeline
python ml_model/train.py

# Run verification test suite (20 automated tests)
pytest tests/ -v

# Start the API server
python app.py
# API runs at: http://localhost:8000
# OpenAPI Docs: http://localhost:8000/docs
```

### 2. Frontend Setup

```bash
cd frontend

# Install npm packages
npm install

# Start development server
npm run dev
# Frontend runs at: http://localhost:3000

# Run production build
npm run build
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| `GET` | `/` | API status and root greeting | Public |
| `GET` | `/health` | Health check & model status | Public |
| `POST` | `/predict` | Predict AQI from 8 parameters | Public |
| `POST` | `/auth/send-otp` | Generate OTP for email verification | Public |
| `POST` | `/auth/signup` | Register user with verified OTP | Public |
| `POST` | `/auth/login` | Authenticate user credentials | Public |
| `GET` | `/aqi-history?days=30` | Historical simulated AQI series | Public |
| `GET` | `/forecast?days=7` | Multi-day model forecast | Public |
| `GET` | `/metrics` | Model training metrics & feature weights | Public |
| `POST` | `/train` | Trigger model retraining | **Protected** (Requires `ENABLE_MODEL_RETRAINING=true` and `X-Admin-Key`) |

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

```ini
ENVIRONMENT=development
PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
EMAILJS_SERVICE_ID=
EMAILJS_TEMPLATE_ID=
EMAILJS_PUBLIC_KEY=
EMAILJS_PRIVATE_KEY=
ENABLE_MODEL_RETRAINING=false
ADMIN_API_KEY=
```

### Frontend (`frontend/.env`)

```ini
VITE_API_URL=/api
```

---

## 🏥 Health & Safety Disclaimer

AQI predictions and advisory recommendations are for educational and situational awareness only. Always consult official municipal monitoring agencies and medical professionals for critical health decisions.
