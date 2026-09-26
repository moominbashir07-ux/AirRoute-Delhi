# PHASE 3C IMPLEMENTATION PLAN — CORRIDOR GEOMETRY & EXPOSURE FEATURE ENGINEERING

**Document Status:** PROPOSED ARCHITECTURE & SPECIFICATION  
**Phase Execution Status:** `PHASE_3C_PLAN = CREATED` | `PHASE_3C_IMPLEMENTATION = NOT STARTED`  
**Prerequisites:** Phase 3B Final Audit Gate PASSED (`PHASE_3B_AUDIT = PASS`)

---

## 1. OBJECTIVE & SCOPE BOUNDARIES

The objective of Phase 3C is to design the deterministic spatial geometry, corridor discretization, and station-to-corridor feature engineering contracts required to support spatial environmental forecasting in Phase 3D.

### Strict Scope Boundaries
* **NO ML Model Training:** No scikit-learn/LightGBM/XGBoost training during Phase 3C.
* **NO Forecasting Implementation:** No inference pipelines or forecast generation.
* **NO Exposure Dose Calculations:** Physiological minute-ventilation / intake dose calculations deferred to Phase 3E.
* **NO Commute Recommendations or Route Optimization:** Routing APIs and recommendations deferred to Phase 3E/3F.
* **NO Frontend Implementation:** UI remains untouched.
* **NO AWS Infrastructure Provisioning:** No Lambda, DynamoDB, or cloud resources created.
* **NO Black-Box Spatial Interpolation:** Continuous kriging, IDW (Inverse Distance Weighting), or thin-plate spline surfaces are strictly prohibited. The system must maintain transparent, explainable point-to-station associations.
* **Phase 2 Backward Compatibility:** Existing `/predict` and `/forecast` endpoints and model artifacts (`best_model.pkl`, `scaler.pkl`) remain untouched and protected.

---

## 2. COMPONENT 1 — COORDINATE & SPATIAL BOUNDS VALIDATION

### Coordinate System & Geodesy
* **Geodetic Datum:** WGS84 (EPSG:4326) standard ellipsoidal coordinates.
* **Format:** Decimal degrees (`float64`).
* **Latitude Range (Delhi NCR Bounding Box):** $[28.20^\circ\text{N}, 28.95^\circ\text{N}]$
* **Longitude Range (Delhi NCR Bounding Box):** $[76.80^\circ\text{E}, 77.55^\circ\text{E}]$

### Validation Rules
1. Coordinates must parse as valid IEEE 754 floats.
2. Coordinates falling strictly outside $[-90, 90]$ latitude or $[-180, 180]$ longitude raise a `GeometryValidationError("Coordinates out of physical bounds")`.
3. Coordinates falling outside the Delhi NCR operational envelope trigger an explicit `NCRBoundingWarning` or `OutOfOperationalCoverageException`.
4. Station coordinates must be immutable and validated against the audited `station_catalog.csv`.

---

## 3. COMPONENT 2 — CORRIDOR REPRESENTATION

A corridor represents a commuter's traversal path between an origin and destination across Delhi NCR.

### Data Structures (Pure Python / Typed Pydantic)
```python
class GeoPoint(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class CorridorSegment(BaseModel):
    segment_index: int = Field(..., ge=0)
    start_point: GeoPoint
    end_point: GeoPoint
    midpoint: GeoPoint
    length_meters: float = Field(..., ge=0.0)
    bearing_degrees: float = Field(..., ge=0.0, lt=360.0)

class Corridor(BaseModel):
    corridor_id: str
    origin: GeoPoint
    destination: GeoPoint
    total_distance_meters: float
    segments: List[CorridorSegment]
```

### Discretization Policy
* Straight-line or waypoint-interpolated paths are discretized into equidistant intervals (e.g., $500\text{m}$ to $1,000\text{m}$ resolution) to capture local air quality gradients without oversampling.
* Each segment is represented by its geometric midpoint:
  $$\text{lat}_{\text{mid}} = \frac{\text{lat}_1 + \text{lat}_2}{2}, \quad \text{lon}_{\text{mid}} = \frac{\text{lon}_1 + \text{lon}_2}{2}$$
  *(For sub-kilometer segments, Euclidean planar approximation for midpoint produces $<0.01\text{m}$ distortion).*

---

## 4. COMPONENT 3 — STATION MATCHING (HAVERSINE DISTANCE)

Station matching maps any geographic point (such as a corridor segment midpoint) to the nearest operational continuous ambient monitoring station.

### Haversine Formula Specification
Given two points $(\phi_1, \lambda_1)$ and $(\phi_2, \lambda_2)$ in radians, with Earth mean radius $R = 6,371,000.0\text{ meters}$:

$$\Delta \phi = \phi_2 - \phi_1, \quad \Delta \lambda = \lambda_2 - \lambda_1$$
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1 - a}\right)$$
$$d = R \cdot c$$

### Rationale for Haversine
* **Metric Accuracy:** Within Delhi NCR ($\sim 50\text{km} \times 50\text{km}$), Haversine has $<0.1\%$ error compared to Vincenty ellipsoidal formulas while avoiding iterative convergence failures.
* **Deterministic & Zero Dependencies:** Operates natively in standard Python `math` library without requiring external GDAL, GEOS, or heavy C extensions.

---

## 5. COMPONENT 4 — STATION-TO-CORRIDOR MAPPING

For each segment $i$ of a corridor:
1. Compute the Haversine distance $d(m_i, s_j)$ from segment midpoint $m_i$ to every station $s_j \in \mathcal{S}$ ($|\mathcal{S}| = 42$).
2. Identify the primary matched station:
   $$s^* = \arg\min_{s_j \in \mathcal{S}} d(m_i, s_j)$$
3. Identify the secondary (backup) matched station:
   $$s_{\text{backup}} = \arg\min_{s_j \in \mathcal{S} \setminus \{s^*\}} d(m_i, s_j)$$
4. Assign:
   * `nearest_station_id`: String identifier (e.g. `site_113`)
   * `distance_to_station_meters`: Float
   * `backup_station_id`: String identifier (for offline redundancy)
   * `backup_distance_meters`: Float

---

## 6. COMPONENT 5 — SPATIAL FEATURE CONTRACT

The spatial feature vector represents the static and dynamic spatial attributes of the segment-station pair:

| Feature Name | Type | Range / Unit | Description |
| :--- | :---: | :---: | :--- |
| `segment_latitude` | `float64` | $[28.2, 28.95]$ | Discretized segment midpoint latitude |
| `segment_longitude` | `float64` | $[76.8, 77.55]$ | Discretized segment midpoint longitude |
| `station_latitude` | `float64` | $[28.2, 28.95]$ | Nearest station latitude |
| `station_longitude` | `float64` | $[76.8, 77.55]$ | Nearest station longitude |
| `distance_to_station_km` | `float64` | $[0.0, 50.0]$ | Haversine distance to assigned station |
| `corridor_bearing_deg` | `float64` | $[0.0, 360.0)$ | Azimuth of travel direction along segment |
| `station_relative_bearing_deg` | `float64` | $[0.0, 360.0)$ | Azimuth from segment midpoint to station |
| `is_within_acceptable_radius` | `int8` | $\{0, 1\}$ | Indicator if distance $\le 10.0\text{ km}$ threshold |

---

## 7. COMPONENT 6 — TEMPORAL OBSERVATIONAL FEATURE CONTRACT

For forecasting future PM2.5 in Phase 3D, each station observation history will provide backward-looking lag features:

| Feature Name | Type | Description |
| :--- | :---: | :--- |
| `pm25_lag_1h` | `float64` | Observed PM2.5 concentration at station at $t - 1\text{ hour}$ ($\mu\text{g/m}^3$) |
| `pm25_lag_2h` | `float64` | Observed PM2.5 concentration at station at $t - 2\text{ hours}$ ($\mu\text{g/m}^3$) |
| `pm25_lag_3h` | `float64` | Observed PM2.5 concentration at station at $t - 3\text{ hours}$ ($\mu\text{g/m}^3$) |
| `pm25_lag_6h` | `float64` | Observed PM2.5 concentration at station at $t - 6\text{ hours}$ ($\mu\text{g/m}^3$) |
| `pm25_rolling_mean_6h` | `float64` | Backward rolling average over $[t - 6\text{h}, t - 1\text{h}]$ |
| `pm25_rolling_mean_24h`| `float64` | Backward rolling average over $[t - 24\text{h}, t - 1\text{h}]$ |
| `hour_of_day_sin` | `float64` | Cyclical time feature: $\sin(2\pi \cdot \text{hour} / 24)$ |
| `hour_of_day_cos` | `float64` | Cyclical time feature: $\cos(2\pi \cdot \text{hour} / 24)$ |
| `day_of_week` | `int8` | Day of week index $[0\text{--}6]$ |

---

## 8. COMPONENT 7 — DATA LEAKAGE PREVENTION & TEMPORAL BOUNDARIES

Strict temporal barriers must be enforced during feature construction:
1. **Prediction Time Barrier ($T_0$):** At inference time $T_0$, only observations with timestamps $t \le T_0$ may be utilized.
2. **Lag Construction:** All rolling aggregates and lag features are calculated strictly using **closed-left, open-right** or **closed-past** windows:
   $$\text{Window}(T_0) = \{ t \mid t \le T_0 \}$$
   No future timestamps ($t > T_0$) can ever appear in rolling window calculations.
3. **No Target Leakage:** Targets for future horizons ($T_0 + 1\text{h}, T_0 + 2\text{h}, \dots, T_0 + 6\text{h}$) must be strictly excluded from the input feature vector.
4. **Chronological Train/Test Partitioning:** In Phase 3D, cross-validation must use strict temporal splits (`TimeSeriesSplit`), never random k-fold shuffling.

---

## 9. COMPONENT 8 — MISSING-STATION & STALE OBSERVATION BEHAVIOR

When querying a matched station at inference time:
1. **Staleness Threshold:** If the latest observation is older than $3\text{ hours}$, the station is marked `STALE`.
2. **Missing Sensor Threshold:** If PM2.5 at the station is `NaN` at $T_0$, the station is marked `SENSOR_OFFLINE`.
3. **Distance Cutoff Threshold:** If the nearest station is $>12.0\text{ km}$ from the segment midpoint, spatial proximity confidence is classified as `LOW_CONFIDENCE`.
4. **Fallback Hierarchy:**
   * *Tier 1 (Primary Nearest Station):* Used if fresh ($\le 3\text{h}$ old) and non-null.
   * *Tier 2 (Secondary Nearest Station):* If primary is stale or offline, smoothly fallback to $s_{\text{backup}}$, logging an audit trail flag `fallback_station_used=True`.
   * *Tier 3 (City-Wide Regional Baseline):* If both primary and backup stations are offline, use the median of all active Delhi monitors at $T_0$, logging `confidence="REGIONAL_ESTIMATE"`.
   * *No Silent Fills:* The fallback status must always be transparently returned in the output metadata.

---

## 10. COMPONENT 9 — GEOMETRY VALIDATION TEST SUITE SPECIFICATION

Phase 3C implementation will require a comprehensive test module: `tests/test_corridor_geometry.py`.

### Mandatory Test Cases
1. `test_identical_origin_and_destination`: Returns a single-point corridor with zero length and valid station match.
2. `test_very_short_corridor`: Traversal of $<100\text{ meters}$ correctly produces 1 segment without division by zero.
3. `test_long_corridor_ncr_crossing`: Cross-city route ($>40\text{ km}$) produces multiple segments and smoothly transitions across station assignment boundaries.
4. `test_out_of_bounds_coordinates`: Latitudes/longitudes outside $[-90, 90]$ or $[-180, 180]$ raise validation errors.
5. `test_equidistant_tie_breaking`: Deterministic tie-breaking by lexicographical `station_id` when two stations have identical distance.
6. `test_haversine_accuracy`: Validates calculated distances against known reference geodetic baselines (e.g. Connaught Place to India Gate).
7. `test_station_catalog_integrity`: Ensures all 42 stations have valid non-null coordinates within Delhi NCR bounding box.

---

## 11. COMPONENT 10 — ZERO BLACK-BOX SPATIAL INTERPOLATION

### Architecture Rule
* **No Continuous Surface Approximations:** Continuous 2D interpolation (e.g. IDW, Kriging, RBF) creates false impressions of precision in urban street canyons where air pollution varies discontinuously due to traffic and topography.
* **Discrete Segment Matching:** Every corridor segment explicitly cites its governing monitoring station, the Euclidean/Haversine distance to that station, and data latency.
* **Explainability:** When a commuter asks why a segment has an AQI of 280, the system answers: *"Based on direct observations from Anand Vihar (DPCC) monitor, located 1.4 km east of your corridor segment."*

---

## 12. PHASE 3C INPUT / OUTPUT SCHEMAS

### Input Schema: `CorridorDiscretizationRequest`
```json
{
  "corridor_id": "commute_home_to_work_001",
  "origin": {
    "latitude": 28.5355,
    "longitude": 77.2600
  },
  "destination": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "discretization_step_meters": 1000.0
}
```

### Output Schema: `CorridorGeometryResponse`
```json
{
  "corridor_id": "commute_home_to_work_001",
  "total_distance_meters": 10540.2,
  "segment_count": 11,
  "segments": [
    {
      "segment_index": 0,
      "midpoint": {"latitude": 28.5392, "longitude": 77.2581},
      "length_meters": 1000.0,
      "bearing_degrees": 335.4,
      "primary_station": {
        "station_id": "site_119",
        "station_name": "Sirifort, Delhi - CPCB",
        "distance_meters": 2150.4,
        "is_within_acceptable_radius": true
      },
      "backup_station": {
        "station_id": "site_109",
        "station_name": "Lodhi Road, Delhi - IMD",
        "distance_meters": 4320.1
      }
    }
  ]
}
```

---

## 13. BACKWARD COMPATIBILITY & REGRESSION PROTECTION

* **Existing Files Untouched:** `backend/ml_model/best_model.pkl`, `scaler.pkl`, `metrics.pkl`, `real_aqi_dataset.csv`.
* **Existing Endpoints Untouched:** `/predict`, `/forecast`, `/aqi-history`, `/train`.
* **Test Isolation:** Phase 3C code and tests will reside in isolated modules (`backend/ml_model/corridor_geometry.py` and `backend/tests/test_corridor_geometry.py`), guaranteeing zero regression to existing Phase 1 and Phase 2 test suites.

---

## 14. AUTHORIZATION STATUS

* **Phase 3C Plan:** **CREATED & ACCEPTED**
* **Phase 3C Implementation:** **NOT STARTED** (Requires explicit human review and authorization).
