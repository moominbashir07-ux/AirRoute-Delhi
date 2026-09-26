# MODEL CARD: Delhi/NCR Multi-Horizon PM2.5 Forecasting Engine

## 1. Model Details

- **Model Name:** Delhi Multi-Horizon PM2.5 Direct Estimator (`phase3d_model_h1` through `h6`)
- **Architecture:** Direct Multi-Horizon Gradient Boosted Trees (`sklearn.ensemble.HistGradientBoostingRegressor`)
- **Version:** 1.0.0 (Phase 3D Production Release)
- **Primary Developer:** Environmental Systems Engineering Team
- **License:** Open Academic / Research Non-Commercial
- **Primary Contact:** GitHub Repository `moominbashir07-ux/weather-final`

---

## 2. Intended Use

- **Intended Task:** Forward forecasting of ambient particulate matter ($\text{PM}_{2.5}$) concentrations in $\mu\text{g/m}^3$ at official Continuous Ambient Air Quality Monitoring (CAAQM) stations across Delhi/NCR.
- **Forecast Horizons:** Direct independent models for lead times $h \in \{1, 2, 3, 4, 5, 6\}$ hours ahead of prediction cutoff time $t$.
- **Downstream Consumer:** Deterministic commuter inhalation exposure estimation engine ($M = \sum C_i \times V_E \times \Delta t_i$).
- **Out-of-Scope Uses:**
  - Medical risk diagnosis or clinical health-outcome prediction.
  - Extrapolation beyond the 6-hour horizon window.
  - Hyper-local street canyon / micro-environment air quality estimation without local sensor calibration.

---

## 3. Training and Evaluation Data

### 3.1 Observational Air Quality Data
- **Source:** XKDR India Air Quality Platform (aggregating Central Pollution Control Board / DPCC telemetry).
- **Scope:** 42 active monitoring stations covering the Delhi National Capital Region.
- **Span:** 2020-01-01 00:00:00 UTC through 2024-12-31 23:59:59 UTC (1,732,402 canonical hourly records).
- **Quality Controls:** Native hourly grid, zero synthetic pollutant interpolation, strict negative value rejection, CO normalized from $\text{mg/m}^3$ to $\mu\text{g/m}^3$.

### 3.2 Meteorological Features
- **Historical Training / Retrospective Evaluation:** ECMWF ERA5 Atmospheric Reanalysis via Open-Meteo Historical Archive API (temperature at 2m, relative humidity, wind speed at 10m, circular wind direction vectors $\sin/\cos$, surface pressure, planetary boundary layer height).
- **Live Production Inference:** Open-Meteo Global NWP Forecast Model API (12-hour hourly forecast cycle).

---

## 4. Retrospective Evaluation vs. Live Production Performance

> [!IMPORTANT]
> **Distinction Between Retrospective Evaluation and Live Production:**
> Historical benchmark metrics were evaluated using ECMWF ERA5 reanalysis meteorology. In live production, the models consume forward Numerical Weather Prediction (NWP) forecasts. NWP forecast error introduces additional variance into real-time PM2.5 predictions that is not present in retrospective benchmarks.

### Summary Metrics on Test Partition (2024-07-01 to 2024-12-31):

| Horizon | Test MAE ($\mu\text{g/m}^3$) | Test RMSE ($\mu\text{g/m}^3$) | Test $R^2$ | Persistence Baseline MAE | Improvement over Persistence |
|---|---|---|---|---|---|
| **$t+1\text{h}$** | 12.41 | 21.08 | 0.941 | 15.82 | +21.5% |
| **$t+2\text{h}$** | 17.89 | 29.54 | 0.884 | 24.11 | +25.8% |
| **$t+3\text{h}$** | 22.15 | 36.20 | 0.826 | 30.65 | +27.7% |
| **$t+4\text{h}$** | 25.72 | 41.65 | 0.770 | 36.12 | +28.8% |
| **$t+5\text{h}$** | 28.64 | 46.18 | 0.718 | 40.78 | +29.8% |
| **$t+6\text{h}$** | 31.12 | 49.92 | 0.672 | 44.60 | +30.2% |

---

## 5. Model Features & Inputs

1. **Base Observational Features ($t$):**
   - Current concentration: $\text{PM}_{2.5}(t)$
   - Historical lags: $\text{PM}_{2.5}(t-1\text{h}), (t-2\text{h}), (t-3\text{h}), (t-6\text{h}), (t-12\text{h}), (t-24\text{h})$
   - Causal rolling averages: $\bar{\text{PM}}_{2.5}(3\text{h}), (6\text{h}), (12\text{h}), (24\text{h})$
2. **Cyclical Calendar Features:**
   - $\sin(2\pi \cdot \text{hour} / 24)$, $\cos(2\pi \cdot \text{hour} / 24)$, $\text{day\_of\_week}$
3. **Station Spatial Metadata:**
   - Station latitude and longitude
4. **Target Meteorological Features ($t+h$):**
   - $\text{Temperature}_{t+h}$, $\text{Humidity}_{t+h}$, $\text{WindSpeed}_{t+h}$, $\sin/\cos(\text{WindDirection})_{t+h}$, $\text{BoundaryLayerHeight}_{t+h}$, $\text{SurfacePressure}_{t+h}$

---

## 6. Known Limitations and Risks

1. **Extreme-Event Peak Underprediction:** Tree ensembles inherently regress toward intermediate conditional means and may underestimate sudden, severe pollution spikes (e.g. episodic post-harvest stubble burning or fireworks during Diwali).
2. **NWP Weather Forecast Uncertainty:** Inaccuracies in predicted boundary layer height or wind speed directly impact dispersion estimates.
3. **Station Density & Micro-Environments:** Ambient monitoring stations sample regional urban air masses at rooftop/suburban elevations; they do not measure localized vehicle tailpipe plumes or street-canyon turbulence.
4. **Deterministic Point Predictions:** The model provides conditional point estimates without calibrated probabilistic confidence bounds.
5. **Strict 6-Hour Horizon Ceiling:** Forecast validity degrades sharply beyond 6 hours; requests beyond 6 hours are intentionally rejected by the API.
