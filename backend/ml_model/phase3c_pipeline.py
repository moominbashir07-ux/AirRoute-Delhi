"""Phase 3C: Orchestration Pipeline for Corridor Geometry & Feature Engineering.

Generates:
1. backend/datasets/phase3c/corridor_segments.parquet
2. backend/datasets/phase3c/segment_station_mapping.parquet
3. backend/datasets/phase3c/station_temporal_features.parquet
4. backend/datasets/phase3c/feature_metadata.json
5. backend/datasets/phase3c/phase3c_metadata.json
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import numpy as np

from ml_model.corridor_geometry import (
    discretize_corridor,
    generate_corridor_id,
    StationSpatialIndex,
    EARTH_RADIUS_KM,
    DEFAULT_MAX_STATION_DISTANCE_KM
)
from ml_model.temporal_features import (
    build_full_temporal_feature_dataset,
    get_feature_metadata_catalog
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("Phase3C_Pipeline")

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
XKDR_DIR = DATASETS_DIR / "xkdr"
PHASE3C_DIR = DATASETS_DIR / "phase3c"

# Benchmark commuter corridors across Delhi NCR representing diverse transit radial axes
BENCHMARK_CORRIDORS = [
    {
        "name": "Connaught Place to Cyber City, Gurugram",
        "origin": {"latitude": 28.6315, "longitude": 77.2167},
        "destination": {"latitude": 28.4950, "longitude": 77.0895},
        "step_km": 1.0
    },
    {
        "name": "Noida Sector 62 to AIIMS / South Extension",
        "origin": {"latitude": 28.6271, "longitude": 77.3619},
        "destination": {"latitude": 28.5672, "longitude": 77.2100},
        "step_km": 1.0
    },
    {
        "name": "Anand Vihar ISBT to Dwarka Sector 21",
        "origin": {"latitude": 28.6469, "longitude": 77.3160},
        "destination": {"latitude": 28.5523, "longitude": 77.0583},
        "step_km": 1.0
    },
    {
        "name": "Rohini Sector 16 to Nehru Place",
        "origin": {"latitude": 28.7325, "longitude": 77.1189},
        "destination": {"latitude": 28.5492, "longitude": 77.2533},
        "step_km": 1.0
    },
    {
        "name": "IGI Airport (T3) to Chandni Chowk / Old Delhi",
        "origin": {"latitude": 28.5562, "longitude": 77.0999},
        "destination": {"latitude": 28.6506, "longitude": 77.2303},
        "step_km": 1.0
    },
    {
        "name": "Vasundhara Ghaziabad to ITO Delhi",
        "origin": {"latitude": 28.6608, "longitude": 77.3573},
        "destination": {"latitude": 28.6286, "longitude": 77.2411},
        "step_km": 1.0
    },
    {
        "name": "Faridabad Sector 15 to Connaught Place",
        "origin": {"latitude": 28.4089, "longitude": 77.3178},
        "destination": {"latitude": 28.6315, "longitude": 77.2167},
        "step_km": 1.0
    },
    # Edge Case: Ultra-short corridor (~350m within Connaught Place)
    {
        "name": "Connaught Place Inner Circle Walk",
        "origin": {"latitude": 28.6328, "longitude": 77.2195},
        "destination": {"latitude": 28.6305, "longitude": 77.2175},
        "step_km": 1.0
    },
    # Edge Case: Single point corridor (Origin == Destination)
    {
        "name": "India Gate Stationary Monitor",
        "origin": {"latitude": 28.6129, "longitude": 77.2295},
        "destination": {"latitude": 28.6129, "longitude": 77.2295},
        "step_km": 1.0
    },
    # Edge Case: Out-of-coverage Remote Highway (Rohtak to Panipat, beyond 10km threshold)
    {
        "name": "Rohtak to Panipat Highway (Out-of-Coverage Test)",
        "origin": {"latitude": 28.8955, "longitude": 76.6066},
        "destination": {"latitude": 29.3909, "longitude": 76.9635},
        "step_km": 5.0
    }
]


def run_phase3c_pipeline():
    """Execute complete Phase 3C generation pipeline."""
    PHASE3C_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Starting Phase 3C Pipeline...")

    # 1. Initialize Station Spatial Index
    catalog_path = XKDR_DIR / "station_catalog.csv"
    logger.info(f"Loading station catalog from {catalog_path}...")
    spatial_index = StationSpatialIndex(catalog_path=catalog_path)
    logger.info(f"Initialized spatial index with {spatial_index.count()} stations.")

    # 2. Discretize Benchmark Corridors
    all_segments = []
    all_corridor_metadata = []

    logger.info(f"Discretizing {len(BENCHMARK_CORRIDORS)} benchmark corridors...")
    for c_idx, c_info in enumerate(BENCHMARK_CORRIDORS):
        o = c_info["origin"]
        d = c_info["destination"]
        step = c_info.get("step_km", 1.0)
        cid = generate_corridor_id(o["latitude"], o["longitude"], d["latitude"], d["longitude"], step)

        segments = discretize_corridor(
            origin_lat=o["latitude"],
            origin_lon=o["longitude"],
            dest_lat=d["latitude"],
            dest_lon=d["longitude"],
            segment_length_km=step,
            corridor_id=cid
        )

        for s in segments:
            s["corridor_name"] = c_info["name"]
        all_segments.extend(segments)

        all_corridor_metadata.append({
            "corridor_id": cid,
            "corridor_name": c_info["name"],
            "origin": o,
            "destination": d,
            "segment_length_km": step,
            "segment_count": len(segments),
            "total_distance_km": round(sum(s["segment_length_km"] for s in segments), 3)
        })

    df_segments = pd.DataFrame(all_segments)
    segments_parquet_path = PHASE3C_DIR / "corridor_segments.parquet"
    df_segments.to_parquet(segments_parquet_path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(df_segments)} corridor segments to {segments_parquet_path}")

    # 3. Map Segments to Nearest Stations
    logger.info("Mapping corridor segments to nearest monitoring stations...")
    mapped_segments = spatial_index.map_corridor_segments(all_segments, max_distance_km=DEFAULT_MAX_STATION_DISTANCE_KM)
    df_mapped = pd.DataFrame(mapped_segments)

    valid_matches = int((df_mapped["station_match_status"] == "VALID_MATCH").sum())
    no_valid = int((df_mapped["station_match_status"] == "NO_VALID_STATION").sum())
    logger.info(f"Mapping Results: {valid_matches} valid matches, {no_valid} outside max distance threshold.")

    mapping_parquet_path = PHASE3C_DIR / "segment_station_mapping.parquet"
    df_mapped.to_parquet(mapping_parquet_path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved segment-station mapping to {mapping_parquet_path}")

    # 4. Generate Station Temporal Features
    parquet_raw_path = XKDR_DIR / "station_observations_2020_2024.parquet"
    logger.info(f"Building temporal features from {parquet_raw_path}...")
    df_temporal_features = build_full_temporal_feature_dataset(parquet_raw_path)
    logger.info(f"Generated temporal features with {len(df_temporal_features):,} rows and {len(df_temporal_features.columns)} columns.")

    temporal_parquet_path = PHASE3C_DIR / "station_temporal_features.parquet"
    df_temporal_features.to_parquet(temporal_parquet_path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved temporal features to {temporal_parquet_path}")

    # 5. Persist Feature Metadata
    feature_meta = get_feature_metadata_catalog()
    feature_meta_path = PHASE3C_DIR / "feature_metadata.json"
    with open(feature_meta_path, "w", encoding="utf-8") as f:
        json.dump(feature_meta, f, indent=2)
    logger.info(f"Saved feature metadata to {feature_meta_path}")

    # 6. Persist Phase 3C Data Provenance Metadata
    dist_valid = df_mapped[df_mapped["station_match_status"] == "VALID_MATCH"]["station_distance_km"]
    phase3c_meta = {
        "phase": "3C",
        "phase_name": "Corridor Geometry & Exposure Feature Engineering",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": "backend/datasets/xkdr/station_observations_2020_2024.parquet",
        "station_catalog": "backend/datasets/xkdr/station_catalog.csv",
        "coordinate_system": "WGS84 (EPSG:4326)",
        "distance_formula": "Haversine (Great-Circle Distance)",
        "earth_radius_km": EARTH_RADIUS_KM,
        "default_max_station_distance_km": DEFAULT_MAX_STATION_DISTANCE_KM,
        "corridor_summary": {
            "total_benchmark_corridors": len(BENCHMARK_CORRIDORS),
            "total_segments": len(df_mapped),
            "valid_station_matches": valid_matches,
            "no_valid_station_segments": no_valid,
            "min_distance_km": round(float(dist_valid.min()), 3) if not dist_valid.empty else None,
            "mean_distance_km": round(float(dist_valid.mean()), 3) if not dist_valid.empty else None,
            "median_distance_km": round(float(dist_valid.median()), 3) if not dist_valid.empty else None,
            "max_distance_km": round(float(dist_valid.max()), 3) if not dist_valid.empty else None
        },
        "temporal_feature_summary": {
            "total_rows": len(df_temporal_features),
            "total_stations": int(df_temporal_features["station_id"].nunique()),
            "feature_columns": list(df_temporal_features.columns),
            "lag_features": ["pm25_lag_1h", "pm25_lag_2h", "pm25_lag_3h", "pm25_lag_6h", "pm25_lag_12h", "pm25_lag_24h"],
            "rolling_features": ["pm25_rolling_mean_3h", "pm25_rolling_mean_6h", "pm25_rolling_mean_12h", "pm25_rolling_mean_24h"],
            "calendar_features": ["hour_of_day_sin", "hour_of_day_cos", "day_of_week"],
            "leakage_boundary": "Closed-past causal features strictly using observations at or prior to prediction reference timestamp t."
        },
        "scientific_integrity_guarantees": {
            "spatial_interpolation_performed": False,
            "zero_imputation_performed": False,
            "future_leakage_risk": False,
            "nearest_time_substitution_permitted": False,
            "exact_contiguous_lag_enforced": True
        }
    }

    phase3c_meta_path = PHASE3C_DIR / "phase3c_metadata.json"
    with open(phase3c_meta_path, "w", encoding="utf-8") as f:
        json.dump(phase3c_meta, f, indent=2)
    logger.info(f"Saved Phase 3C metadata to {phase3c_meta_path}")

    logger.info("Phase 3C Pipeline execution successfully completed!")


if __name__ == "__main__":
    run_phase3c_pipeline()
