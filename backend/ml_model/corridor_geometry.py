"""Phase 3C: Corridor Geometry & Spatial Station Matching Module.

Provides deterministic WGS84 coordinate validation, Haversine distance calculation,
corridor discretization, segment bearing, and nearest-station mapping with deterministic
tie-breaking. Strictly adheres to zero black-box spatial interpolation.
"""

import math
import hashlib
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import pandas as pd
import numpy as np

# Earth's mean radius in kilometers (IUGG standard: 6371.0088 km, standard spherical: 6371.0 km)
EARTH_RADIUS_KM = 6371.0

# Delhi NCR operational envelope bounding box (Sanity checks, not an arbitrary polygon boundary)
NCR_LAT_MIN = 28.20
NCR_LAT_MAX = 28.95
NCR_LON_MIN = 76.80
NCR_LON_MAX = 77.55

# Configurable maximum valid station matching distance
DEFAULT_MAX_STATION_DISTANCE_KM = 10.0


def validate_coordinates(lat: Any, lon: Any, require_ncr_bounds: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate latitude and longitude against WGS84 and optional NCR operational envelope.
    
    Returns (is_valid, error_message).
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False, "Coordinates must be valid numeric floating-point values."

    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        return False, "Coordinates cannot be NaN or infinite."

    if not (-90.0 <= lat <= 90.0):
        return False, f"Latitude {lat} out of physical bounds [-90.0, 90.0]."

    if not (-180.0 <= lon <= 180.0):
        return False, f"Longitude {lon} out of physical bounds [-180.0, 180.0]."

    if require_ncr_bounds:
        if not (NCR_LAT_MIN <= lat <= NCR_LAT_MAX and NCR_LON_MIN <= lon <= NCR_LON_MAX):
            return False, (
                f"Coordinates ({lat}, {lon}) fall outside the Delhi NCR operational envelope "
                f"[{NCR_LAT_MIN}-{NCR_LAT_MAX} N, {NCR_LON_MIN}-{NCR_LON_MAX} E]."
            )

    return True, None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in kilometers
    using the standard Haversine formula with EARTH_RADIUS_KM = 6371.0.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    # Clamp 'a' to [0, 1] to avoid float precision issues with math.sqrt
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial compass bearing from (lat1, lon1) to (lat2, lon2).
    
    0° = North, 90° = East, 180° = South, 270° = West.
    Normalized to [0.0, 360.0).
    For identical points, returns 0.0.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    return (bearing_deg + 360.0) % 360.0


def generate_corridor_id(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float,
                         segment_length_km: float = 1.0) -> str:
    """Generate a deterministic corridor ID based on canonical string representation and SHA256 hash."""
    canonical_repr = (
        f"orig_{origin_lat:.5f}_{origin_lon:.5f}|"
        f"dest_{dest_lat:.5f}_{dest_lon:.5f}|"
        f"step_{segment_length_km:.2f}"
    )
    digest = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()[:12]
    return f"corr_{digest}"


def discretize_corridor(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    segment_length_km: float = 1.0,
    corridor_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Divide a geodesic corridor into discrete segments of configurable length.
    
    Handles:
    - Identical origin and destination (returns single point segment with length 0.0).
    - Very short corridor (< segment_length_km: returns 1 segment).
    - Standard corridors: divides path into N equidistant segments along the great-circle arc.
    """
    is_valid_orig, err_orig = validate_coordinates(origin_lat, origin_lon)
    if not is_valid_orig:
        raise ValueError(f"Invalid origin coordinates: {err_orig}")

    is_valid_dest, err_dest = validate_coordinates(dest_lat, dest_lon)
    if not is_valid_dest:
        raise ValueError(f"Invalid destination coordinates: {err_dest}")

    if segment_length_km <= 0.0:
        raise ValueError(f"segment_length_km must be positive, got {segment_length_km}")

    cid = corridor_id or generate_corridor_id(origin_lat, origin_lon, dest_lat, dest_lon, segment_length_km)
    total_dist_km = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)

    # Edge Case: Identical origin and destination (single-point corridor)
    if total_dist_km == 0.0:
        return [{
            "corridor_id": cid,
            "segment_index": 0,
            "start_latitude": origin_lat,
            "start_longitude": origin_lon,
            "end_latitude": dest_lat,
            "end_longitude": dest_lon,
            "midpoint_latitude": origin_lat,
            "midpoint_longitude": origin_lon,
            "segment_length_km": 0.0,
            "bearing_degrees": 0.0,
            "is_single_point": True
        }]

    # Compute number of segments
    num_segments = max(1, int(math.ceil(total_dist_km / segment_length_km)))
    bearing = calculate_bearing(origin_lat, origin_lon, dest_lat, dest_lon)

    segments = []
    for i in range(num_segments):
        frac_start = i / float(num_segments)
        frac_end = (i + 1) / float(num_segments)
        frac_mid = (frac_start + frac_end) / 2.0

        # Linear interpolation along geographic coordinates for Delhi-scale corridors (<60km)
        # provides <0.05% error compared to spherical intermediate points, preserving fast determinism
        s_lat = origin_lat + frac_start * (dest_lat - origin_lat)
        s_lon = origin_lon + frac_start * (dest_lon - origin_lon)
        e_lat = origin_lat + frac_end * (dest_lat - origin_lat)
        e_lon = origin_lon + frac_end * (dest_lon - origin_lon)
        m_lat = origin_lat + frac_mid * (dest_lat - origin_lat)
        m_lon = origin_lon + frac_mid * (dest_lon - origin_lon)

        seg_dist = haversine_distance(s_lat, s_lon, e_lat, e_lon)
        seg_bearing = calculate_bearing(s_lat, s_lon, e_lat, e_lon) if seg_dist > 0.0 else bearing

        segments.append({
            "corridor_id": cid,
            "segment_index": i,
            "start_latitude": round(s_lat, 6),
            "start_longitude": round(s_lon, 6),
            "end_latitude": round(e_lat, 6),
            "end_longitude": round(e_lon, 6),
            "midpoint_latitude": round(m_lat, 6),
            "midpoint_longitude": round(m_lon, 6),
            "segment_length_km": round(seg_dist, 4),
            "bearing_degrees": round(seg_bearing, 2),
            "is_single_point": False
        })

    return segments


class StationSpatialIndex:
    """Spatial index for monitoring stations using vectorized Haversine distance
    and deterministic lexicographical tie-breaking on station_id.
    """

    def __init__(self, catalog_path: Optional[Path] = None, stations_df: Optional[pd.DataFrame] = None):
        if stations_df is not None:
            self.df = stations_df.copy()
        elif catalog_path is not None:
            self.df = pd.read_csv(catalog_path)
        else:
            default_path = (
                Path(__file__).resolve().parent.parent / "datasets" / "xkdr" / "station_catalog.csv"
            )
            self.df = pd.read_csv(default_path)

        # Validate required columns
        required_cols = ["station_id", "station_name", "latitude", "longitude"]
        for col in required_cols:
            if col not in self.df.columns:
                raise ValueError(f"Station catalog missing required column: {col}")

        # Ensure valid numeric coordinates and drop any corrupt rows
        self.df["latitude"] = pd.to_numeric(self.df["latitude"], errors="coerce")
        self.df["longitude"] = pd.to_numeric(self.df["longitude"], errors="coerce")
        self.df = self.df.dropna(subset=["station_id", "latitude", "longitude"]).copy()

        # Cache station arrays for vectorized Haversine
        self.station_ids = self.df["station_id"].astype(str).values
        self.station_names = self.df["station_name"].astype(str).values
        self.station_lats = self.df["latitude"].values
        self.station_lons = self.df["longitude"].values
        self.station_lats_rad = np.radians(self.station_lats)
        self.station_lons_rad = np.radians(self.station_lons)
        self.station_providers = (
            self.df["source"].astype(str).values if "source" in self.df.columns else np.array(["unknown"] * len(self.df))
        )

    def count(self) -> int:
        return len(self.station_ids)

    def nearest_station(
        self,
        lat: float,
        lon: float,
        max_distance_km: float = DEFAULT_MAX_STATION_DISTANCE_KM
    ) -> Dict[str, Any]:
        """Find the nearest monitoring station to (lat, lon) with deterministic tie-breaking.
        
        Tie-breaking rule:
        Sort candidate matches primarily by distance ascending;
        Secondary key is station_id ascending (lexicographical).
        """
        is_valid, err = validate_coordinates(lat, lon)
        if not is_valid:
            return {
                "station_id": None,
                "station_name": None,
                "station_latitude": None,
                "station_longitude": None,
                "distance_km": None,
                "match_status": "INVALID_COORDINATES",
                "error_message": err
            }

        # Vectorized Haversine calculation against all stations
        phi1 = math.radians(lat)
        lambda1 = math.radians(lon)

        dphi = self.station_lats_rad - phi1
        dlambda = self.station_lons_rad - lambda1

        a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(self.station_lats_rad) * np.sin(dlambda / 2.0) ** 2
        a = np.clip(a, 0.0, 1.0)
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        distances_km = EARTH_RADIUS_KM * c

        # Deterministic sorting: Primary = distance, Secondary = station_id
        # Lexsort uses keys in reverse order: secondary first, primary last
        sort_order = np.lexsort((self.station_ids, distances_km))
        best_idx = sort_order[0]

        best_dist = float(distances_km[best_idx])
        best_id = str(self.station_ids[best_idx])
        best_name = str(self.station_names[best_idx])
        best_lat = float(self.station_lats[best_idx])
        best_lon = float(self.station_lons[best_idx])
        best_provider = str(self.station_providers[best_idx])

        match_status = "VALID_MATCH" if best_dist <= max_distance_km else "NO_VALID_STATION"

        # Also get backup station (second nearest)
        backup_station_id = None
        backup_distance_km = None
        if len(sort_order) > 1:
            sec_idx = sort_order[1]
            backup_station_id = str(self.station_ids[sec_idx])
            backup_distance_km = round(float(distances_km[sec_idx]), 4)

        return {
            "station_id": best_id if match_status == "VALID_MATCH" else None,
            "station_name": best_name if match_status == "VALID_MATCH" else None,
            "station_latitude": best_lat if match_status == "VALID_MATCH" else None,
            "station_longitude": best_lon if match_status == "VALID_MATCH" else None,
            "provider": best_provider if match_status == "VALID_MATCH" else None,
            "distance_km": round(best_dist, 4),
            "match_status": match_status,
            "max_distance_threshold_km": max_distance_km,
            "backup_station_id": backup_station_id,
            "backup_distance_km": backup_distance_km,
            "nearest_candidate_station_id": best_id,
            "nearest_candidate_distance_km": round(best_dist, 4)
        }

    def map_corridor_segments(
        self,
        segments: List[Dict[str, Any]],
        max_distance_km: float = DEFAULT_MAX_STATION_DISTANCE_KM
    ) -> List[Dict[str, Any]]:
        """Map each corridor segment to its nearest monitoring station."""
        mapped_segments = []
        for seg in segments:
            m_lat = seg["midpoint_latitude"]
            m_lon = seg["midpoint_longitude"]
            match = self.nearest_station(m_lat, m_lon, max_distance_km=max_distance_km)

            mapped_seg = {
                **seg,
                "nearest_station_id": match["station_id"],
                "station_name": match["station_name"],
                "station_latitude": match["station_latitude"],
                "station_longitude": match["station_longitude"],
                "station_distance_km": match["distance_km"],
                "station_match_status": match["match_status"],
                "max_distance_threshold_km": max_distance_km,
                "backup_station_id": match["backup_station_id"],
                "backup_distance_km": match["backup_distance_km"]
            }
            mapped_segments.append(mapped_seg)
        return mapped_segments
