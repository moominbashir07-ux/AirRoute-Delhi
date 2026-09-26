"""Tests for Phase 4 Commute Exposure Engine and Dose Calculations."""

import pytest
from datetime import datetime, timezone, timedelta
from ml_model.exposure_engine import (
    CommuteExposureEngine,
    MODE_SPEEDS_KM_H,
    MODE_VENTILATION_RATES_M3_H,
    MIN_ACCEPTABLE_COVERAGE_PERCENT
)


@pytest.fixture
def exposure_engine():
    return CommuteExposureEngine()


def test_mode_speed_and_ventilation_parameters():
    """Verify that mode speeds and scenario ventilation rates match scientific documentation."""
    assert MODE_SPEEDS_KM_H["walking"] == 5.0
    assert MODE_SPEEDS_KM_H["cycling"] == 15.0
    assert MODE_SPEEDS_KM_H["motorized"] == 30.0

    assert MODE_VENTILATION_RATES_M3_H["walking"] == 1.3
    assert MODE_VENTILATION_RATES_M3_H["cycling"] == 2.1
    assert MODE_VENTILATION_RATES_M3_H["motorized"] == 0.6


def test_inhaled_dose_formula_calculation(exposure_engine):
    """Verify mathematical formula M = C * V_E * delta_t for single segment exposure."""
    # Let C = 100 ug/m3, V_E = 2.1 m3/h (cycling), delta_t = 0.5 hours (30 min)
    # Expected M = 100 * 2.1 * 0.5 = 105.0 ug
    c = 100.0
    v_e = 2.1
    dt_hours = 0.5
    expected_dose = c * v_e * dt_hours
    assert expected_dose == 105.0


def test_optimize_commute_valid_delhi_corridor(exposure_engine):
    """Test full corridor exposure optimization between Connaught Place and South Extension."""
    now = datetime.now(timezone.utc)
    res = exposure_engine.optimize_commute(
        origin_lat=28.6315,
        origin_lon=77.2167,
        dest_lat=28.5672,
        dest_lon=77.2100,
        mode="cycling",
        departure_window_start=now,
        departure_window_end=now + timedelta(hours=1),
        interval_minutes=15
    )

    assert res["status"] == "success"
    assert "corridor_summary" in res
    assert res["corridor_summary"]["mode"] == "cycling"
    assert res["corridor_summary"]["distance_km"] > 0.0

    assert "recommended_departure" in res
    rec = res["recommended_departure"]
    assert rec["estimated_inhaled_pm25_ug"] > 0.0
    assert rec["time_weighted_pm25_ug_m3"] > 0.0
    assert rec["coverage_percent"] >= MIN_ACCEPTABLE_COVERAGE_PERCENT
    assert "recommendation_statement" in rec

    assert len(res["departure_candidates"]) > 1
    # Check that exactly one departure candidate is marked recommended
    rec_count = sum(1 for c in res["departure_candidates"] if c["is_recommended"])
    assert rec_count == 1

    # Check that segment breakdown is populated
    assert len(res["segment_breakdown"]) > 0
    seg0 = res["segment_breakdown"][0]
    assert "mapped_station_id" in seg0
    assert "segment_inhaled_dose_ug" in seg0


def test_optimize_commute_out_of_bounds_coordinates(exposure_engine):
    """Verify rejection of coordinates outside Delhi/NCR operational boundaries."""
    now = datetime.now(timezone.utc)
    # Mumbai coordinates
    with pytest.raises(ValueError, match="outside the Delhi NCR operational envelope"):
        exposure_engine.optimize_commute(
            origin_lat=19.0760,
            origin_lon=72.8777,
            dest_lat=28.6315,
            dest_lon=77.2167,
            mode="walking",
            departure_window_start=now,
            departure_window_end=now + timedelta(hours=1)
        )


def test_optimize_commute_invalid_mode(exposure_engine):
    """Verify rejection of unsupported travel modes."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="Unsupported mode 'helicopter'"):
        exposure_engine.optimize_commute(
            origin_lat=28.6315,
            origin_lon=77.2167,
            dest_lat=28.5672,
            dest_lon=77.2100,
            mode="helicopter",
            departure_window_start=now,
            departure_window_end=now + timedelta(hours=1)
        )


def test_optimize_commute_excessive_forecast_horizon(exposure_engine):
    """Verify rejection of journeys exceeding the validated 6-hour forecast horizon."""
    now = datetime.now(timezone.utc)
    # Walking across Delhi (35 km) at 5 km/h takes 7 hours -> exceeds 6h horizon
    with pytest.raises(ValueError, match="exceeds the validated 6-hour forecast horizon"):
        exposure_engine.optimize_commute(
            origin_lat=28.4089,  # Faridabad
            origin_lon=77.3178,
            dest_lat=28.7325,  # Rohini
            dest_lon=77.1189,
            mode="walking",
            departure_window_start=now,
            departure_window_end=now + timedelta(minutes=30)
        )
