# PHASE 3D MODEL CARD: STATION-LEVEL MULTI-HORIZON PM2.5 FORECASTER

**Model Name:** `phase3d_pm25_forecaster_v1`  
**Version:** 1.0.0  
**Release Date:** September 25, 2026  
**Model Type:** Multi-Horizon Direct Gradient Boosted Decision Trees (`HistGradientBoostingRegressor`)  
**Target:** Continuous PM2.5 Concentration ($\mu\text{g/m}^3$) for lead times $t+1\text{h}$ through $t+6\text{h}$  
**Framework:** scikit-learn  
**Repository:** `https://github.com/moominbashir07-ux/weather-final`  

---

## 1. INTENDED USE & SCOPE

### Primary Intended Use
* Forecasting station-level ambient PM2.5 concentrations for horizons 1 through 6 hours ahead across Delhi/NCR continuous ambient air quality monitoring stations.
* Providing the environmental forecasting layer to feed Phase 3E's deterministic commuter decision engine (e.g. evaluating time-dependent transit windows along commuter corridors).

### Out-of-Scope & Prohibited Uses
* **Clinical / Medical Advice:** This model does NOT calculate personalized health risk, organ uptake doses, or medical safety guarantees.
* **Continuous Pollution Surfaces:** This model does NOT perform spatial interpolation, Kriging, or IDW between stations. Forecasts apply specifically to monitored station coordinates.
* **Multi-Day Climatology:** This model is designed strictly for short-term lead times ($t+1\text{h}$ to $t+6\text{h}$); it must not be extrapolated to multi-day horizons.
* **Regulatory Compliance Actions:** Model predictions must not be used in lieu of certified statutory ambient air monitoring telemetry.

---

## 2. TRAINING DATA & CHRONOLOGICAL PARTITIONS

* **Observational Source:** Audited Phase 3B XKDR continuous hourly monitoring dataset ([`backend/datasets/xkdr/station_observations_2020_2024.parquet`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/xkdr/station_observations_2020_2024.parquet)).
* **Geographic Coverage:** 42 monitoring stations across Delhi/NCR (DPCC, IMD, CPCB, UPPCB, IITM, US Embassy).
* **Total Study Records:** $1,732,402$ canonical station-hour rows.
* **Chronological Partitions (No Random Shuffling):**
  * **Training Set:** 2020-01-01 00:00:00 to 2023-12-31 23:59:59 UTC ($1,325,967$ valid horizon-1 samples across 4 full years).
  * **Validation Set:** 2024-01-01 00:00:00 to 2024-06-30 23:59:59 UTC ($170,149$ valid horizon-1 samples, used for early stopping).
  * **Test Set (Firewalled Final Holdout):** 2024-07-01 00:00:00 to 2024-12-31 23:59:59 UTC ($169,624$ valid horizon-1 samples, completely untouched during model training and hyperparameter selection).

---

## 3. FEATURE ARCHITECTURE

Every forecast made at reference time $t$ for lead time $t+h$ uses only information available at $t$:

| Feature Group | Features | Description | Leakage Boundary |
| :--- | :--- | :--- | :--- |
| **Current Observation** | `pm25_t0` | Station PM2.5 concentration at cutoff $t$ | Strictly $\le t$ |
| **Exact Contiguous Lags** | `pm25_lag_1h`, `pm25_lag_2h`, `pm25_lag_3h`, `pm25_lag_6h`, `pm25_lag_12h`, `pm25_lag_24h` | Causal backward lags on exact 1-hour physical grid | $\le t - 1\text{h}$ |
| **Causal Rolling Means** | `pm25_rolling_mean_3h`, `pm25_rolling_mean_6h`, `pm25_rolling_mean_12h`, `pm25_rolling_mean_24h` | Backward rolling averages ($[t - w + 1, t]$) | $\le t$ (No centered or future windows) |
| **Calendar Cyclical** | `hour_of_day_sin`, `hour_of_day_cos`, `day_of_week` | Sine/Cosine diurnal components and day-of-week | Deterministic calendar |
| **Spatial Station Geodesy** | `latitude`, `longitude` | WGS84 coordinates of the monitoring station | Static metadata |
| **Future Weather Forecast** | `temperature_h{h}`, `humidity_h{h}`, `wind_speed_h{h}`, `wind_direction_sin_h{h}`, `wind_direction_cos_h{h}`, `boundary_layer_height_h{h}`, `surface_pressure_h{h}` | Numerical Weather Prediction (NWP) forecast valid at $t+h$ | Open-Meteo NWP forecast issued $\le t$ |

---

## 4. METEOROLOGICAL SOURCE DISTINCTION

1. **Training / Historical Evaluation Mode:**  
   ECMWF ERA5 Atmospheric Reanalysis Archive from Open-Meteo (`archive-api.open-meteo.com/v1/archive`).
2. **Production Inference Mode:**  
   Real-time GFS/ECMWF Numerical Weather Prediction (NWP) forecast from Open-Meteo (`api.open-meteo.com/v1/forecast`).
3. **Circularity Representation:**  
   Wind direction degrees are converted into continuous orthogonal components:  
   $$\text{wind\_direction\_sin} = \sin(\text{radians}(\theta)), \quad \text{wind\_direction\_cos} = \cos(\text{radians}(\theta))$$

---

## 5. MODEL ARCHITECTURE & HYPERPARAMETERS

* **Algorithm:** `HistGradientBoostingRegressor` (Multi-Horizon Direct Forecasting: separate estimators $M_1 \dots M_6$).
* **Hyperparameters:**
  * `max_iter`: 150
  * `learning_rate`: 0.08
  * `max_leaf_nodes`: 31
  * `min_samples_leaf`: 25
  * `early_stopping`: True (`n_iter_no_change`: 10)
  * `random_state`: 42
* **Missingness Handling:** Native learned missingness splits within histogram binning. When sensor telemetry has gaps, the tree routes `NaN` to the optimal partition without synthetic data imputation.
* **Non-Negative Post-Processing:** PM2.5 cannot physically be negative. Predictions are clamped at $\hat{y} = \max(0.0, \hat{y})$. Clamped prediction frequency in the 2024 H2 test set was $\le 0.0006\%$.

---

## 6. MULTI-HORIZON PERFORMANCE (TEST SET: 2024 H2)

Evaluation on $167,621$ to $169,624$ holdout test observations:

| Horizon ($h$) | ML Model MAE ($\mu\text{g/m}^3$) | Persistence MAE ($\mu\text{g/m}^3$) | MAE Reduction | Relative Improvement | ML Model $R^2$ | Persistence $R^2$ | Mean Bias Error |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1h** | **14.14** | 15.15 | $1.01$ | **+6.67%** | **0.9386** | 0.9343 | $-0.28$ |
| **2h** | **20.50** | 23.78 | $3.28$ | **+13.80%** | **0.8840** | 0.8498 | $-0.39$ |
| **3h** | **24.39** | 30.26 | $5.87$ | **+19.40%** | **0.8408** | 0.7618 | $-0.57$ |
| **4h** | **26.92** | 35.47 | $8.55$ | **+24.11%** | **0.8078** | 0.6800 | $-0.80$ |
| **5h** | **28.84** | 39.75 | $10.91$ | **+27.45%** | **0.7801** | 0.6070 | $-1.02$ |
| **6h** | **30.25** | 43.09 | $12.85$ | **+29.81%** | **0.7595** | 0.5454 | $-1.24$ |

*Summary:* The ML model outperforms persistence at **every single horizon**, scaling from a $6.67\%$ reduction in error at 1 hour to nearly $30\%$ reduction at 6 hours.

---

## 7. KNOWN LIMITATIONS & RISK FACTORS

1. **Extreme Winter Smog Peak Underprediction:**  
   During severe episodic pollution events ($\text{PM2.5} > 250\,\mu\text{g/m}^3$), the model exhibits negative bias (e.g. mean bias $-45\,\mu\text{g/m}^3$ at 3h). Tree regressors minimizing mean loss naturally regress toward the conditional mean during unprecedented peaks.
2. **Missing Input Telemetry:**  
   If a monitoring station goes offline for $>24$ hours, lag features become unobserved. While native `NaN` branching allows the model to produce a prediction, accuracy degrades compared to when recent observations are active.
3. **NWP Weather Forecast Uncertainty:**  
   In production, errors in weather forecasts (e.g., mispredicted temperature inversion timing or boundary layer collapse) propagate directly into PM2.5 predictions.
4. **Point Forecasts:**  
   Outputs are currently deterministic point estimates; formal conformal quantile prediction intervals are deferred to post-Phase 3D.
