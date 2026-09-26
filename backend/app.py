"""
AirRoute Delhi - FastAPI Backend
Production API for commuter PM2.5 forecasting and exposure advisory across Delhi/NCR.
"""

import os
import sys
import pickle
import logging
import random
import math
import uuid
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Any
from contextlib import asynccontextmanager

import numpy as np
import re
import secrets
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Add ml_model and root backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml_model"))
sys.path.insert(0, os.path.dirname(__file__))
from train import train, FEATURES, MODEL_PATH, SCALER_PATH, METRICS_PATH
from database import (
    init_db, create_user, get_user_by_email, save_otp, verify_otp,
    verify_password, can_request_otp, delete_otp, create_or_get_user
)
from email_service import send_otp_email
from model_integrity import verify_artifact_integrity

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
        integrity_report = verify_artifact_integrity()
        if integrity_report["status"] != "valid":
            logger.warning(f"Model integrity check warning: {integrity_report['errors']}")
        else:
            logger.info("Model artifacts integrity successfully verified against manifest.")
    except Exception as e:
        logger.warning(f"Could not complete startup integrity verification: {e}")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}")
    logger.info("AirRoute Delhi API started successfully.")
    yield
    logger.info("AirRoute Delhi API shutting down.")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AirRoute Delhi API",
    description="A commuter PM2.5 exposure advisor that forecasts PM2.5 along Delhi/NCR commute corridors and estimates inhaled exposure across departure windows.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Environment Configuration ──────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ENABLE_MODEL_RETRAINING = os.getenv("ENABLE_MODEL_RETRAINING", "false").lower() in ("true", "1")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,https://air-route-delhi.vercel.app"
)
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
frontend_origin = os.getenv("FRONTEND_ORIGIN", "https://air-route-delhi.vercel.app").strip()
if frontend_origin and frontend_origin not in cors_origins:
    cors_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://air-route-delhi.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ─── Rate Limiting & Traceability Middleware ─────────────────────────────────
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
_rate_limit_records = defaultdict(list)
RATE_LIMITED_PATHS = {
    "/predict", "/forecast", "/commute/optimize", "/api/commute/optimize", "/train",
    "/auth/send-otp", "/auth/verify-otp"
}

def is_rate_limited(client_ip: str, path: str) -> bool:
    """In-memory sliding-window rate limiter per client IP."""
    if path not in RATE_LIMITED_PATHS:
        return False
    now = time.time()
    cutoff = now - 60.0
    history = _rate_limit_records[client_ip]
    _rate_limit_records[client_ip] = [ts for ts in history if ts > cutoff]
    if len(_rate_limit_records[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_limit_records[client_ip].append(now)
    return False

@app.middleware("http")
async def production_hardening_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id

    client_ip = request.client.host if request.client else "127.0.0.1"
    if is_rate_limited(client_ip, request.url.path):
        logger.warning(f"Rate limit exceeded for IP {client_ip} on {request.url.path} [ReqID: {req_id}]")
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please wait before retrying.",
                    "request_id": req_id
                },
                "detail": "Too many requests. Please retry in 60 seconds."
            },
            headers={"X-Request-ID": req_id, "Retry-After": "60"}
        )

    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000.0
        response.headers["X-Request-ID"] = req_id
        logger.info(
            f"{request.method} {request.url.path} | Status: {response.status_code} | "
            f"{duration_ms:.1f}ms | ReqID: {req_id}"
        )
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000.0
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path} | "
            f"{duration_ms:.1f}ms | ReqID: {req_id} | Error: {e}",
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact support.",
                    "request_id": req_id
                },
                "detail": "Internal server error."
            },
            headers={"X-Request-ID": req_id}
        )

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": req_id
            },
            "detail": exc.detail
        },
        headers={"X-Request-ID": req_id}
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
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def is_valid_email(email: str) -> bool:
    """Validate RFC-compliant email length, structure, and domain format."""
    if not email or len(email) > 254 or "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    if not local or not domain or len(local) > 64 or len(domain) > 255:
        return False
    if ".." in domain or domain.startswith(".") or domain.endswith("."):
        return False
    return bool(EMAIL_REGEX.match(email))

class SendOTPRequest(BaseModel):
    email: str
    name: Optional[str] = None

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
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
    return {"message": "AirRoute Delhi API", "version": "1.0.0", "docs": "/docs"}

# ─── Authentication Routes ───────────────────────────────────────────────────
@app.post("/auth/send-otp")
def send_otp_endpoint(data: SendOTPRequest):
    """
    Generates a cryptographically secure 6-digit OTP, records its salted cryptographic hash,
    and dispatches it via EmailJS REST API. Never returns plaintext OTP.
    """
    email = data.email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # 1. Enforce cooldown and per-email rate limiting
    allowed, reason, retry_after = can_request_otp(email, cooldown_seconds=60, max_requests_per_hour=5)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": reason
                },
                "detail": reason,
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )

    # 2. Cryptographically secure 6-digit OTP
    otp = f"{secrets.randbelow(900000) + 100000}"

    # 3. Store salted hash in SQLite database
    try:
        save_otp(email, otp, expires_in_seconds=300, max_attempts=5)
    except Exception as e:
        logger.error(f"Failed to record pending OTP in database: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

    # 4. Dispatch via EmailJS REST API
    success, email_msg = send_otp_email(to_email=email, otp=otp, to_name=data.name)
    if not success:
        # Invalidate pending OTP if dispatch failed so user is not stuck with an unreceived code
        delete_otp(email)
        logger.error(f"Failed to dispatch OTP email to {email}: {email_msg}")
        raise HTTPException(
            status_code=502,
            detail="Failed to dispatch verification email via EmailJS provider. Please try again later."
        )

    # 5. Return success without exposing OTP
    return {
        "status": "success",
        "message": "OTP sent to your email.",
        "cooldown": 60
    }

@app.post("/auth/verify-otp")
def verify_otp_endpoint(data: VerifyOTPRequest):
    """
    Verifies 6-digit OTP against stored cryptographic hash,
    invalidates OTP immediately upon success, and authenticates the user.
    """
    email = data.email.strip().lower()
    otp = data.otp.strip()

    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if not otp or len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="Please enter a valid 6-digit numeric OTP.")

    success, message = verify_otp(email, otp)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    user = create_or_get_user(email, data.name)
    return {
        "status": "success",
        "message": "Authentication successful.",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
    }

@app.post("/auth/signup")
def signup_endpoint(data: SignupRequest):
    """Verifies OTP and registers a new user in the SQLite database."""
    email = data.email.strip().lower()
    name = data.name.strip()
    password = data.password
    otp = data.otp.strip()

    if not email or not name or not password or not otp:
        raise HTTPException(status_code=400, detail="All fields are required.")

    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="Please enter a valid 6-digit numeric OTP.")

    success, message = verify_otp(email, otp)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    created = create_user(email, password, name)
    if not created:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    user = get_user_by_email(email)
    return {
        "status": "success",
        "message": "User registered successfully.",
        "user": {"id": user["id"] if user else 0, "email": email, "name": name}
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
@app.get("/api/health")
def health():
    """Liveness probe: verifies application is running and model artifacts are loaded."""
    model_loaded = bool(_model_cache)
    return {
        "status": "healthy",
        "service": "weather-final",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "model_loaded": model_loaded,
        "model": _model_cache.get("name", "none")
    }

@app.get("/ready")
@app.get("/api/ready")
def readiness():
    """Readiness probe: verifies all model artifacts and station catalog integrity."""
    from ml_model.model_integrity import verify_artifact_integrity
    report = verify_artifact_integrity()
    is_ready = report["status"] == "valid"
    if not is_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "weather-final",
                "errors": report["errors"],
                "total_artifacts": report["total_artifacts"],
                "verified_artifacts": report["verified_artifacts"]
            }
        )
    return {
        "status": "ready",
        "service": "weather-final",
        "artifacts_verified": True,
        "total_artifacts": report["total_artifacts"],
        "verified_artifacts": report["verified_artifacts"]
    }


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

# ─── Phase 4: Production Commuter Decision & Stations API ───────────────────
_commute_engine = None
_station_catalog_cache = None

def get_commute_engine() -> Any:
    global _commute_engine
    if _commute_engine is None:
        try:
            from ml_model.exposure_engine import CommuteExposureEngine
            _commute_engine = CommuteExposureEngine()
            logger.info("Initialized CommuteExposureEngine.")
        except Exception as e:
            logger.error(f"Failed to initialize CommuteExposureEngine: {e}")
            raise HTTPException(status_code=503, detail=f"Forecasting & exposure engine unavailable: {e}")
    return _commute_engine

class GeoCoordinate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class DepartureWindowInput(BaseModel):
    start: str = Field(..., description="ISO 8601 start timestamp, e.g. 2026-09-25T08:00:00+05:30")
    end: str = Field(..., description="ISO 8601 end timestamp, e.g. 2026-09-25T10:00:00+05:30")
    interval_minutes: int = Field(15, ge=1, le=120)

class CommuteOptimizeRequest(BaseModel):
    origin: GeoCoordinate
    destination: GeoCoordinate
    mode: str = Field("cycling", description="Transit mode: walking, cycling, motorized")
    departure_window: DepartureWindowInput

def _handle_commute_optimize(payload: CommuteOptimizeRequest):
    """Shared execution logic for commute optimization."""
    engine = get_commute_engine()

    # Parse timestamps
    try:
        t_start = datetime.fromisoformat(payload.departure_window.start)
        t_end = datetime.fromisoformat(payload.departure_window.end)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ISO 8601 timestamp in departure_window: {e}"
        )

    # Ensure timezone awareness (default to IST if naive)
    if t_start.tzinfo is None:
        from datetime import timezone, timedelta
        t_start = t_start.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if t_end.tzinfo is None:
        from datetime import timezone, timedelta
        t_end = t_end.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))

    try:
        result = engine.optimize_commute(
            origin_lat=payload.origin.latitude,
            origin_lon=payload.origin.longitude,
            dest_lat=payload.destination.latitude,
            dest_lon=payload.destination.longitude,
            mode=payload.mode,
            departure_window_start=t_start,
            departure_window_end=t_end,
            interval_minutes=payload.departure_window.interval_minutes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Commute optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"Commute optimization engine failure: {str(e)}")

@app.post("/commute/optimize")
def commute_optimize_endpoint(payload: CommuteOptimizeRequest):
    """Production endpoint for commuter corridor PM2.5 exposure minimization."""
    return _handle_commute_optimize(payload)

@app.post("/api/commute/optimize")
def api_commute_optimize_endpoint(payload: CommuteOptimizeRequest):
    """Aliased production endpoint matching /api route convention."""
    return _handle_commute_optimize(payload)

def _get_delhi_stations():
    """Retrieve Delhi/NCR monitoring stations metadata from authoritative catalog."""
    global _station_catalog_cache
    if _station_catalog_cache is None:
        catalog_path = os.path.join(os.path.dirname(__file__), "datasets", "xkdr", "station_catalog.csv")
        if not os.path.exists(catalog_path):
            raise HTTPException(status_code=503, detail="Station catalog unavailable.")
        import pandas as pd
        df = pd.read_csv(catalog_path)
        stations = []
        for _, row in df.iterrows():
            pollutants = str(row.get("available_pollutants", "")).split(";") if pd.notna(row.get("available_pollutants")) else []
            stations.append({
                "station_id": str(row["station_id"]),
                "station_name": str(row["station_name"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "city": str(row.get("city", "Delhi")),
                "source": str(row.get("source", "cpcb_caaqm")),
                "available_pollutants": pollutants
            })
        _station_catalog_cache = stations
    return {
        "status": "success",
        "total_stations": len(_station_catalog_cache),
        "stations": _station_catalog_cache
    }

@app.get("/stations/delhi")
def stations_delhi_endpoint():
    """Returns official Delhi/NCR monitoring stations catalog."""
    return _get_delhi_stations()

@app.get("/api/stations/delhi")
def api_stations_delhi_endpoint():
    """Aliased official Delhi/NCR monitoring stations catalog."""
    return _get_delhi_stations()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
