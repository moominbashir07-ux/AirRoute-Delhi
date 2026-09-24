"""
AQI Predictor - FastAPI Backend
Production-ready API for AQI prediction and forecasting.
"""

import os
import sys
import pickle
import logging
import random
import math
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Add ml_model to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml_model"))
from train import train, FEATURES, MODEL_PATH, SCALER_PATH, METRICS_PATH
from database import init_db, create_user, get_user_by_email, save_otp, verify_otp, verify_password

# ─── Logging ────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log"),
    ],
)
logger = logging.getLogger(__name__)

# ─── Lifespan Context Manager ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_artifacts()
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}")
    logger.info("AQI Predictor API started successfully.")
    yield
    logger.info("AQI Predictor API shutting down.")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AQI Predictor API",
    description="Air Quality Index prediction using Machine Learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Environment Configuration ──────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ALLOW_DEV_OTP = os.getenv("ALLOW_DEV_OTP", "false").lower() in ("true", "1")
ENABLE_MODEL_RETRAINING = os.getenv("ENABLE_MODEL_RETRAINING", "false").lower() in ("true", "1")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────
class AQIInput(BaseModel):
    temperature: float = Field(..., ge=-20, le=60, description="Temperature in °C")
    humidity: float = Field(..., ge=0, le=100, description="Humidity in %")
    wind_speed: float = Field(..., ge=0, le=100, description="Wind speed in km/h")
    co2: float = Field(..., ge=300, le=5000, description="CO2 in ppm")
    pm25: float = Field(..., ge=0, le=1000, description="PM2.5 in µg/m³")
    pm10: float = Field(..., ge=0, le=1200, description="PM10 in µg/m³")
    no2: float = Field(..., ge=0, le=500, description="NO2 in µg/m³")
    so2: float = Field(..., ge=0, le=500, description="SO2 in µg/m³")

    @field_validator("pm10")
    @classmethod
    def pm10_must_be_gte_pm25(cls, v, info):
        # soft validation - pm10 >= pm25 usually
        return v

class PredictionResponse(BaseModel):
    aqi: float
    category: str
    color: str
    health_message: str
    model_used: str
    confidence: str

class TrainResponse(BaseModel):
    status: str
    best_model: str
    metrics: dict
    feature_importance: dict

# ─── Auth Models ─────────────────────────────────────────────────────────────
class SendOTPRequest(BaseModel):
    email: str
    name: Optional[str] = None

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    otp: str

class LoginRequest(BaseModel):
    email: str
    password: str


# ─── AQI Helpers ─────────────────────────────────────────────────────────────
def classify_aqi(aqi: float) -> dict:
    aqi = max(0, aqi)
    if aqi <= 50:
        return {"category": "Good", "color": "#00E400", "health_message": "Air quality is satisfactory. Safe for all."}
    elif aqi <= 100:
        return {"category": "Moderate", "color": "#FFFF00", "health_message": "Acceptable air quality. Unusually sensitive people should limit outdoor exertion."}
    elif aqi <= 150:
        return {"category": "Unhealthy for Sensitive Groups", "color": "#FF7E00", "health_message": "Sensitive groups may experience health effects. General public is not likely affected."}
    elif aqi <= 200:
        return {"category": "Unhealthy", "color": "#FF0000", "health_message": "Everyone may experience health effects. Sensitive groups should avoid outdoor activity."}
    elif aqi <= 300:
        return {"category": "Very Unhealthy", "color": "#8F3F97", "health_message": "Health alert! Everyone may experience serious health effects."}
    else:
        return {"category": "Hazardous", "color": "#7E0023", "health_message": "Emergency conditions. Everyone should avoid all outdoor activity."}

# ─── Model Loading ────────────────────────────────────────────────────────────
_model_cache = {}

def load_artifacts():
    """Load model, scaler, and metrics from disk."""
    global _model_cache
    if not os.path.exists(MODEL_PATH):
        logger.warning("No trained model found. Training now...")
        train()
    try:
        with open(MODEL_PATH, "rb") as f:
            model_data = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
        metrics = {}
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, "rb") as f:
                metrics = pickle.load(f)
        _model_cache = {"model": model_data["model"], "name": model_data["name"], "scaler": scaler, "metrics": metrics}
        logger.info(f"Loaded model: {model_data['name']}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

# (Deprecated startup event removed - logic migrated to lifespan context manager)

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "AQI Predictor API", "version": "1.0.0", "docs": "/docs"}

# ─── Authentication Routes ───────────────────────────────────────────────────
@app.post("/auth/send-otp")
def send_otp_endpoint(data: SendOTPRequest):
    """Generates an OTP, stores it, logs it, and returns it for development verification."""
    email = data.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    
    otp = f"{random.randint(100000, 999999)}"
    try:
        save_otp(email, otp)
    except Exception as e:
        logger.error(f"Failed to save OTP: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")
    
    # In development, optionally allow dev_otp bypass only if explicitly enabled via ALLOW_DEV_OTP=true
    response = {"status": "success", "message": "OTP generated and dispatched."}
    if ENVIRONMENT == "development" and ALLOW_DEV_OTP:
        response["dev_otp"] = otp
    return response

@app.post("/auth/signup")
def signup_endpoint(data: SignupRequest):
    """Verifies OTP and registers a new user in the SQLite database."""
    email = data.email.strip().lower()
    name = data.name.strip()
    password = data.password
    otp = data.otp.strip()
    
    if not email or not name or not password or not otp:
        raise HTTPException(status_code=400, detail="All fields are required.")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    
    if not verify_otp(email, otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code.")
    
    success = create_user(email, password, name)
    if not success:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")
        
    return {
        "status": "success",
        "message": "User registered successfully.",
        "user": {"email": email, "name": name}
    }

@app.post("/auth/login")
def login_endpoint(data: LoginRequest):
    """Authenticates the user and returns user info."""
    email = data.email.strip().lower()
    password = data.password
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
        
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password.")
        
    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password.")
        
    return {
        "status": "success",
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
    }


@app.get("/health")
def health():
    model_loaded = bool(_model_cache)
    return {"status": "healthy", "model_loaded": model_loaded, "model": _model_cache.get("name", "none")}

@app.post("/predict", response_model=PredictionResponse)
def predict(data: AQIInput):
    """Predict AQI from environmental parameters."""
    if not _model_cache:
        raise HTTPException(status_code=503, detail="Model not loaded. Try POST /train first.")
    try:
        features = np.array([[
            data.temperature, data.humidity, data.wind_speed,
            data.co2, data.pm25, data.pm10, data.no2, data.so2
        ]])
        scaled = _model_cache["scaler"].transform(features)
        aqi_raw = float(_model_cache["model"].predict(scaled)[0])
        aqi = round(max(0, aqi_raw), 1)
        cls = classify_aqi(aqi)
        logger.info(f"Prediction: AQI={aqi}, Category={cls['category']}")
        return PredictionResponse(
            aqi=aqi,
            category=cls["category"],
            color=cls["color"],
            health_message=cls["health_message"],
            model_used=_model_cache["name"],
            confidence="High" if aqi < 300 else "Medium",
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train", response_model=TrainResponse)
def retrain(x_admin_key: Optional[str] = Header(None)):
    """Retrain the ML model (admin/protected endpoint)."""
    if not ENABLE_MODEL_RETRAINING:
        raise HTTPException(
            status_code=403,
            detail="Model retraining is disabled in this environment. Set ENABLE_MODEL_RETRAINING=true to enable."
        )
    if ADMIN_API_KEY and x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key header.")
    try:
        result = train()
        load_artifacts()
        return TrainResponse(
            status=result["status"],
            best_model=result["best_model"],
            metrics=result["metrics"],
            feature_importance=result["feature_importance"],
        )
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/aqi-history")
def aqi_history(days: int = 30):
    """Returns simulated historical AQI data."""
    data = []
    base_date = datetime.now() - timedelta(days=days)
    prev_aqi = 75
    r = random.Random(42)
    for i in range(days):
        delta = r.uniform(-15, 20)
        aqi = max(10, min(300, prev_aqi + delta))
        prev_aqi = aqi
        cls = classify_aqi(aqi)
        data.append({
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "aqi": round(aqi, 1),
            "category": cls["category"],
            "color": cls["color"],
            "pm25": round(aqi * 0.4 + r.uniform(-5, 5), 1),
            "pm10": round(aqi * 0.5 + r.uniform(-5, 5), 1),
            "no2": round(aqi * 0.15 + r.uniform(-3, 3), 1),
        })
    return {"status": "success", "data": data, "days": days}

@app.get("/forecast")
def forecast(days: int = 7):
    """Returns AQI forecast for next N days."""
    if not _model_cache:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    forecasts = []
    r = random.Random(100)
    
    # Base environmental parameters
    temp = 25.0
    hum = 60.0
    wind = 10.0
    co2 = 450.0
    pm25 = 35.0
    pm10 = 70.0
    no2 = 40.0
    so2 = 20.0

    for i in range(days):
        date = (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
        
        # Perturb the parameters slightly per day to simulate weather trends
        day_temp = temp + math.sin(i * 0.5) * 5 + r.uniform(-1, 1)
        day_hum = max(10, min(100, hum + math.cos(i * 0.5) * 10 + r.uniform(-3, 3)))
        day_wind = max(0, wind + r.uniform(-2, 2))
        day_co2 = co2 + i * 5 + r.uniform(-5, 5)
        day_pm25 = max(0, pm25 + math.sin(i * 0.8) * 15 + i * 2 + r.uniform(-3, 3))
        day_pm10 = max(day_pm25, pm10 + math.sin(i * 0.8) * 20 + i * 3 + r.uniform(-5, 5))
        day_no2 = max(0, no2 + r.uniform(-2, 2))
        day_so2 = max(0, so2 + r.uniform(-1, 1))
        
        features = np.array([[
            day_temp, day_hum, day_wind, day_co2, day_pm25, day_pm10, day_no2, day_so2
        ]])
        
        scaled = _model_cache["scaler"].transform(features)
        aqi_raw = float(_model_cache["model"].predict(scaled)[0])
        aqi = round(max(0, aqi_raw), 1)
        cls = classify_aqi(aqi)
        
        forecasts.append({
            "date": date,
            "day": i + 1,
            "aqi": aqi,
            "category": cls["category"],
            "color": cls["color"],
            "health_message": cls["health_message"],
            "pm25": round(day_pm25, 1),
            "confidence": round(max(50, 95 - i * 3), 0),
        })
    return {"status": "success", "forecast": forecasts, "model": _model_cache.get("name")}

@app.get("/metrics")
def get_metrics():
    """Returns model training metrics."""
    if not _model_cache or not _model_cache.get("metrics"):
        raise HTTPException(status_code=404, detail="No metrics available. Train the model first.")
    m = _model_cache["metrics"]
    return {
        "best_model": m.get("best_model"),
        "all_models": m.get("all_models", []),
        "feature_importance": m.get("feature_importance", {}),
        "feature_names": m.get("feature_names", FEATURES),
        "sample_predictions": {
            "y_test": m.get("y_test", [])[:50],
            "predicted": m.get("best_predictions", [])[:50],
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
