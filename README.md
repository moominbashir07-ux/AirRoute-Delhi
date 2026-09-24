# 🌬️ AQI Predictor — Air Quality Forecasting System

An end-to-end full-stack web application for Air Quality Index (AQI) estimation and environmental health awareness. Built with React 18, FastAPI, and scikit-learn.

![AQI Predictor](https://img.shields.io/badge/ML-Prototype-22d3ee?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)

> **Phase 1 Baseline Status:** The current machine learning pipeline utilizes a synthetic generator to demonstrate the end-to-end regression workflow and model export architecture. Training on real-world monitoring datasets (e.g. OpenAQ / EPA) and advanced temporal forecasting are scheduled for Phase 2.

---

## ✨ Features

- **Interactive AQI Predictor** — Dual-mode input (manual sliders + live Open-Meteo coordinate autofill) with an animated SVG semicircle gauge.
- **7-Day Weather & Air Telemetry** — Interactive multi-day charts powered by Open-Meteo's global weather and atmospheric data feeds.
- **Analytics & Model Metrics** — Feature importance visualizations, predicted-vs-actual scatter views, and historical trend charts.
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
│   │   ├── train.py            # Baseline ML pipeline (scikit-learn)
│   │   ├── best_model.pkl      # Pickled model artifact
│   │   ├── scaler.pkl          # Pickled feature scaler
│   │   └── metrics.pkl         # Serialized training metrics
│   ├── datasets/
│   │   └── aqi_dataset.csv     # Historical reference CSV
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

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create local environment config
cp .env.example .env

# Train baseline model artifacts (if best_model.pkl does not exist)
python ml_model/train.py

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
| `POST` | `/train` | Trigger model retraining | **Protected** (Requires `ENABLE_MODEL_RETRAINING=true` and optional `X-Admin-Key`) |

---

## 🤖 Baseline Machine Learning Pipeline

The baseline pipeline in `backend/ml_model/train.py` evaluates three standard regression algorithms:
- **Linear Regression**
- **Random Forest Regressor** ($n=100$)
- **Decision Tree Regressor** ($\text{max\_depth}=10$)

Features evaluated:
- Ambient: `temperature`, `humidity`, `wind_speed`
- Pollutants: `pm25`, `pm10`, `no2`, `so2`, `co2`

*Note on baseline evaluation:* Models in Phase 1 are fitted against a controlled mathematical generator for architecture validation. Ground-truth historical training against real municipal monitoring stations is part of Phase 2.

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

```ini
ENVIRONMENT=development
PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOW_DEV_OTP=false
ENABLE_MODEL_RETRAINING=false
ADMIN_API_KEY=
```

### Frontend (`frontend/.env`)

```ini
VITE_API_URL=/api
VITE_EMAILJS_PUBLIC_KEY=
```

---

## 🏥 Health & Safety Disclaimer

AQI predictions and advisory recommendations are for educational and situational awareness only. Always consult official municipal monitoring agencies and medical professionals for critical health decisions.
