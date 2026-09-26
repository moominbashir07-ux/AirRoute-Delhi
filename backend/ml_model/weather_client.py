"""Phase 3D: Meteorological Data Client for Open-Meteo.

Distinguishes explicitly between:
1. Historical / archived reanalysis mode (ECMWF ERA5 via archive-api.open-meteo.com)
2. Production NWP forecast mode (via api.open-meteo.com/v1/forecast)

Transforms wind direction degrees into circular vector components (sin and cos).
"""

import os
import math
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import httpx
import pandas as pd
import numpy as np

logger = logging.getLogger("WeatherClient")

DEFAULT_LATITUDE = 28.6139
DEFAULT_LONGITUDE = 77.2090

BASE_DIR = Path(__file__).resolve().parent.parent
PHASE3D_DATA_DIR = BASE_DIR / "datasets" / "phase3d"


def transform_wind_direction(degrees_series: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Transform circular wind direction degrees [0, 360) into continuous sin and cos components.
    
    Wind direction is circular: 0° (North) is identical to 360°.
    sin(0) = 0, cos(0) = 1.
    """
    rad = np.radians(degrees_series.astype(float))
    sin_comp = np.sin(rad)
    cos_comp = np.cos(rad)
    return sin_comp, cos_comp


class NWPServiceError(Exception):
    """Raised when external NWP weather service is unavailable, times out, or returns invalid data."""
    pass


class WeatherClient:
    """Client for fetching and caching Open-Meteo meteorological telemetry."""

    def __init__(self, cache_dir: Optional[Path] = None, timeout_seconds: Optional[float] = None):
        self.cache_dir = cache_dir or PHASE3D_DATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.historical_cache_file = self.cache_dir / "historical_weather_2020_2024.parquet"
        self.timeout_seconds = timeout_seconds or float(os.getenv("NWP_TIMEOUT_SECONDS", "10.0"))

    def fetch_historical_archive(
        self,
        start_date: str = "2020-01-01",
        end_date: str = "2024-12-31",
        latitude: float = DEFAULT_LATITUDE,
        longitude: float = DEFAULT_LONGITUDE,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """Fetch historical meteorological reanalysis data from Open-Meteo ERA5 archive.
        
        Uses local cache if available unless force_refresh is True.
        """
        if self.historical_cache_file.exists() and not force_refresh:
            logger.info(f"Loading cached historical weather from {self.historical_cache_file}...")
            return pd.read_parquet(self.historical_cache_file)

        logger.info(f"Querying Open-Meteo ERA5 Archive for {start_date} to {end_date}...")
        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={latitude}&longitude={longitude}"
            f"&start_date={start_date}&end_date={end_date}"
            f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,boundary_layer_height"
        )

        with httpx.Client(timeout=90.0) as client:
            res = client.get(url)
            res.raise_for_status()
            data = res.json()["hourly"]

        df = pd.DataFrame(data)
        # Parse timestamp to UTC
        df["timestamp_utc"] = pd.to_datetime(df["time"], utc=True)
        df = df.drop(columns=["time"])

        # Rename to canonical names
        df = df.rename(columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "wind_speed_10m": "wind_speed",
            "boundary_layer_height": "boundary_layer_height",
            "surface_pressure": "surface_pressure"
        })

        # Circular wind transformation
        sin_w, cos_w = transform_wind_direction(df["wind_direction_10m"])
        df["wind_direction_sin"] = sin_w
        df["wind_direction_cos"] = cos_w

        # Drop raw wind direction degrees to avoid non-circular collinearity
        df = df.drop(columns=["wind_direction_10m"])

        # Sort and deduplicate
        df = df.sort_values("timestamp_utc").drop_duplicates(subset=["timestamp_utc"]).reset_index(drop=True)

        logger.info(f"Saving {len(df)} historical weather records to {self.historical_cache_file}...")
        df.to_parquet(self.historical_cache_file, index=False, engine="pyarrow", compression="snappy")
        return df

    def fetch_production_forecast(
        self,
        latitude: float = DEFAULT_LATITUDE,
        longitude: float = DEFAULT_LONGITUDE,
        forecast_hours: int = 12,
        max_retries: int = 2
    ) -> pd.DataFrame:
        """Fetch real-time NWP weather forecast from Open-Meteo Forecast API with retries and timeout.
        
        This mode represents production inference weather available at prediction time.
        Raises NWPServiceError if the external service fails or times out.
        """
        logger.info(f"Querying Open-Meteo NWP Forecast API for ({latitude}, {longitude})...")
        base_url = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1").rstrip("/")
        url = (
            f"{base_url}/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,boundary_layer_height"
            f"&forecast_days=2"
        )

        last_error = None
        import time
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    res = client.get(url)
                    res.raise_for_status()
                    data = res.json()["hourly"]

                df = pd.DataFrame(data)
                df["timestamp_utc"] = pd.to_datetime(df["time"], utc=True)
                df = df.drop(columns=["time"])

                df = df.rename(columns={
                    "temperature_2m": "temperature",
                    "relative_humidity_2m": "humidity",
                    "wind_speed_10m": "wind_speed",
                    "boundary_layer_height": "boundary_layer_height",
                    "surface_pressure": "surface_pressure"
                })

                sin_w, cos_w = transform_wind_direction(df["wind_direction_10m"])
                df["wind_direction_sin"] = sin_w
                df["wind_direction_cos"] = cos_w
                df = df.drop(columns=["wind_direction_10m"])

                df = df.sort_values("timestamp_utc").reset_index(drop=True)
                return df.iloc[:forecast_hours]
            except Exception as e:
                last_error = e
                logger.warning(f"NWP fetch attempt {attempt + 1}/{max_retries + 1} failed: {e}")
                if attempt < max_retries:
                    time.sleep(0.3 * (attempt + 1))

        raise NWPServiceError(f"Open-Meteo NWP service failed after {max_retries + 1} attempts: {last_error}")

