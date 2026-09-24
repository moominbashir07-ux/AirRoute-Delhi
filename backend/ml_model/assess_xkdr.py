"""
XKDR India Air Quality Database Assessment Script
Evaluates data availability, stations, pollutants, quality, and feasibility
for Delhi/NCR air quality modeling without exposing API keys.
"""

import os
import json
import logging
from datetime import datetime
import pandas as pd
import requests
from dotenv import dotenv_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("xkdr_assessment")

BASE_URL = "https://airquality.xkdr.org"


def get_api_key() -> str:
    """Retrieve API key safely from environment or .env without logging it."""
    # Check project root and backend .env
    root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    vals = {}
    if os.path.exists(root_env):
        vals.update(dotenv_values(root_env))
    if os.path.exists(backend_env):
        vals.update(dotenv_values(backend_env))
    vals.update(os.environ)

    key = vals.get("XKDR_API_KEY") or vals.get("OPENAQ_API_KEY") or ""
    if not key:
        raise ValueError("No XKDR/OpenAQ API key detected in environment or .env files.")
    return key


def get_headers() -> dict:
    key = get_api_key()
    return {"Authorization": f"Bearer {key}"}


def step1_verify_auth() -> dict:
    logger.info("STEP 1: Verifying authentication...")
    headers = get_headers()
    url = f"{BASE_URL}/v1/meta"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Authentication failed: HTTP {resp.status_code}")
    data = resp.json()
    auth_summary = {
        "status": "PASS",
        "tier": data.get("your_tier"),
        "max_rows": data.get("max_rows_per_query"),
        "timezone_note": data.get("timezone_note"),
        "total_rows": data.get("measurements", {}).get("rows"),
        "first_month": data.get("measurements", {}).get("first_month"),
        "last_month": data.get("measurements", {}).get("last_month"),
    }
    logger.info(f"Auth verified successfully: Tier={auth_summary['tier']}")
    return auth_summary


def step2_parameters() -> list:
    logger.info("STEP 2: Inspecting parameters...")
    headers = get_headers()
    resp = requests.get(f"{BASE_URL}/v1/parameters", headers=headers, timeout=15)
    resp.raise_for_status()
    params = resp.json().get("data", [])
    logger.info(f"Found {len(params)} parameters in XKDR catalog.")
    return params


def step3_delhi_stations() -> pd.DataFrame:
    logger.info("STEP 3: Discovering Delhi monitoring stations...")
    headers = get_headers()
    # Query city=Delhi
    resp = requests.get(f"{BASE_URL}/v1/stations?city=Delhi", headers=headers, timeout=20)
    resp.raise_for_status()
    stations_delhi = resp.json().get("data", [])

    # Also query state=Delhi to be comprehensive
    resp_state = requests.get(f"{BASE_URL}/v1/stations?state=Delhi", headers=headers, timeout=20)
    stations_state = resp_state.json().get("data", []) if resp_state.status_code == 200 else []

    # Merge unique
    all_stations = {s["station_id"]: s for s in stations_delhi + stations_state}
    df = pd.DataFrame(list(all_stations.values()))
    logger.info(f"Found {len(df)} monitoring stations for Delhi.")
    return df


def step4_pollutant_availability(stations_df: pd.DataFrame, params: list) -> dict:
    logger.info("STEP 4: Determining pollutant & weather variable availability...")
    all_station_params = set()
    for p_list in stations_df["parameters"]:
        if isinstance(p_list, list):
            all_station_params.update(p_list)

    catalog_names = {p["parameter_name"]: p for p in params}

    target_pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "Ozone"]
    weather_vars = ["Temperature", "Relative Humidity", "Wind Speed", "Wind Direction", "Pressure", "Rainfall"]

    availability = {}
    for p in target_pollutants:
        in_catalog = p in catalog_names
        in_delhi = p in all_station_params
        # count stations with this param
        count = sum(1 for p_list in stations_df["parameters"] if isinstance(p_list, list) and p in p_list)
        availability[p] = {
            "type": "pollutant",
            "in_catalog": in_catalog,
            "in_delhi_stations": in_delhi,
            "delhi_stations_count": count,
            "delhi_station_coverage_pct": round(count / len(stations_df) * 100, 1),
            "unit": catalog_names.get(p, {}).get("unit"),
        }

    for w in weather_vars:
        # Check case-insensitive match
        match = next((k for k in catalog_names if k.lower() == w.lower()), None)
        in_delhi = next((k for k in all_station_params if k.lower() == w.lower()), None)
        count = 0
        if in_delhi:
            count = sum(1 for p_list in stations_df["parameters"] if isinstance(p_list, list) and in_delhi in p_list)
        availability[w] = {
            "type": "weather",
            "in_catalog": match is not None,
            "in_delhi_stations": in_delhi is not None,
            "delhi_stations_count": count,
            "delhi_station_coverage_pct": round(count / len(stations_df) * 100, 1) if in_delhi else 0.0,
            "unit": catalog_names.get(match, {}).get("unit") if match else None,
        }

    return availability


def step5_historical_coverage() -> dict:
    logger.info("STEP 5: Testing annual coverage (2020 - 2025)...")
    headers = get_headers()
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    results = {}

    for yr in years:
        # Representative 1-week test in November (peak pollution period in Delhi)
        start_date = f"{yr}-11-01"
        end_date = f"{yr}-11-07"
        url = f"{BASE_URL}/v1/measurements?city=Delhi&parameter=PM2.5&start={start_date}&end={end_date}&agg=daily"
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                data = r.json()
                rows = data.get("data", [])
                stations = set(row.get("station_id") for row in rows)
                results[yr] = {
                    "status": "available",
                    "sample_week": f"{start_date} to {end_date}",
                    "row_count": len(rows),
                    "active_delhi_stations": len(stations),
                    "mean_pm25": round(pd.DataFrame(rows)["mean"].mean(), 1) if rows and "mean" in rows[0] else None,
                }
            else:
                results[yr] = {"status": f"HTTP {r.status_code}", "active_delhi_stations": 0}
        except Exception as e:
            results[yr] = {"status": f"Error: {type(e).__name__}", "active_delhi_stations": 0}

    return results


def step6_data_quality_deep_dive() -> dict:
    logger.info("STEP 6: Measuring data quality on representative Delhi multi-station sample...")
    headers = get_headers()
    # Pull 1 month of raw hourly data for a major continuous station in Delhi: e.g. site_5024 (Alipur, Delhi)
    # or Anand Vihar / IHBAS across PM2.5, PM10, NO2, SO2, CO, Ozone
    params = ["PM2.5", "PM10", "NO2", "SO2", "CO", "Ozone"]
    param_query = "&".join(f"parameter={p}" for p in params)
    url = f"{BASE_URL}/v1/measurements?city=Delhi&{param_query}&start=2024-11-01&end=2024-11-07&format=json"

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    raw_data = resp.json().get("data", [])
    df = pd.DataFrame(raw_data)

    if df.empty:
        return {"error": "No raw data returned for sample period"}

    # Quality metrics
    total_records = len(df)
    unique_stations = df["station_id"].nunique()
    timestamp_range = [df["collected_at"].min(), df["collected_at"].max()]
    
    # Negative/impossible values
    neg_counts = {}
    null_counts = {}
    for p in params:
        sub = df[df["parameter_name"] == p]
        neg_counts[p] = int((sub["value"] < 0).sum())
        null_counts[p] = int(sub["value"].isnull().sum())

    # Duplicate check: (station_id, parameter_name, collected_at)
    duplicates = int(df.duplicated(subset=["station_id", "parameter_name", "collected_at"]).sum())

    return {
        "sample_period": "2024-11-01 to 2024-11-07 (Delhi, all stations, 6 criteria pollutants)",
        "total_records": total_records,
        "unique_stations": unique_stations,
        "timestamp_range": timestamp_range,
        "duplicates": duplicates,
        "negative_values_by_pollutant": neg_counts,
        "null_values_by_pollutant": null_counts,
        "parameters_returned": df["parameter_name"].value_counts().to_dict(),
    }


def run_full_assessment():
    logger.info("Starting comprehensive XKDR India Air Quality assessment...")
    auth_summary = step1_verify_auth()
    params = step2_parameters()
    delhi_stations = step3_delhi_stations()
    pollutant_avail = step4_pollutant_availability(delhi_stations, params)
    historical_cov = step5_historical_coverage()
    quality_summary = step6_data_quality_deep_dive()

    report_data = {
        "assessment_timestamp": datetime.utcnow().isoformat() + "Z",
        "auth_summary": auth_summary,
        "delhi_stations_total": len(delhi_stations),
        "parameters_catalog": params,
        "pollutant_availability": pollutant_avail,
        "historical_coverage": historical_cov,
        "data_quality_sample": quality_summary,
        "delhi_station_sample": delhi_stations[["station_id", "station_name", "latitude", "longitude", "source"]].head(15).to_dict(orient="records"),
    }

    output_path = os.path.join(os.path.dirname(__file__), "xkdr_assessment_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    logger.info(f"Assessment complete. Raw summary saved to {output_path}")
    return report_data


if __name__ == "__main__":
    run_full_assessment()
