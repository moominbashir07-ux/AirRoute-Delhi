# REPRODUCIBILITY GUIDE

**System:** Air Quality Index Predictor & Commuter Environmental Exposure Advisor  
**Repository:** `https://github.com/moominbashir07-ux/weather-final`  
**Phase:** Phase 5 Production Release  

---

## 1. System Requirements

- **Operating System:** Windows 10/11, Ubuntu 22.04 LTS+, or macOS 13+
- **Python Runtime:** Python 3.10, 3.11, 3.12, or 3.13
- **Node Runtime:** Node.js v18.x or v20.x (with npm v9+)
- **Memory:** Minimum 4 GB RAM recommended
- **Disk Space:** ~500 MB for repository, dependencies, and model artifacts

---

## 2. Environment Setup

### 2.1 Clone Repository
```bash
git clone https://github.com/moominbashir07-ux/weather-final.git
cd weather-final
```

### 2.2 Environment Variables
Copy `.env.example` to `.env` in the root and `backend/` directories:
```bash
cp .env.example .env
cp .env.example backend/.env
```

Configuration keys:
```env
ENVIRONMENT=production
PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173
FRONTEND_ORIGIN=http://localhost:5173
XKDR_API_KEY=
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1
NWP_TIMEOUT_SECONDS=10.0
ALLOW_DEV_OTP=false
ENABLE_MODEL_RETRAINING=false
ADMIN_API_KEY=
RATE_LIMIT_PER_MINUTE=60
```

---

## 3. Backend Setup & Startup

### 3.1 Python Virtual Environment
```bash
cd backend
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### 3.2 Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt pytest httpx pyarrow
```

### 3.3 Verify Model Artifact Integrity
Run the SHA-256 integrity verifier to ensure all 10 pre-trained production model files and catalogs match `model_manifest.json`:
```bash
python -c "from ml_model.model_integrity import verify_artifact_integrity; r = verify_artifact_integrity(); print('Integrity check:', r['status'], f'({r[\"verified_artifacts\"]}/{r[\"total_artifacts\"]} artifacts verified)')"
```

### 3.4 Run Test Suite
Execute the full 95-test suite:
```bash
pytest tests/ -v
```

### 3.5 Start Backend Server
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```
- API will be accessible at: `http://localhost:8000`
- Swagger Documentation: `http://localhost:8000/docs`
- Health Liveness Probe: `http://localhost:8000/health`
- Readiness Integrity Probe: `http://localhost:8000/ready`

---

## 4. Frontend Setup & Build

### 4.1 Install Node Dependencies
```bash
cd ../frontend
npm ci
```

### 4.2 Run Development Server
```bash
npm run dev
```
Accessible at `http://localhost:5173`. Proxies `/api/*` to `http://localhost:8000`.

### 4.3 Build Production Bundle
```bash
npm run build
```
Creates minified assets in `frontend/dist/`.

---

## 5. End-to-End API Verification

Execute a test commuter corridor optimization via cURL:
```bash
curl -X POST "http://localhost:8000/api/commute/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {"latitude": 28.6315, "longitude": 77.2167},
    "destination": {"latitude": 28.5355, "longitude": 77.3910},
    "mode": "cycling",
    "departure_window": {
      "start": "2026-09-25T08:00:00+05:30",
      "end": "2026-09-25T09:30:00+05:30",
      "interval_minutes": 15
    }
  }'
```
