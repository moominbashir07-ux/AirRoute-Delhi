"""Tests for Phase 3D Production Inference Contract."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ml_model.forecasting_engine import MultiHorizonForecaster


@pytest.fixture
def forecaster():
    f = MultiHorizonForecaster()
    f.load_artifacts()
    return f


@pytest.fixture
def mock_inference_inputs():
    pred_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
    # 48 hours of historical observations
    hist_times = [pred_time - timedelta(hours=i) for i in range(48)]
    hist_values = [120.0 + (i % 15) for i in range(48)]
    hist_series = pd.Series(hist_values, index=hist_times)

    # 12 hours of future weather forecasts
    future_wx_times = [pred_time + timedelta(hours=i) for i in range(1, 13)]
    wx_rows = []
    for ts in future_wx_times:
        wx_rows.append({
            "timestamp_utc": ts,
            "temperature": 18.5,
            "humidity": 65.0,
            "wind_speed": 7.2,
            "wind_direction_sin": 0.5,
            "wind_direction_cos": 0.866,
            "boundary_layer_height": 450.0,
            "surface_pressure": 1012.0
        })
    df_wx = pd.DataFrame(wx_rows)
    return pred_time, hist_series, df_wx


def test_forecast_pm25_contract_schema(forecaster, mock_inference_inputs):
    pred_time, hist_series, df_wx = mock_inference_inputs

    res = forecaster.forecast_pm25(
        station_id="site_113",
        station_lat=28.6515,
        station_lon=77.1473,
        prediction_time=pred_time,
        historical_pm25_series=hist_series,
        future_weather_df=df_wx
    )

    # Verify root fields
    assert res["station_id"] == "site_113"
    assert res["prediction_time"] == pred_time.isoformat()
    assert res["persistence_baseline_pm25"] == pytest.approx(120.0, 0.1)
    assert "forecasts" in res

    # Verify all 6 horizons
    for h in [1, 2, 3, 4, 5, 6]:
        h_str = f"{h}h"
        assert h_str in res["forecasts"]
        f_h = res["forecasts"][h_str]
        assert "timestamp" in f_h
        assert "pm25_ug_m3" in f_h
        assert isinstance(f_h["pm25_ug_m3"], float)
        assert f_h["pm25_ug_m3"] >= 0.0
        assert "is_clipped_non_negative" in f_h
        # Timestamp must be exactly t + h hours
        exp_ts = (pred_time + timedelta(hours=h)).isoformat()
        assert f_h["timestamp"] == exp_ts


def test_inference_deterministic_outputs(forecaster, mock_inference_inputs):
    pred_time, hist_series, df_wx = mock_inference_inputs

    res1 = forecaster.forecast_pm25("site_113", 28.65, 77.15, pred_time, hist_series, df_wx)
    res2 = forecaster.forecast_pm25("site_113", 28.65, 77.15, pred_time, hist_series, df_wx)

    for h in [1, 2, 3, 4, 5, 6]:
        h_str = f"{h}h"
        assert res1["forecasts"][h_str]["pm25_ug_m3"] == res2["forecasts"][h_str]["pm25_ug_m3"]


def test_inference_with_missing_lags_handled_gracefully(forecaster, mock_inference_inputs):
    pred_time, _, df_wx = mock_inference_inputs
    # Historical series has ONLY current observation, all lags are missing (NaN)
    sparse_series = pd.Series([150.0], index=[pred_time])

    res = forecaster.forecast_pm25(
        station_id="site_113",
        station_lat=28.65,
        station_lon=77.15,
        prediction_time=pred_time,
        historical_pm25_series=sparse_series,
        future_weather_df=df_wx
    )

    # Must still produce valid predictions using model's native NaN handling
    assert "forecasts" in res
    for h in [1, 2, 3, 4, 5, 6]:
        pred_val = res["forecasts"][f"{h}h"]["pm25_ug_m3"]
        assert isinstance(pred_val, float)
        assert not np.isnan(pred_val)
        assert pred_val >= 0.0
