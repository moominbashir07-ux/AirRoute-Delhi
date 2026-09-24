"""
AQI Predictor - Real-World Dataset Ingestion Pipeline
Fetches continuous hourly atmospheric and meteorological data from Open-Meteo
(Copernicus Atmosphere Monitoring Service CAMS & ECMWF ERA5 reanalysis).
Coverage: New Delhi (lat=28.6139, lon=77.2090), 2023-01-01 to 2024-12-31 (17,544 continuous hours).
License: Creative Commons Attribution 4.0 International (CC BY 4.0).
"""

import os
import json
import logging
from datetime import datetime
import httpx
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets"))
DATASET_CSV = os.path.join(DATASET_DIR, "real_aqi_dataset.csv")
METADATA_JSON = os.path.join(DATASET_DIR, "dataset_metadata.json")

# Ground coordinates: New Delhi NCR, India (reference ground station grid)
LATITUDE = 28.6139
LONGITUDE = 77.2090
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"


def fetch_real_dataset() -> pd.DataFrame:
    """Fetch real-world hourly atmospheric chemistry and weather observations."""
    os.makedirs(DATASET_DIR, exist_ok=True)

    aq_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&start_date={START_DATE}&end_date={END_DATE}"
        f"&hourly=pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,us_aqi"
    )
    wx_url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&start_date={START_DATE}&end_date={END_DATE}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )

    logger.info("Ingesting real atmospheric chemistry from Copernicus CAMS archive...")
    with httpx.Client(timeout=60.0) as client:
        aq_res = client.get(aq_url)
        aq_res.raise_for_status()
        aq_data = aq_res.json()["hourly"]

        logger.info("Ingesting meteorological telemetry from ECMWF ERA5 reanalysis archive...")
        wx_res = client.get(wx_url)
        wx_res.raise_for_status()
        wx_data = wx_res.json()["hourly"]

    df_aq = pd.DataFrame(aq_data)
    df_wx = pd.DataFrame(wx_data)

    df = pd.merge(df_aq, df_wx, on="time")
    logger.info(f"Ingested {len(df)} total hourly records.")

    # Canonical feature mapping
    df = df.rename(
        columns={
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "wind_speed_10m": "wind_speed",
            "carbon_monoxide": "co2",
            "pm2_5": "pm25",
            "nitrogen_dioxide": "no2",
            "sulphur_dioxide": "so2",
            "us_aqi": "aqi",
        }
    )

    # Sort strictly chronologically
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    return df


def validate_and_clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Validate data integrity, verify physical limits, and clean anomalies."""
    initial_rows = len(df)

    # 1. Deduplicate by timestamp
    df = df.drop_duplicates(subset=["time"])

    # 2. Check nulls
    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        logger.warning(f"Null values detected:\n{null_counts[null_counts > 0]}")
        # Drop rows where target is null
        df = df.dropna(subset=["aqi"])
        # Forward fill and median fill remaining sensor gaps
        df = df.ffill().bfill()

    # 3. Physical range sanity checks
    # Temperature (-20 to 60 C), Humidity (0 to 100 %), Wind (>= 0), Particulates (>= 0)
    df = df[
        (df["temperature"].between(-20, 60))
        & (df["humidity"].between(0, 100))
        & (df["wind_speed"] >= 0)
        & (df["pm25"] >= 0)
        & (df["pm10"] >= 0)
        & (df["aqi"] >= 0)
    ].reset_index(drop=True)

    # PM10 is physical parent fraction of PM2.5 (PM10 >= PM2.5)
    # Correct any minor sensor fraction inversion
    df["pm10"] = df[["pm10", "pm25"]].max(axis=1)

    logger.info(f"Dataset validated & cleaned: {initial_rows} -> {len(df)} valid observations.")
    return df


def save_dataset_and_metadata(df: pd.DataFrame):
    """Save clean CSV and provenance metadata."""
    df.to_csv(DATASET_CSV, index=False)
    logger.info(f"Saved real-world dataset to {DATASET_CSV}")

    metadata = {
        "dataset_name": "Open-Meteo Atmospheric & Meteorological Archive (Copernicus CAMS & ECMWF ERA5)",
        "source": "Open-Meteo Open Data API",
        "reference_url": "https://open-meteo.com/en/docs/air-quality-api",
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "geographic_coverage": {
            "region": "New Delhi NCR, India",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
        "time_period": {
            "start": str(df["time"].min()),
            "end": str(df["time"].max()),
        },
        "sample_count": len(df),
        "sampling_frequency": "1 hour",
        "features": {
            "temperature": {"unit": "°C", "description": "Ambient dry bulb temperature at 2m"},
            "humidity": {"unit": "%", "description": "Relative humidity at 2m"},
            "wind_speed": {"unit": "km/h", "description": "Wind speed at 10m height"},
            "co2": {"unit": "µg/m³", "description": "Ambient Carbon Monoxide concentration"},
            "pm25": {"unit": "µg/m³", "description": "Particulate matter with diameter <= 2.5 µm"},
            "pm10": {"unit": "µg/m³", "description": "Particulate matter with diameter <= 10 µm"},
            "no2": {"unit": "µg/m³", "description": "Nitrogen dioxide concentration"},
            "so2": {"unit": "µg/m³", "description": "Sulfur dioxide concentration"},
        },
        "target": {
            "name": "aqi",
            "standard": "US EPA Air Quality Index (0-500 scale)",
            "description": "Continuous EPA AQI computed across pollutant criteria",
        },
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
    }

    with open(METADATA_JSON, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved provenance metadata to {METADATA_JSON}")


def run_ingestion() -> pd.DataFrame:
    """Execute complete ingestion pipeline."""
    df = fetch_real_dataset()
    df = validate_and_clean_dataset(df)
    save_dataset_and_metadata(df)
    return df


if __name__ == "__main__":
    run_ingestion()
