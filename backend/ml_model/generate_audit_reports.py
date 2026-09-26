"""
Generates Audit 2 (Temporal Resolution) and Audit 3 (Missingness Denominator) Reports.
Analyzes exact sampling resolution, delta intervals, and separates Active-Period coverage
from Global-Window coverage across all 42 Delhi stations and 6 criteria pollutants.
"""

import os
import json
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("audit_generator")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
XKDR_DATA_DIR = os.path.join(BACKEND_DIR, "datasets", "xkdr")

PARQUET_DATASET_PATH = os.path.join(XKDR_DATA_DIR, "station_observations_2020_2024.parquet")
STATION_CATALOG_PATH = os.path.join(XKDR_DATA_DIR, "station_catalog.csv")
TEMPORAL_REPORT_PATH = os.path.join(XKDR_DATA_DIR, "temporal_resolution_report.json")
MISSINGNESS_AUDIT_PATH = os.path.join(XKDR_DATA_DIR, "missingness_audit.json")

GLOBAL_START_IST = "2020-01-01 00:00:00+05:30"
GLOBAL_END_IST = "2024-12-31 23:00:00+05:30"
GLOBAL_EXPECTED_HOURS = 43848  # 1827 days * 24 hours (2020 leap year has 366 days)
POLLUTANTS = ["pm25", "pm10", "no2", "so2", "co", "o3"]


def generate_reports():
    logger.info("Loading Parquet observational dataset...")
    df = pd.read_parquet(PARQUET_DATASET_PATH)
    df_catalog = pd.read_csv(STATION_CATALOG_PATH)
    logger.info(f"Loaded {len(df):,} rows across {df['station_id'].nunique()} stations.")

    # ─────────────────────────────────────────────────────────────────────────────
    # AUDIT 1 & 2: TEMPORAL RESOLUTION REPORT
    # ─────────────────────────────────────────────────────────────────────────────
    logger.info("Analyzing temporal resolution and delta distributions...")
    
    interval_counts = {}
    station_temporal = {}
    
    for station_id, group in df.groupby("station_id"):
        s_sorted = group.sort_values("timestamp_utc")
        diffs = s_sorted["timestamp_utc"].diff().dropna()
        diff_minutes = (diffs.dt.total_seconds() / 60.0).astype(int)
        
        counts = diff_minutes.value_counts().to_dict()
        for delta, cnt in counts.items():
            interval_counts[delta] = interval_counts.get(delta, 0) + cnt
            
        exact_60 = int((diff_minutes == 60).sum())
        exact_30 = int((diff_minutes == 30).sum())
        other_intervals = int(((diff_minutes != 60) & (diff_minutes != 30)).sum())
        
        station_temporal[station_id] = {
            "station_name": s_sorted["station_name"].iloc[0],
            "total_records": len(s_sorted),
            "ist_minute_offset": int(s_sorted["timestamp_ist"].dt.minute.mode().iloc[0]),
            "utc_minute_offset": int(s_sorted["timestamp_utc"].dt.minute.mode().iloc[0]),
            "min_delta_minutes": int(diff_minutes.min()) if len(diff_minutes) > 0 else 0,
            "median_delta_minutes": float(diff_minutes.median()) if len(diff_minutes) > 0 else 0.0,
            "mode_delta_minutes": int(diff_minutes.mode().iloc[0]) if len(diff_minutes) > 0 else 0,
            "count_60min_deltas": exact_60,
            "count_30min_deltas": exact_30,
            "count_gap_deltas": other_intervals,
        }

    # Aggregate interval distribution sorted
    sorted_intervals = {f"{k} min ({k/60:.1f}h)": v for k, v in sorted(interval_counts.items(), key=lambda x: x[1], reverse=True)[:15]}

    temporal_report = {
        "source_resolution": "60 minutes (Hourly). CPCB CAAQM monitors report at :00 minutes past the hour in IST; US Embassy monitor reports at :30 minutes past the hour in IST.",
        "canonical_resolution": "60 minutes (Hourly). Exactly one row represents one station-observation timestamp.",
        "aggregation_rule_applied": "NONE (The source API returns native hourly observations. No sub-hourly averaging or downsampling was performed).",
        "total_deltas_analyzed": sum(interval_counts.values()),
        "count_exactly_60min": interval_counts.get(60, 0),
        "count_exactly_30min": interval_counts.get(30, 0),
        "count_sub_hourly_intervals": sum(v for k, v in interval_counts.items() if k < 60),
        "top_intervals": sorted_intervals,
        "station_temporal_statistics": station_temporal,
    }

    with open(TEMPORAL_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(temporal_report, f, indent=2)
    logger.info(f"Saved temporal resolution report to {TEMPORAL_REPORT_PATH}")

    # ─────────────────────────────────────────────────────────────────────────────
    # AUDIT 3: MISSINGNESS DENOMINATOR REPORT
    # ─────────────────────────────────────────────────────────────────────────────
    logger.info("Computing dual-denominator missingness metrics (Active vs Global)...")

    missingness_records = []
    
    for station_id, group in df.groupby("station_id"):
        st_meta = df_catalog[df_catalog["station_id"] == station_id].iloc[0] if station_id in df_catalog["station_id"].values else {}
        st_name = st_meta.get("station_name", group["station_name"].iloc[0])
        st_agency = "US Embassy" if "Embassy" in st_name else ("DPCC" if "DPCC" in st_name else ("CPCB" if "CPCB" in st_name else ("IMD" if "IMD" in st_name else "Other")))

        s_min_utc = group["timestamp_utc"].min()
        s_max_utc = group["timestamp_utc"].max()
        s_min_ist = group["timestamp_ist"].min()
        s_max_ist = group["timestamp_ist"].max()

        active_span_hours = int((s_max_utc - s_min_utc).total_seconds() / 3600) + 1
        observed_station_hours = len(group)

        # Denominator 1: Active-Period Coverage
        active_missing_hours = active_span_hours - observed_station_hours
        active_coverage_pct = round(observed_station_hours / active_span_hours * 100, 2)
        active_missing_pct = round(100.0 - active_coverage_pct, 2)

        # Denominator 2: Global-Window Coverage (43,848 hours)
        global_missing_hours = GLOBAL_EXPECTED_HOURS - observed_station_hours
        global_coverage_pct = round(observed_station_hours / GLOBAL_EXPECTED_HOURS * 100, 2)
        global_missing_pct = round(100.0 - global_coverage_pct, 2)

        st_dict = {
            "station_id": station_id,
            "station_name": st_name,
            "agency": st_agency,
            "station_active_start_ist": str(s_min_ist),
            "station_active_end_ist": str(s_max_ist),
            "active_span_hours": active_span_hours,
            "global_window_hours": GLOBAL_EXPECTED_HOURS,
            "observed_station_hours": observed_station_hours,
            "active_period": {
                "coverage_pct": active_coverage_pct,
                "missing_pct": active_missing_pct,
                "missing_hours": active_missing_hours,
            },
            "global_window": {
                "coverage_pct": global_coverage_pct,
                "missing_pct": global_missing_pct,
                "missing_hours": global_missing_hours,
            },
            "pollutant_metrics": {},
        }

        for p in POLLUTANTS:
            obs_p = int(group[p].notnull().sum())
            active_p_cov = round(obs_p / active_span_hours * 100, 2)
            global_p_cov = round(obs_p / GLOBAL_EXPECTED_HOURS * 100, 2)
            st_dict["pollutant_metrics"][p] = {
                "observed_count": obs_p,
                "active_period_coverage_pct": active_p_cov,
                "active_period_missing_pct": round(100.0 - active_p_cov, 2),
                "global_window_coverage_pct": global_p_cov,
                "global_window_missing_pct": round(100.0 - global_p_cov, 2),
            }

        missingness_records.append(st_dict)

    # Sort stations by global coverage
    missingness_records = sorted(missingness_records, key=lambda x: x["global_window"]["coverage_pct"], reverse=True)

    # Global Summary
    total_active_potential_hours = sum(r["active_span_hours"] for r in missingness_records)
    total_global_potential_hours = GLOBAL_EXPECTED_HOURS * len(missingness_records)
    total_observed_hours = len(df)

    global_pollutant_summary = {}
    for p in POLLUTANTS:
        obs_total = int(df[p].notnull().sum())
        active_cov = round(obs_total / total_active_potential_hours * 100, 2)
        global_cov = round(obs_total / total_global_potential_hours * 100, 2)
        global_pollutant_summary[p] = {
            "observed_total": obs_total,
            "active_period_coverage_pct": active_cov,
            "active_period_missing_pct": round(100.0 - active_cov, 2),
            "global_window_coverage_pct": global_cov,
            "global_window_missing_pct": round(100.0 - global_cov, 2),
        }

    missingness_audit = {
        "audit_description": "Dual-denominator missingness audit separating active operational span from the 5-year global window.",
        "global_window": {
            "start_ist": GLOBAL_START_IST,
            "end_ist": GLOBAL_END_IST,
            "total_hours": GLOBAL_EXPECTED_HOURS,
            "total_stations": len(missingness_records),
        },
        "aggregate_coverage": {
            "total_observed_station_hours": total_observed_hours,
            "active_period_coverage_pct": round(total_observed_hours / total_active_potential_hours * 100, 2),
            "global_window_coverage_pct": round(total_observed_hours / total_global_potential_hours * 100, 2),
        },
        "pollutant_aggregate_coverage": global_pollutant_summary,
        "station_coverage_audit": missingness_records,
    }

    with open(MISSINGNESS_AUDIT_PATH, "w", encoding="utf-8") as f:
        json.dump(missingness_audit, f, indent=2)
    logger.info(f"Saved missingness audit report to {MISSINGNESS_AUDIT_PATH}")


if __name__ == "__main__":
    generate_reports()
