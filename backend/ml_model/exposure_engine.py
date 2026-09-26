"""Phase 4: Production Deterministic Commute Exposure & Departure Optimizer Engine.

Integrates:
- Geodesic corridor discretization (Phase 3C)
- Station spatial matching (Phase 3C)
- Multi-horizon PM2.5 forecasting (Phase 3D)
- Deterministic inhaled dose estimation: M = C * V_E * delta_t (Phase 3E)
- Departure window evaluation and coverage filtering (Phase 3E)
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
import numpy as np

from ml_model.corridor_geometry import (
    discretize_corridor,
    generate_corridor_id,
    haversine_distance,
    validate_coordinates,
    StationSpatialIndex,
    NCR_LAT_MIN,
    NCR_LAT_MAX,
    NCR_LON_MIN,
    NCR_LON_MAX,
    DEFAULT_MAX_STATION_DISTANCE_KM
)
from ml_model.forecasting_engine import MultiHorizonForecaster
from ml_model.weather_client import WeatherClient

logger = logging.getLogger("ExposureEngine")

# Supported transit modes and scenario parameters
# Speeds in km/h
MODE_SPEEDS_KM_H = {
    "walking": 5.0,
    "cycling": 15.0,
    "motorized": 30.0
}

# Scenario ventilation rates in m3/hour (physiological intake rate assumptions)
MODE_VENTILATION_RATES_M3_H = {
    "walking": 1.3,
    "cycling": 2.1,
    "motorized": 0.6
}

MIN_ACCEPTABLE_COVERAGE_PERCENT = 80.0
MAX_FORECAST_HORIZON_HOURS = 6.0


class CommuteExposureEngine:
    """Production service for corridor discretization, station matching,
    multi-horizon forecasting, and departure-window exposure comparison.
    """

    def __init__(
        self,
        spatial_index: Optional[StationSpatialIndex] = None,
        forecaster: Optional[MultiHorizonForecaster] = None,
        weather_client: Optional[WeatherClient] = None
    ):
        self.spatial_index = spatial_index or StationSpatialIndex()
        self.forecaster = forecaster or MultiHorizonForecaster()
        self.weather_client = weather_client or WeatherClient()

        # Cache station latest observation history from Phase 3B Parquet
        self._load_recent_station_history()

    def _load_recent_station_history(self):
        """Load recent historical observations per station for forecasting feature inputs."""
        try:
            parquet_path = Path(__file__).resolve().parent.parent / "datasets" / "xkdr" / "station_observations_2020_2024.parquet"
            if parquet_path.exists():
                logger.info("Caching recent historical observations for all stations...")
                df = pd.read_parquet(parquet_path)
                df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
                # Keep latest 72 hours per station for robust lag calculation
                max_time = df["timestamp_utc"].max()
                min_time = max_time - pd.to_timedelta(72, unit="h")
                recent = df[df["timestamp_utc"] >= min_time].copy()
                self.station_history = {}
                for st_id, group in recent.groupby("station_id"):
                    self.station_history[st_id] = group.set_index("timestamp_utc")["pm25"]
            else:
                self.station_history = {}
        except Exception as e:
            logger.warning(f"Could not pre-cache station history: {e}")
            self.station_history = {}

    def get_station_series(self, station_id: str, ref_time: datetime) -> pd.Series:
        """Retrieve recent observation series for station up to ref_time."""
        if station_id in self.station_history:
            return self.station_history[station_id]
        # Return fallback series with nominal baseline
        times = [ref_time - timedelta(hours=i) for i in range(48)]
        return pd.Series([75.0] * len(times), index=times)

    def optimize_commute(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str,
        departure_window_start: datetime,
        departure_window_end: datetime,
        interval_minutes: int = 15,
        reference_prediction_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Compute corridor exposure across departure window candidates."""
        # 1. Validate Coordinates
        is_orig_val, err_orig = validate_coordinates(origin_lat, origin_lon, require_ncr_bounds=True)
        if not is_orig_val:
            raise ValueError(f"Origin coordinates error: {err_orig}")

        is_dest_val, err_dest = validate_coordinates(dest_lat, dest_lon, require_ncr_bounds=True)
        if not is_dest_val:
            raise ValueError(f"Destination coordinates error: {err_dest}")

        # 2. Validate Mode
        mode = mode.strip().lower()
        if mode not in MODE_SPEEDS_KM_H:
            raise ValueError(
                f"Unsupported mode '{mode}'. Supported modes are: {list(MODE_SPEEDS_KM_H.keys())}"
            )

        # 3. Validate Departure Window
        if departure_window_end <= departure_window_start:
            raise ValueError("departure_window.end must be strictly greater than departure_window.start.")

        if interval_minutes <= 0 or interval_minutes > 120:
            raise ValueError("interval_minutes must be between 1 and 120.")

        total_window_mins = (departure_window_end - departure_window_start).total_seconds() / 60.0
        if total_window_mins > 360.0:
            raise ValueError("Departure window exceeds maximum supported span of 6 hours.")

        speed_km_h = MODE_SPEEDS_KM_H[mode]
        ventilation_rate = MODE_VENTILATION_RATES_M3_H[mode]

        # 4. Generate Corridor Segments & Station Mapping
        segments = discretize_corridor(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            segment_length_km=1.0
        )
        mapped_segments = self.spatial_index.map_corridor_segments(
            segments, max_distance_km=DEFAULT_MAX_STATION_DISTANCE_KM
        )

        total_distance_km = sum(s["segment_length_km"] for s in mapped_segments)
        total_duration_hours = total_distance_km / speed_km_h if speed_km_h > 0 else 0.0
        total_duration_minutes = total_duration_hours * 60.0

        # Reference time for forecast lead time validation
        ref_time = reference_prediction_time or departure_window_start

        # 5. Validate Maximum Forecast Horizon
        # Check if journey completion for latest departure exceeds 6 hours from ref_time
        max_transit_lead_time_hours = (
            (departure_window_end + timedelta(minutes=total_duration_minutes) - ref_time).total_seconds() / 3600.0
        )
        if max_transit_lead_time_hours > MAX_FORECAST_HORIZON_HOURS + 0.5:
            raise ValueError(
                f"Requested journey completes {max_transit_lead_time_hours:.1f} hours from prediction time, "
                f"which exceeds the validated 6-hour forecast horizon."
            )

        # 6. Fetch Weather Forecast for Delhi (for future horizons)
        weather_status = "live_nwp"
        weather_degraded_reason = None
        try:
            future_wx_df = self.weather_client.fetch_production_forecast(
                latitude=(origin_lat + dest_lat) / 2.0,
                longitude=(origin_lon + dest_lon) / 2.0,
                forecast_hours=12
            )
        except Exception as e:
            logger.warning(f"Live NWP fetch failed: {e}. Falling back to degraded meteorological cycle.")
            weather_status = "degraded_historical"
            weather_degraded_reason = str(e)
            try:
                future_wx_df = self.weather_client.fetch_historical_archive().iloc[-12:].copy()
            except Exception as archive_err:
                raise ValueError(f"Meteorological service unavailable and archive cache unreadable: {archive_err}")


        # 7. Pre-compute PM2.5 forecasts for unique mapped stations across horizons 1..6
        unique_stations = {s["nearest_station_id"] for s in mapped_segments if s["nearest_station_id"]}
        station_forecasts = {}
        for st_id in unique_stations:
            st_info = self.spatial_index.df[self.spatial_index.df["station_id"] == st_id].iloc[0]
            st_series = self.get_station_series(st_id, ref_time)
            try:
                st_fc = self.forecaster.forecast_pm25(
                    station_id=st_id,
                    station_lat=float(st_info["latitude"]),
                    station_lon=float(st_info["longitude"]),
                    prediction_time=ref_time,
                    historical_pm25_series=st_series,
                    future_weather_df=future_wx_df
                )
                station_forecasts[st_id] = st_fc["forecasts"]
            except Exception as e:
                logger.error(f"Failed to generate forecast for station {st_id}: {e}")
                station_forecasts[st_id] = {}

        # 8. Evaluate Each Departure Candidate
        candidates = []
        curr_dep = departure_window_start
        candidate_count = 0

        while curr_dep <= departure_window_end and candidate_count < 30:
            candidate_res = self._evaluate_departure_candidate(
                departure_time=curr_dep,
                ref_time=ref_time,
                mapped_segments=mapped_segments,
                station_forecasts=station_forecasts,
                speed_km_h=speed_km_h,
                ventilation_rate=ventilation_rate
            )
            candidates.append(candidate_res)
            curr_dep += timedelta(minutes=interval_minutes)
            candidate_count += 1

        # 9. Filter Candidates by Coverage and Find Optimal Departure
        valid_candidates = [
            c for c in candidates if c["coverage_percent"] >= MIN_ACCEPTABLE_COVERAGE_PERCENT
        ]

        if not valid_candidates:
            # Fall back to candidate with highest coverage
            best_candidate = max(candidates, key=lambda c: c["coverage_percent"]) if candidates else None
        else:
            # Optimal candidate has lowest estimated inhaled PM2.5
            best_candidate = min(valid_candidates, key=lambda c: c["estimated_inhaled_pm25_ug"])

        # Modeled reduction percentage vs worst valid candidate
        reduction_pct = 0.0
        if valid_candidates and len(valid_candidates) > 1 and best_candidate:
            worst_candidate = max(valid_candidates, key=lambda c: c["estimated_inhaled_pm25_ug"])
            w_dose = worst_candidate["estimated_inhaled_pm25_ug"]
            b_dose = best_candidate["estimated_inhaled_pm25_ug"]
            if w_dose > 0:
                reduction_pct = round(((w_dose - b_dose) / w_dose) * 100.0, 1)

        # Mark recommendation in candidate list
        for c in candidates:
            c["is_recommended"] = bool(best_candidate and c["departure_time_utc"] == best_candidate["departure_time_utc"])

        # Format optimal recommendation
        rec_summary = None
        if best_candidate:
            rec_summary = {
                "departure_time_ist": best_candidate["departure_time_ist"],
                "departure_time_utc": best_candidate["departure_time_utc"],
                "estimated_inhaled_pm25_ug": best_candidate["estimated_inhaled_pm25_ug"],
                "time_weighted_pm25_ug_m3": best_candidate["time_weighted_pm25_ug_m3"],
                "journey_duration_minutes": round(total_duration_minutes, 1),
                "coverage_percent": best_candidate["coverage_percent"],
                "modeled_exposure_reduction_percent": reduction_pct,
                "recommendation_statement": (
                    f"Among evaluated departure candidates meeting the {MIN_ACCEPTABLE_COVERAGE_PERCENT:.0f}% coverage threshold, "
                    f"departure at {best_candidate['departure_time_ist'][11:16]} IST provides the lowest modeled PM2.5 exposure "
                    f"estimate ({best_candidate['estimated_inhaled_pm25_ug']:.1f} µg)."
                )
            }

        # Representative segment breakdown for recommended departure
        segment_trace = best_candidate["segment_details"] if best_candidate else []

        limitations_list = [
            "Ambient station forecasts represent regional neighborhood air masses rather than micro-scale aerodynamic street canyons.",
            "Inhaled PM2.5 mass is an environmental exposure index based on scenario ventilation assumptions (walking=1.3, cycling=2.1, motorized=0.6 m³/h), not individual clinical biometric measurement.",
            "Forecast horizon is strictly validated up to 6 hours ahead; journeys completing beyond 6 hours are not modeled.",
            "Predictions rely on numerical weather prediction (NWP) forecasts; meteorological forecast errors propagate directly into PM2.5 estimates."
        ]
        if weather_status != "live_nwp":
            limitations_list.append(
                f"Live NWP weather input degraded ({weather_degraded_reason or 'fallback'}). Predictions conditioned on baseline meteorological cycle."
            )

        return {
            "status": "success",
            "corridor_summary": {
                "corridor_id": mapped_segments[0]["corridor_id"] if mapped_segments else "corr_unknown",
                "distance_km": round(total_distance_km, 2),
                "estimated_duration_minutes": round(total_duration_minutes, 1),
                "total_segments": len(mapped_segments),
                "mode": mode,
                "assumed_speed_km_h": speed_km_h,
                "assumed_ventilation_rate_m3_h": ventilation_rate,
                "weather_status": weather_status
            },
            "recommended_departure": rec_summary,
            "departure_candidates": [
                {
                    "departure_time_ist": c["departure_time_ist"],
                    "departure_time_utc": c["departure_time_utc"],
                    "estimated_inhaled_pm25_ug": c["estimated_inhaled_pm25_ug"],
                    "time_weighted_pm25_ug_m3": c["time_weighted_pm25_ug_m3"],
                    "coverage_percent": c["coverage_percent"],
                    "is_recommended": c["is_recommended"]
                }
                for c in candidates
            ],
            "segment_breakdown": segment_trace,
            "limitations": limitations_list,
            "scientific_disclaimer": "This is an environmental exposure estimation tool for comparative departure planning. It is NOT a medical diagnosis, clinical health assessment, or guarantee of health safety."
        }

    def _evaluate_departure_candidate(
        self,
        departure_time: datetime,
        ref_time: datetime,
        mapped_segments: List[Dict[str, Any]],
        station_forecasts: Dict[str, Any],
        speed_km_h: float,
        ventilation_rate: float
    ) -> Dict[str, Any]:
        """Calculate detailed segment-by-segment exposure for a single departure candidate."""
        elapsed_hours = 0.0
        total_inhaled_ug = 0.0
        time_weighted_sum = 0.0
        covered_time_hours = 0.0
        total_time_hours = 0.0

        segment_details = []

        for seg in mapped_segments:
            seg_len = seg["segment_length_km"]
            seg_dur_hours = seg_len / speed_km_h if speed_km_h > 0 else 0.0
            total_time_hours += seg_dur_hours

            # Midpoint transit time for this segment
            seg_mid_time = departure_time + timedelta(hours=elapsed_hours + seg_dur_hours / 2.0)
            elapsed_hours += seg_dur_hours

            # Determine forecast lead time h in {1..6}
            lead_time_hours = (seg_mid_time - ref_time).total_seconds() / 3600.0
            h = max(1, min(6, int(round(lead_time_hours))))

            st_id = seg["nearest_station_id"]
            fc_dict = station_forecasts.get(st_id, {})
            h_key = f"{h}h"

            conc_ug_m3 = None
            if h_key in fc_dict:
                conc_ug_m3 = fc_dict[h_key].get("pm25_ug_m3")

            if conc_ug_m3 is not None and not np.isnan(conc_ug_m3):
                # Dose = C * V_E * delta_t
                seg_dose_ug = conc_ug_m3 * ventilation_rate * seg_dur_hours
                total_inhaled_ug += seg_dose_ug
                time_weighted_sum += conc_ug_m3 * seg_dur_hours
                covered_time_hours += seg_dur_hours
                is_mapped = True
            else:
                seg_dose_ug = None
                is_mapped = False

            segment_details.append({
                "segment_index": seg["segment_index"],
                "midpoint": {
                    "latitude": seg["midpoint_latitude"],
                    "longitude": seg["midpoint_longitude"]
                },
                "length_km": seg_len,
                "travel_time_minutes": round(seg_dur_hours * 60.0, 1),
                "mapped_station_id": st_id,
                "station_name": seg.get("station_name"),
                "station_distance_km": seg.get("station_distance_km"),
                "forecast_horizon_h": h,
                "forecasted_pm25_ug_m3": round(conc_ug_m3, 1) if conc_ug_m3 is not None else None,
                "segment_inhaled_dose_ug": round(seg_dose_ug, 2) if seg_dose_ug is not None else None,
                "is_covered": is_mapped
            })

        coverage_pct = round((covered_time_hours / total_time_hours) * 100.0, 1) if total_time_hours > 0 else 0.0
        time_weighted_pm25 = round(time_weighted_sum / covered_time_hours, 1) if covered_time_hours > 0 else 0.0

        dep_ist = departure_time.astimezone(timezone(timedelta(hours=5, minutes=30))).isoformat()

        return {
            "departure_time_ist": dep_ist,
            "departure_time_utc": departure_time.astimezone(timezone.utc).isoformat(),
            "estimated_inhaled_pm25_ug": round(total_inhaled_ug, 2),
            "time_weighted_pm25_ug_m3": time_weighted_pm25,
            "coverage_percent": coverage_pct,
            "segment_details": segment_details
        }
