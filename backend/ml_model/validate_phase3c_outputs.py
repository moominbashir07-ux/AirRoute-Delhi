import json
import pandas as pd
from pathlib import Path

p3c_dir = Path("datasets/phase3c")

df_seg = pd.read_parquet(p3c_dir / "corridor_segments.parquet")
df_map = pd.read_parquet(p3c_dir / "segment_station_mapping.parquet")
df_temp = pd.read_parquet(p3c_dir / "station_temporal_features.parquet")

with open(p3c_dir / "feature_metadata.json", "r", encoding="utf-8") as f:
    feat_meta = json.load(f)

with open(p3c_dir / "phase3c_metadata.json", "r", encoding="utf-8") as f:
    p3c_meta = json.load(f)

print("=== PHASE 3C INDEPENDENT RELOAD SUMMARY ===")
print("Corridor segments rows:", len(df_seg))
print("Corridors count:", df_seg["corridor_id"].nunique())
print("Mapped segments rows:", len(df_map))
print("Valid matches:", (df_map["station_match_status"] == "VALID_MATCH").sum())
print("No valid matches:", (df_map["station_match_status"] == "NO_VALID_STATION").sum())

valid_dists = df_map[df_map["station_match_status"] == "VALID_MATCH"]["station_distance_km"]
print(f"Distance min: {valid_dists.min():.3f} km, mean: {valid_dists.mean():.3f} km, median: {valid_dists.median():.3f} km, max: {valid_dists.max():.3f} km")
print("Temporal feature rows:", len(df_temp))
print("Temporal stations count:", df_temp["station_id"].nunique())
print("Temporal feature columns:", list(df_temp.columns))
print("Feature metadata keys count:", len(feat_meta))
print("Metadata phase:", p3c_meta.get("phase"), p3c_meta.get("version"))
print(f"Lag 1h null count: {df_temp['pm25_lag_1h'].isna().sum()} ({df_temp['pm25_lag_1h'].isna().mean()*100:.2f}%)")
print(f"Lag 24h null count: {df_temp['pm25_lag_24h'].isna().sum()} ({df_temp['pm25_lag_24h'].isna().mean()*100:.2f}%)")
print(f"Rolling 6h null count: {df_temp['pm25_rolling_mean_6h'].isna().sum()} ({df_temp['pm25_rolling_mean_6h'].isna().mean()*100:.2f}%)")
print(f"Rolling 24h null count: {df_temp['pm25_rolling_mean_24h'].isna().sum()} ({df_temp['pm25_rolling_mean_24h'].isna().mean()*100:.2f}%)")
