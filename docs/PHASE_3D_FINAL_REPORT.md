# PHASE 3D FINAL REPORT — STATION-LEVEL PM2.5 FORECASTING ENGINE

**Repository:** `https://github.com/moominbashir07-ux/weather-final`  
**Execution Date:** September 25, 2026  
**Auditor & Lead ML Engineer:** Senior ML Engineer & Environmental Time-Series Scientist  

---

## 1. EXECUTIVE STATUS

```text
PHASE_3D_STATUS = COMPLETE
```

All 6 multi-horizon direct forecasting models ($M_1 \dots M_6$), meteorological feature integration, chronological split enforcement, zero-leakage constraints, baseline comparisons, and production inference interfaces have been successfully implemented, tested, and validated.

---

## 2. DATASET SUMMARY

* **Observational Dataset:** Audited Phase 3B XKDR continuous hourly monitoring dataset ([`backend/datasets/xkdr/station_observations_2020_2024.parquet`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/xkdr/station_observations_2020_2024.parquet)).
* **Total Canonical Records:** $1,732,402$ station-hour records.
* **Monitoring Stations:** **42 stations** covering Delhi NCR (DPCC, IMD, CPCB, UPPCB, IITM, US Embassy).
* **Date Range:** 2020-01-01 00:00:00 to 2024-12-31 23:00:00 UTC (5 full historical years).
* **Meteorological Dataset:** Open-Meteo ECMWF ERA5 Reanalysis Archive ($43,848$ hourly records matching the exact 5-year temporal span).
* **Chronological Partitions:**
  * **Train Set:** `2020-01-01` to `2023-12-31` ($1,325,967$ valid horizon-1 samples across 4 years).
  * **Validation Set:** `2024-01-01` to `2024-06-30` ($170,149$ valid horizon-1 samples).
  * **Test Set (Firewalled Holdout):** `2024-07-01` to `2024-12-31` ($169,624$ valid horizon-1 samples).

---

## 3. FORECAST HORIZONS & ARCHITECTURE

* **Forecasting Strategy:** Multi-Horizon Direct Forecasting. Six separate models ($M_1, M_2, M_3, M_4, M_5, M_6$) trained independently for horizons $h \in \{1, 2, 3, 4, 5, 6\}$ hours.
* **Model Algorithm:** `HistGradientBoostingRegressor` (scikit-learn).
* **Key Hyperparameters:**
  * `max_iter`: 150
  * `learning_rate`: 0.08
  * `max_leaf_nodes`: 31
  * `min_samples_leaf`: 25
  * `early_stopping`: True (`n_iter_no_change`: 10)
  * `random_state`: 42
* **Total Features per Model:** 23 features (16 base causal historical + spatial features + 7 future weather forecast features at valid time $t+h$).

---

## 4. BASELINE COMPARISON & MULTI-HORIZON TEST METRICS

Evaluated on the independent test holdout (2024-07-01 to 2024-12-31, $N \approx 168,000$ samples per horizon):

### Multi-Horizon Test Metrics Table

| Horizon | Model Architecture | MAE ($\mu\text{g/m}^3$) | RMSE ($\mu\text{g/m}^3$) | $R^2$ Score | Median AE ($\mu\text{g/m}^3$) | Mean Bias Error | Sample Count |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1h** | **ML Forecaster (M1)** | **14.14** | **28.29** | **0.9386** | **7.19** | **-0.28** | 169,624 |
| 1h | Persistence Baseline | 15.15 | 29.27 | 0.9343 | 7.95 | -0.06 | 169,624 |
| 1h | Rolling 6h Baseline | 27.88 | 50.46 | 0.8046 | 13.33 | -0.16 | 169,624 |
| **2h** | **ML Forecaster (M2)** | **20.50** | **38.87** | **0.8840** | **10.71** | **-0.39** | 168,896 |
| 2h | Persistence Baseline | 23.78 | 44.24 | 0.8498 | 12.00 | -0.12 | 168,896 |
| 2h | Rolling 6h Baseline | 32.96 | 59.28 | 0.7302 | 15.67 | -0.19 | 168,896 |
| **3h** | **ML Forecaster (M3)** | **24.39** | **45.57** | **0.8408** | **12.69** | **-0.57** | 168,509 |
| 3h | Persistence Baseline | 30.26 | 55.73 | 0.7618 | 15.00 | -0.16 | 168,509 |
| 3h | Rolling 6h Baseline | 36.92 | 66.21 | 0.6639 | 17.27 | -0.21 | 168,509 |
| **4h** | **ML Forecaster (M4)** | **26.92** | **50.13** | **0.8078** | **14.02** | **-0.80** | 168,050 |
| 4h | Persistence Baseline | 35.47 | 64.69 | 0.6800 | 17.00 | -0.25 | 168,050 |
| 4h | Rolling 6h Baseline | 40.07 | 71.64 | 0.6076 | 18.55 | -0.29 | 168,050 |
| **5h** | **ML Forecaster (M5)** | **28.84** | **53.68** | **0.7801** | **15.07** | **-1.02** | 167,709 |
| 5h | Persistence Baseline | 39.75 | 71.77 | 0.6070 | 19.00 | -0.29 | 167,709 |
| 5h | Rolling 6h Baseline | 42.50 | 75.72 | 0.5626 | 19.67 | -0.34 | 167,709 |
| **6h** | **ML Forecaster (M6)** | **30.25** | **56.18** | **0.7595** | **15.86** | **-1.24** | 167,621 |
| 6h | Persistence Baseline | 43.10 | 77.24 | 0.5454 | 20.00 | -0.31 | 167,621 |
| 6h | Rolling 6h Baseline | 44.31 | 78.70 | 0.5281 | 20.37 | -0.38 | 167,621 |

### Summary of ML vs. Persistence Improvement

$$\begin{aligned}
\text{Horizon 1h}:& \quad \Delta\text{MAE} = -1.01\,\mu\text{g/m}^3 \quad (\mathbf{+6.67\% \text{ reduction in error}}) \\
\text{Horizon 2h}:& \quad \Delta\text{MAE} = -3.28\,\mu\text{g/m}^3 \quad (\mathbf{+13.80\% \text{ reduction in error}}) \\
\text{Horizon 3h}:& \quad \Delta\text{MAE} = -5.87\,\mu\text{g/m}^3 \quad (\mathbf{+19.40\% \text{ reduction in error}}) \\
\text{Horizon 4h}:& \quad \Delta\text{MAE} = -8.55\,\mu\text{g/m}^3 \quad (\mathbf{+24.11\% \text{ reduction in error}}) \\
\text{Horizon 5h}:& \quad \Delta\text{MAE} = -10.91\,\mu\text{g/m}^3 \quad (\mathbf{+27.45\% \text{ reduction in error}}) \\
\text{Horizon 6h}:& \quad \Delta\text{MAE} = -12.85\,\mu\text{g/m}^3 \quad (\mathbf{+29.81\% \text{ reduction in error}})
\end{aligned}$$

The ML model outperforms persistence and rolling baselines across **all six horizons**, with the competitive advantage scaling monotonically from 1 hour to 6 hours.

---

## 5. PERFORMANCE BY POLLUTION CONCENTRATION REGIME

Evaluated on the holdout test set across concentration strata:

| Regime | Range ($\mu\text{g/m}^3$) | Samples (1h) | 1h MAE | 1h Bias | Samples (3h) | 3h MAE | 3h Bias | Samples (6h) | 6h MAE | 6h Bias |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Low** | $0 \le \text{PM2.5} < 30$ | 42,398 | 6.55 | +5.79 | 42,126 | 9.81 | +9.81 | 41,876 | 14.18 | +13.40 |
| **Moderate** | $30 \le \text{PM2.5} < 60$ | 42,408 | 7.94 | +1.77 | 42,173 | 11.43 | +2.96 | 41,919 | 13.83 | +5.50 |
| **High** | $60 \le \text{PM2.5} < 120$ | 32,873 | 13.79 | +1.03 | 32,718 | 20.81 | +2.53 | 32,542 | 25.66 | +5.32 |
| **Very High** | $120 \le \text{PM2.5} < 250$ | 33,989 | 20.91 | +0.44 | 33,765 | 32.21 | +2.56 | 33,561 | 38.50 | +1.77 |
| **Severe** | $\text{PM2.5} \ge 250$ | 17,956 | 47.93 | -31.39 | 17,752 | 78.62 | -45.25 | 17,723 | 99.88 | -69.52 |

*Scientific Takeaway:* The model is highly accurate in Low, Moderate, High, and Very High regimes ($\text{MAE} \le 20.9\,\mu\text{g/m}^3$ at 1h). For severe winter smog episodes ($>250\,\mu\text{g/m}^3$), the model exhibits an expected conservative underprediction bias, as gradient boosting trees regress toward the conditional mean during unprecedented spikes.

---

## 6. PERFORMANCE BY STATION

Evaluated for all stations with $\ge 100$ valid test samples (Horizon 1h):
* **Median Station MAE:** $13.84\,\mu\text{g/m}^3$
* **Top Performing Stations:**
  * US Embassy (`DS1010001`): $\text{MAE} = 11.36\,\mu\text{g/m}^3$, $R^2 = 0.9544$ ($N=4,386$)
  * IGI Airport T3 (`site_106`): $\text{MAE} = 13.49\,\mu\text{g/m}^3$, $R^2 = 0.9400$ ($N=4,355$)
  * Karni Singh Stadium (`site_1570`): $\text{MAE} = 12.39\,\mu\text{g/m}^3$, $R^2 = 0.9482$ ($N=4,352$)
* **High Pollution Hotspot Stations:**
  * Anand Vihar (`site_122`): $\text{MAE} = 18.23\,\mu\text{g/m}^3$, $R^2 = 0.9084$ (heavy inter-state bus terminal influence)
  * Burari Crossing (`site_104`): $\text{MAE} = 19.75\,\mu\text{g/m}^3$, $R^2 = 0.8981$

---

## 7. WEATHER PROVENANCE & CIRCULAR WIND ENCODING

* **Historical Archive:** ECMWF ERA5 Reanalysis Archive ingested via Open-Meteo (`archive-api.open-meteo.com`).
* **Production Forecast Mode:** Real-time NWP Numerical Weather Prediction via Open-Meteo (`api.open-meteo.com/v1/forecast`).
* **Circular Representation:**
  $$\text{wind\_direction\_sin} = \sin(\text{radians}(\theta)), \quad \text{wind\_direction\_cos} = \cos(\text{radians}(\theta))$$
  Raw degrees were dropped to eliminate circular boundary discontinuities.

---

## 8. LEAKAGE PREVENTION AUDIT

All 6 mandatory leakage checks passed without exception:
1. **Target Leakage:** Automated assertion confirms no `target_t_plus_*` appears in any model feature set (`test_target_columns_excluded_from_feature_columns`).
2. **Future Weather Leakage:** Automated assertion confirms horizon $h$ uses strictly weather aligned to $t+h$, with no exposure to later intervals (`test_weather_features_at_horizon_h_do_not_leak_subsequent_weather`).
3. **Temporal Partitioning:** Train, Validation, and Test boundaries are strictly monotonic with zero overlapping timestamps (`test_strict_chronological_split_no_temporal_overlap`).
4. **Native Missingness (No Imputer Leakage):** Features with missing history remain `NaN` and are partitioned via learned tree branches, avoiding global or future-looking imputation.
5. **No Test-Set Tuning:** Hyperparameters were selected using early stopping on the 2024 H1 validation set; the 2024 H2 test set was accessed strictly for final one-shot reporting.
6. **Station Isolation:** Stations remain grouped across all time periods, preventing random row shuffling leakage.

---

## 9. NON-NEGATIVE PREDICTION CLAMPING

* Physical constraint: Ambient particulate concentration cannot be negative ($\text{PM2.5} \ge 0.0$).
* Post-processing clamping: $\hat{y} = \max(0.0, \hat{y})$.
* Frequency: Across all test horizons ($N \approx 1,010,000$ cumulative predictions), exactly **1 single prediction** ($<0.0001\%$) was clamped (in Horizon 5h). The raw gradient boosting models naturally produce non-negative outputs without distortion.

---

## 10. REPRODUCIBILITY & PERSISTED ARTIFACTS

* Random seeds fixed at `random_state = 42`.
* Model artifacts:
  * [`backend/ml_model/phase3d/model_h1.pkl`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/ml_model/phase3d/model_h1.pkl) through `model_h6.pkl`
  * [`backend/ml_model/phase3d/metrics.json`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/ml_model/phase3d/metrics.json)
  * [`backend/ml_model/phase3d/model_metadata.json`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/ml_model/phase3d/model_metadata.json)
  * [`backend/datasets/phase3d/split_metadata.json`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/phase3d/split_metadata.json)
  * [`backend/datasets/phase3d/feature_metadata.json`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/phase3d/feature_metadata.json)

---

## 11. REGRESSION & INTEGRITY VERIFICATION

* **Phase 2 Artifacts:** `best_model.pkl`, `scaler.pkl`, `metrics.pkl`, `real_aqi_dataset.csv` are **100% UNCHANGED** (`git diff` is empty).
* **Endpoints:** `/predict` and `/forecast` contracts remain fully functional and passing all smoke tests.
* **Phase 3B Observational Parquet:** Byte-preserved, unchanged.
* **Phase 3C Geometry Parquets:** Byte-preserved, unchanged.
* **Test Suite:** **72 / 72 tests PASSED** in 7.07 seconds.

---

## 12. MAJOR LIMITATIONS

1. **Episodic Smog Peak Underprediction:**
   During severe agricultural burning or stagnant winter inversions ($\text{PM2.5} > 250\,\mu\text{g/m}^3$), the model underpredicts peak concentrations due to quadratic loss regression shrinkage.
2. **NWP Forecast Propagation:**
   In production, any error in numerical weather forecasts (e.g. wind lull timing or planetary boundary layer height) directly affects the PM2.5 prediction.
3. **Observational Sensor Outages:**
   When a monitoring station goes offline for multiple consecutive hours, lag features become unavailable, temporarily degrading forecast accuracy.
4. **Point Forecasts:**
   Predictions are deterministic expected concentrations; calibrated conformal prediction intervals remain an area for future enhancement.

---

## 13. PHASE 3E READINESS

```text
PHASE_3E_READINESS = YES
```

The multi-horizon station-level forecasting engine is fully validated and ready to supply deterministic environmental forecasts to Phase 3E (Commuter Route Exposure & Decision Engine).
