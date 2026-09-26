"""
Independent Validation Script for Phase 3B Observational Cache
Reloads the finalized station_observations_2020_2024.parquet from disk and independently
audits row counts, station counts, date ranges, duplicates, negatives, missingness,
and timestamp/unit consistency against the metadata report.
"""

import os
import json
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("independent_validator")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
XKDR_DATA_DIR = os.path.join(BACKEND_DIR, "datasets", "xkdr")

PARQUET_DATASET_PATH = os.path.join(XKDR_DATA_DIR, "station_observations_2020_2024.parquet")
STATION_CATALOG_PATH = os.path.join(XKDR_DATA_DIR, "station_catalog.csv")
QUALITY_REPORT_PATH = os.path.join(XKDR_DATA_DIR, "quality_report.json")
DATASET_METADATA_PATH = os.path.join(XKDR_DATA_DIR, "dataset_metadata.json")


def validate_observational_dataset():
    logger.info("=== Commencing Independent Validation Pass ===")
    
    assert os.path.exists(PARQUET_DATASET_PATH), f"Missing parquet dataset: {PARQUET_DATASET_PATH}"
    assert os.path.exists(QUALITY_REPORT_PATH), f"Missing quality report: {QUALITY_REPORT_PATH}"
    assert os.path.exists(STATION_CATALOG_PATH), f"Missing station catalog: {STATION_CATALOG_PATH}"

    # 1. Load Parquet from disk
    logger.info(f"Reloading {PARQUET_DATASET_PATH} from disk...")
    df = pd.read_parquet(PARQUET_DATASET_PATH)
    logger.info(f"Loaded {len(df):,} wide rows. Columns: {df.columns.tolist()}")

    # 2. Load Reports
    with open(QUALITY_REPORT_PATH, "r", encoding="utf-8") as f:
        quality_rep = json.load(f)

    df_catalog = pd.read_csv(STATION_CATALOG_PATH)

    # 3. Independent Row and Station Verification
    assert len(df) == quality_rep["total_wide_rows"], (
        f"Row count mismatch: df has {len(df)}, report claims {quality_rep['total_wide_rows']}"
    )
    assert df["station_id"].nunique() == quality_rep["station_count"], (
        f"Station count mismatch: df has {df['station_id'].nunique()}, report claims {quality_rep['station_count']}"
    )
    assert df["station_id"].nunique() == len(df_catalog), (
        f"Station count mismatch with catalog: {df['station_id'].nunique()} vs {len(df_catalog)}"
    )

    # 4. Independent Duplicate Check on Canonical Key
    logger.info("Checking for duplicate (station_id, timestamp_utc) keys...")
    dup_count = int(df.duplicated(subset=["station_id", "timestamp_utc"]).sum())
    assert dup_count == 0, f"Found {dup_count} duplicate station-hour records in wide dataset!"

    # 5. Independent Negative Values Check
    logger.info("Verifying absence of impossible negative values...")
    pollutants = ["pm25", "pm10", "no2", "so2", "co", "o3"]
    for p in pollutants:
        neg_count = int((df[p] < 0).sum())
        assert neg_count == 0, f"Found {neg_count} negative concentrations in pollutant {p}!"

    # 6. Independent Timestamp Consistency Check (UTC vs IST)
    logger.info("Verifying timestamp alignment: timestamp_utc + 5h30m == timestamp_ist...")
    # IST to UTC
    ist_series = pd.to_datetime(df["timestamp_ist"])
    utc_series = pd.to_datetime(df["timestamp_utc"])
    
    # Check timezone awareness
    assert ist_series.dt.tz is not None, "timestamp_ist is not timezone-aware!"
    assert utc_series.dt.tz is not None, "timestamp_utc is not timezone-aware!"
    
    # Check that diff is exactly 0
    diff = (ist_series.dt.tz_convert("UTC") - utc_series).abs()
    assert (diff == pd.Timedelta(0)).all(), "Found timestamp conversion discrepancy between IST and UTC!"

    # 7. Independent Unit Consistency Check
    logger.info("Verifying pollutant concentration distributions and unit scaling...")
    # CO was converted from mg/m3 to ug/m3 -> mean in Delhi must be realistic (e.g. 500 - 3000 ug/m3)
    co_valid = df["co"].dropna()
    assert co_valid.mean() > 100.0, f"CO mean appears too low ({co_valid.mean()} ug/m3), unit conversion failure!"
    assert co_valid.mean() < 5000.0, f"CO mean appears implausibly high ({co_valid.mean()} ug/m3)!"

    # PM2.5 mean in Delhi is typically 50 - 150 ug/m3
    pm25_valid = df["pm25"].dropna()
    assert 40.0 < pm25_valid.mean() < 200.0, f"PM2.5 mean ({pm25_valid.mean()}) outside plausible Delhi range!"

    # 8. Check Missingness Preserved (Zero Interpolation Rule)
    logger.info("Verifying that missing values remain null (no artificial interpolation)...")
    for p in pollutants:
        null_count = int(df[p].isnull().sum())
        reported_null = quality_rep["pollutant_summary"][p]["missing_count"]
        assert null_count == reported_null, (
            f"Null count mismatch for {p}: actual {null_count} vs reported {reported_null}"
        )
        assert null_count > 0, f"Suspicious: pollutant {p} has zero missing values across 5 years!"

    # 9. Verify Date Range
    min_date = df["timestamp_utc"].min()
    max_date = df["timestamp_utc"].max()
    logger.info(f"Verified Date Range: {min_date} to {max_date}")
    assert min_date <= pd.Timestamp("2020-01-01", tz="UTC")
    assert max_date >= pd.Timestamp("2024-12-31", tz="UTC")

    logger.info("=== INDEPENDENT VALIDATION PASS: 100% VERIFIED SUCCESSFUL ===")
    return {
        "status": "PASS",
        "total_wide_rows": len(df),
        "total_stations": df["station_id"].nunique(),
        "duplicates": dup_count,
        "date_range": [str(min_date), str(max_date)],
        "co_mean_ug_m3": round(float(co_valid.mean()), 2),
        "pm25_mean_ug_m3": round(float(pm25_valid.mean()), 2),
        "pm10_mean_ug_m3": round(float(df["pm10"].dropna().mean()), 2),
    }


if __name__ == "__main__":
    result = validate_observational_dataset()
    print("\nIndependent Validation Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")
