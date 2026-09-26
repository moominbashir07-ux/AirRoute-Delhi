# PHASE 3C — CORRIDOR GEOMETRY & EXPOSURE FEATURE ENGINEERING SPECIFICATION

**Phase Status:** COMPLETE  
**Repository:** `https://github.com/moominbashir07-ux/weather-final`  
**Module Code:**  
* [`backend/ml_model/corridor_geometry.py`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/ml_model/corridor_geometry.py)
* [`backend/ml_model/temporal_features.py`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/ml_model/temporal_features.py)
* [`backend/ml_model/phase3c_pipeline.py`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/ml_model/phase3c_pipeline.py)

---

## 1. OBJECTIVE & SYSTEM CONTEXT

Phase 3C establishes the deterministic spatial and temporal feature-engineering layer that connects physical transit corridors across the National Capital Region (NCR) to the audited historical observational monitoring network (Phase 3B).

```
Commuter Corridor (Origin & Destination)
                 ↓
  Discretization into 1 km Geodesic Segments
                 ↓
  Deterministic Nearest-Station Matching (Haversine, ≤10 km)
                 ↓
  Station Observational History (Phase 3B Parquet)
                 ↓
  Contiguous Backward Lags + Causal Rolling Features
                 ↓
  Ready for Phase 3D PM2.5 Forecasting Engine
```

> [!IMPORTANT]
> **Scientific & Operational Scope Boundary:**
> Phase 3C does **not** perform pollution forecasting, commuter route optimization, dose calculations, health scoring, or road-network navigation. It does **not** generate continuous pollution surfaces or apply spatial interpolation (IDW, Kriging, Splines). All relationships are discrete, transparent segment-to-monitor associations.

---

## 2. INPUT DATASETS & PROVENANCE

* **Observational Time Series:** [`backend/datasets/xkdr/station_observations_2020_2024.parquet`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/xkdr/station_observations_2020_2024.parquet)
  * 42 stations across Delhi NCR.
  * 1,732,402 canonical hourly rows from 2020-01-01 to 2024-12-31.
  * Native hourly sampling rate (0 count of 30-min intervals).
* **Station Catalog:** [`backend/datasets/xkdr/station_catalog.csv`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/xkdr/station_catalog.csv)
  * Exact station IDs, coordinates, names, and operational providers (DPCC, IMD, CPCB, UPPCB, IITM, US Embassy).

---

## 3. COORDINATE SYSTEM & GEODESY

* **Datum / CRS:** WGS84 (EPSG:4326) ellipsoidal geographic coordinates.
* **Coordinate Validation:**
  * Coordinates must parse as IEEE 754 floats.
  * Range limits strictly enforced: $-90.0 \le \text{latitude} \le 90.0$, $-180.0 \le \text{longitude} \le 180.0$.
  * `NaN`, `+Inf`, and `-Inf` explicitly raise validation errors.
  * Optional NCR Operational Envelope check: $[28.20^\circ\text{N}, 28.95^\circ\text{N}]$, $[76.80^\circ\text{E}, 77.55^\circ\text{E}]$.
  * Coordinates are never silently altered, shifted, or rounded before distance calculation.

---

## 4. HAVERSINE DISTANCE FORMULA & EARTH RADIUS

Great-circle distance between two points $(\phi_1, \lambda_1)$ and $(\phi_2, \lambda_2)$ in radians is calculated using:

$$\Delta \phi = \phi_2 - \phi_1, \quad \Delta \lambda = \lambda_2 - \lambda_1$$
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1 - a}\right)$$
$$d = R \cdot c$$

* **Earth Mean Radius:** $R = 6,371.0\text{ km}$ (standard spherical mean radius).
* **Properties:**
  * $d \ge 0.0\text{ km}$.
  * For identical coordinates: $d \equiv 0.0\text{ km}$.
  * Verified against known landmarks: Connaught Place to India Gate $= 2.40\text{ km}$.

---

## 5. CORRIDOR REPRESENTATION & DISCRETIZATION

### Corridor Definition
A corridor is defined by its endpoints:
```json
{
  "origin": {"latitude": 28.6315, "longitude": 77.2167},
  "destination": {"latitude": 28.4950, "longitude": 77.0895}
}
```
* **Distinction:** This is a **geodesic corridor representation**, representing the spatial swath between origin and destination, not road-network turn-by-turn geometry.

### Deterministic Corridor ID
Corridor IDs are generated using a deterministic SHA256 digest of normalized coordinates and step configuration:
$$\text{Digest} = \text{SHA256}(\text{"orig\_28.63150\_77.21670|dest\_28.49500\_77.08950|step\_1.00"})[:12]$$
Output format: `corr_5a8f4c91b2e3`.

### Segmentation Policy
* **Default Step:** $\Delta s = 1.0\text{ km}$.
* **Number of Segments:** $N = \max\left(1, \lceil \text{Total Distance} / \Delta s \rceil\right)$.
* **Midpoint Representation:** Each segment $i \in [0, N-1]$ contains start, end, and geometric midpoint coordinates.
* **Bearing ($\theta$):**
  $$\theta = \text{atan2}\left(\sin(\Delta \lambda)\cos(\phi_2), \cos(\phi_1)\sin(\phi_2) - \sin(\phi_1)\cos(\phi_2)\cos(\Delta \lambda)\right)$$
  Normalized strictly to $[0.0, 360.0)^\circ$ with $0^\circ = \text{North}, 90^\circ = \text{East}, 180^\circ = \text{South}, 270^\circ = \text{West}$.
* **Edge Cases:**
  * *Origin == Destination:* Produces a single segment ($N=1$) with length $0.0\text{ km}$, bearing $0.0^\circ$, flagged `is_single_point = True`.
  * *Short corridor ($<\Delta s$):* Produces exactly 1 segment with length equal to the total distance.

---

## 6. STATION SPATIAL MATCHING & TIE-BREAKING

For each corridor segment midpoint:
1. Compute vectorized Haversine distance to all 42 stations in the spatial index.
2. **Deterministic Tie-Breaking:**
   Candidates are sorted primarily by distance ascending; secondary sort key is `station_id` ascending lexicographically:
   $$\text{sort\_order} = \text{lexsort}((\text{station\_ids}, \text{distances\_km}))$$
3. **Threshold Enforcement (`MAX_STATION_DISTANCE_KM = 10.0`):**
   * If $\min(d) \le 10.0\text{ km} \implies \text{match\_status} = \text{"VALID\_MATCH"}$.
   * If $\min(d) > 10.0\text{ km} \implies \text{match\_status} = \text{"NO\_VALID\_STATION"}$ (nearest station details are masked to `None` to prevent silent misassignment; candidate ID preserved in audit metadata).
   * If coordinates are invalid $\implies \text{"INVALID\_COORDINATES"}$.
4. **Backup Station:** The second-nearest station ($s_{\text{backup}}$) and its distance are recorded for offline resilience.

---

## 7. ZERO SPATIAL INTERPOLATION GUARANTEE

The system strictly avoids:
* Inverse Distance Weighting (IDW)
* Ordinary / Universal Kriging
* Radial Basis Function (RBF) Splines
* Continuous pollution raster grid generation

**Scientific Justification:** Urban air pollution in Delhi is heavily modulated by micro-scale aerodynamic street canyons, localized point sources (brick kilns, waste burning), and vehicular density. Continuous 2D mathematical interpolations create artificial spatial smoothness and false confidence. Instead, every segment transparently exposes its actual governing sensor station and distance.

---

## 8. TEMPORAL FEATURE ENGINEERING

Temporal features are derived directly from the canonical hourly time series of each monitoring station.

### Contiguous-Lag Requirement (Zero Nearest-Time Substitution)
* For a forecast made at time $t$, lag features require observations at exact backward physical intervals:
  $$\text{pm25\_lag\_1h} = \text{PM2.5}(t - 1\text{ hour})$$
  $$\text{pm25\_lag\_2h} = \text{PM2.5}(t - 2\text{ hours})$$
  $$\text{pm25\_lag\_3h} = \text{PM2.5}(t - 3\text{ hours})$$
  $$\text{pm25\_lag\_6h} = \text{PM2.5}(t - 6\text{ hours})$$
  $$\text{pm25\_lag\_12h} = \text{PM2.5}(t - 12\text{ hours})$$
  $$\text{pm25\_lag\_24h} = \text{PM2.5}(t - 24\text{ hours})$$
* **Implementation:** Each station time series is reindexed onto a strict 1-hour regular grid. If $t - 1\text{h}$ is missing, $\text{pm25\_lag\_1h}$ is strictly `NaN`. The pipeline never substitutes an observation from $t - 2\text{h}$ or $t - 3\text{h}$ into the 1-hour lag slot.

### Causal Rolling Historical Means
* Rolling statistics use right-closed, backward-looking windows:
  $$\text{pm25\_rolling\_mean\_3h} = \frac{1}{|W_3|} \sum_{\tau \in [t - 2\text{h}, t]} \text{PM2.5}(\tau)$$
  $$\text{pm25\_rolling\_mean\_6h} = \frac{1}{|W_6|} \sum_{\tau \in [t - 5\text{h}, t]} \text{PM2.5}(\tau)$$
  $$\text{pm25\_rolling\_mean\_12h} = \frac{1}{|W_{12}|} \sum_{\tau \in [t - 11\text{h}, t]} \text{PM2.5}(\tau)$$
  $$\text{pm25\_rolling\_mean\_24h} = \frac{1}{|W_{24}|} \sum_{\tau \in [t - 23\text{h}, t]} \text{PM2.5}(\tau)$$
* **Minimum Periods Policy:** Requires at least $50\%$ valid observations within the window (e.g., $\ge 3$ valid hours for a 6h window), otherwise returns `NaN`.
* **Zero Future Windows:** No centered or forward-looking rolling windows.

### Cyclical Calendar Features
* $\text{hour\_of\_day\_sin} = \sin(2\pi \cdot \text{hour} / 24)$
* $\text{hour\_of\_day\_cos} = \cos(2\pi \cdot \text{hour} / 24)$
* $\text{day\_of\_week} \in [0, 6]$ ($0 = \text{Monday}, 6 = \text{Sunday}$)

---

## 9. DATA LEAKAGE PREVENTION & AUDIT PROOF

To prevent future target information from leaking into training or inference features:
1. **Prediction Horizon Barrier ($T_0$):** Features at time $T_0$ use only observations from $t \le T_0$.
2. **Mathematical Invariance Proof:**
   A dedicated test (`test_mandatory_future_observation_invariance`) constructs two datasets identical up to $t$, with an extreme divergence at $t+1$ (e.g. $50\,\mu\text{g/m}^3$ vs $999\,\mu\text{g/m}^3$). It asserts that all lag, rolling, and cyclical features at $t$ remain bit-identical between both datasets.

---

## 10. GENERATED ARTIFACTS & DATA SCHEMAS

All Phase 3C deliverables reside in [`backend/datasets/phase3c/`](file:///c:/Users/moomi/OneDrive/Desktop/sites/aqi-predictor/backend/datasets/phase3c/):

| File Name | Format | Rows | Columns | Description |
| :--- | :---: | :---: | :---: | :--- |
| `corridor_segments.parquet` | Parquet | 162 | 11 | Discretized 1 km segments across 10 benchmark transit corridors. |
| `segment_station_mapping.parquet` | Parquet | 162 | 16 | Segment-to-station matches, distances, backup stations, and match status. |
| `station_temporal_features.parquet` | Parquet | 1,732,402 | 22 | 5-year station observations with exact backward lags and rolling features. |
| `feature_metadata.json` | JSON | 17 keys | N/A | Feature catalog specifying formulas, types, sources, and missingness behavior. |
| `phase3c_metadata.json` | JSON | 1 document | N/A | Full dataset provenance, geodetic parameters, and distance statistics. |

---

## 11. LIMITATIONS & OPERATIONAL CONSTRAINTS

1. **Nearest-Station Approximation:** The nearest monitor may be up to 10 km away. While it accurately represents regional urban air masses, hyper-local street-level emissions (e.g. next to a diesel generator) will not be captured.
2. **Monitoring Station Sparsity:** South-West Delhi (Dwarka) and rural NCR perimeters have fewer continuous monitoring stations than central New Delhi.
3. **Data Gaps in Lags:** When a monitoring station experiences an outage (e.g., during routine recalibration), lag features correctly become `NaN` rather than imputed. Downstream models must handle missing feature entries gracefully.
4. **Geodesic Path Assumption:** Segments follow great-circle arcs rather than exact road turnings.

---

## 12. VERIFICATION & TEST SUMMARY

* **Phase 3C Dedicated Test Suite:** **23 / 23 PASSED**
  * Geometry & Validation: 11 tests
  * Station Spatial Matching & Tie-breaking: 6 tests
  * Temporal Feature Lags & Windows: 4 tests
  * Leakage Invariance: 2 tests
* **Full Backend Test Suite:** **60 / 60 PASSED** in 4.63s
* **Phase 2 Regression Diff:** **Zero lines changed** (`best_model.pkl`, `scaler.pkl`, `metrics.pkl` intact).
