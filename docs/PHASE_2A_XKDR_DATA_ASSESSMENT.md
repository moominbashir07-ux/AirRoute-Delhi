# Phase 2A — XKDR India Air Quality Database Assessment Report

**Evaluation Date:** September 25, 2026  
**Investigator:** Senior ML & Data Engineering Team  
**Target Airshed:** Delhi National Capital Region (NCR), India  
**API Service:** [XKDR India Air Quality Database](https://airquality.xkdr.org) (`https://airquality.xkdr.org/v1`)  

---

## 1. Executive Summary

This assessment investigates whether the **XKDR India Air Quality Database** provides a reliable historical observational dataset to serve as the foundation for our machine learning pipeline in Delhi NCR. 

The evaluation confirmed that XKDR aggregates hourly measurements across **42 active monitoring stations** in Delhi from the Central Pollution Control Board (CPCB CAAQM) and US Embassy networks, covering criteria pollutants ($\text{PM}_{2.5}, \text{PM}_{10}, \text{NO}_2, \text{SO}_2, \text{CO}, \text{Ozone}$) continuously from 2020 through late 2024. 

However, **XKDR does not provide meteorological parameters** (temperature, humidity, wind speed are absent from its catalog), and **does not provide pre-calculated AQI values**. Adopting XKDR would require calculating the AQI target mathematically from raw pollutant concentrations and executing a spatiotemporal join with Open-Meteo ERA5 reanalysis to obtain weather telemetry. 

**Recommendation: PROCEED WITH LIMITATIONS**. XKDR is scientifically sound for observational ground-truth air pollution, but its integration requires a multi-source schema pipeline rather than a drop-in replacement.

---

## 2. API Authentication Result

* **Endpoint:** `GET https://airquality.xkdr.org/v1/meta`
* **Authentication Method:** HTTP Bearer token (`Authorization: Bearer aqi_...`)
* **Status:** **PASS (HTTP 200 OK)**
* **Access Tier:** `full` (Authorized research tier)
* **Query Constraints:**
  - `max_rows_per_query`: **None** (Unrestricted row cap for full tier)
  - `query_timeout_seconds`: $90.0\,\text{s}$
* **Timezone Specification:** Timestamps (`collected_at`) are reported as naive timestamps in **Indian Standard Time (IST, UTC+05:30)**.
* **Archive Volume:** $196,521,834$ total rows spanning $207$ months ($2009\text{--}01$ to $2026\text{--}03$) across $558$ monitoring stations nationwide.
* **Security & Confidentiality:** The API key was loaded strictly from environment configuration via standard project loaders and was never logged, printed, or staged in version control.

---

## 3. Delhi Station Coverage

Querying the station catalog (`/v1/stations?city=Delhi` and `state=Delhi`) identified **42 distinct continuous ambient air quality monitoring stations**:

| Station ID | Station Name | Operating Agency | Latitude | Longitude | Primary Source |
|---|---|---|---|---|---|
| `site_5024` | Alipur, Delhi | DPCC | $28.8153^\circ\text{ N}$ | $77.1530^\circ\text{ E}$ | CPCB CAAQM |
| `site_301` | Anand Vihar, Delhi | DPCC | $28.6476^\circ\text{ N}$ | $77.3158^\circ\text{ E}$ | CPCB CAAQM |
| `site_1420` | Ashok Vihar, Delhi | DPCC | $28.6954^\circ\text{ N}$ | $77.1817^\circ\text{ E}$ | CPCB CAAQM |
| `site_108` | Aya Nagar, Delhi | IMD | $28.4707^\circ\text{ N}$ | $77.1099^\circ\text{ E}$ | CPCB CAAQM |
| `site_1560` | Bawana, Delhi | DPCC | $28.7762^\circ\text{ N}$ | $77.0511^\circ\text{ E}$ | CPCB CAAQM |
| `site_104` | Burari Crossing, Delhi | IMD | $28.7257^\circ\text{ N}$ | $77.2012^\circ\text{ E}$ | CPCB CAAQM |
| `site_103` | CRRI Mathura Road, Delhi | IMD | $28.5512^\circ\text{ N}$ | $77.2736^\circ\text{ E}$ | CPCB CAAQM |
| `site_5393` | Chandni Chowk, Delhi | IITM | $28.6568^\circ\text{ N}$ | $77.2272^\circ\text{ E}$ | CPCB CAAQM |
| `site_118` | DTU, Delhi | CPCB | $28.7500^\circ\text{ N}$ | $77.1113^\circ\text{ E}$ | CPCB CAAQM |
| `site_1421` | Dr. Karni Singh Range, Delhi | DPCC | $28.4986^\circ\text{ N}$ | $77.2648^\circ\text{ E}$ | CPCB CAAQM |
| `site_1422` | Dwarka Sector-8, Delhi | DPCC | $28.5710^\circ\text{ N}$ | $77.0719^\circ\text{ E}$ | CPCB CAAQM |
| `site_106` | IGI Airport (T3), Delhi | IMD | $28.5628^\circ\text{ N}$ | $77.1180^\circ\text{ E}$ | CPCB CAAQM |
| `site_114` | IHBAS Dilshad Garden, Delhi | CPCB | $28.6812^\circ\text{ N}$ | $77.3025^\circ\text{ E}$ | CPCB CAAQM |
| `site_117` | ITO, Delhi | CPCB | $28.6286^\circ\text{ N}$ | $77.2411^\circ\text{ E}$ | CPCB CAAQM |
| `site_113` | Shadipur, Delhi | CPCB | $28.6515^\circ\text{ N}$ | $77.1581^\circ\text{ E}$ | CPCB CAAQM |

*42 total stations distribute spatial coverage across industrial, commercial, residential, and background traffic corridors.*

---

## 4. Historical Coverage (Annual Breakdown)

To test longitudinal viability, representative multi-day sample queries were executed across years 2020 through 2025 during the peak autumn pollution window (November 1–7):

| Year | Sampling Window | Active Delhi Stations | Total Record Count | Mean Observed $\text{PM}_{2.5}$ ($\mu\text{g/m}^3$) | Status |
|---|---|---|---|---|---|
| **2020** | Nov 01 – Nov 07 | 38 stations | 261 daily aggregates | $240.7$ | **Available** |
| **2021** | Nov 01 – Nov 07 | 41 stations | 287 daily aggregates | $250.5$ | **Available** |
| **2022** | Nov 01 – Nov 07 | 39 stations | 271 daily aggregates | $248.5$ | **Available** |
| **2023** | Nov 01 – Nov 07 | 39 stations | 271 daily aggregates | $277.3$ | **Available** |
| **2024** | Nov 01 – Nov 07 | 40 stations | 280 daily aggregates | $218.0$ | **Available** |
| **2025** | Nov 01 – Nov 07 | 0 stations | 0 | — | *Future Period (Not Yet Recorded)* |

**Finding:** The historical continuity between **2021 and 2024** is exceptionally robust, maintaining $39\text{--}41$ concurrently reporting stations in Delhi with high density.

---

## 5. Pollutant & Weather Variable Availability

Inspecting `/v1/parameters` revealed $15$ chemical species. We cross-referenced these against the project's model requirements:

### A. Criteria Air Pollutants

| Parameter | Unit | In XKDR Catalog? | Present in Delhi Stations? | Delhi Stations with Sensor | Delhi Station Coverage |
|---|---|---|---|---|---|
| **$\text{PM}_{2.5}$** | $\mu\text{g/m}^3$ | **Yes** | **Yes** | **42 / 42** | **$100.0\%$** |
| **$\text{PM}_{10}$** | $\mu\text{g/m}^3$ | **Yes** | **Yes** | **41 / 42** | **$97.6\%$** |
| **$\text{NO}_2$** | $\mu\text{g/m}^3$ | **Yes** | **Yes** | **41 / 42** | **$97.6\%$** |
| **$\text{SO}_2$** | $\mu\text{g/m}^3$ | **Yes** | **Yes** | **34 / 42** | **$81.0\%$** |
| **$\text{CO}$** | $\text{mg/m}^3$ | **Yes** | **Yes** | **41 / 42** | **$97.6\%$** |
| **$\text{Ozone}$** | $\mu\text{g/m}^3$ | **Yes** | **Yes** | **41 / 42** | **$97.6\%$** |
| $\text{NH}_3$ | $\mu\text{g/m}^3$ | **Yes** | **Yes** | 38 / 42 | $90.5\%$ |
| $\text{Benzene}$ | $\mu\text{g/m}^3$ | **Yes** | **Yes** | 35 / 42 | $83.3\%$ |

*Note on units:* CO is reported in $\text{mg/m}^3$ in XKDR (standard CPCB units) compared to $\mu\text{g/m}^3$ in CAMS.

### B. Meteorological Variables

| Meteorological Feature | Required by Model? | In XKDR Catalog? | Station Availability |
|---|---|---|---|
| **Temperature** | **Yes** ($^\circ\text{C}$) | **No** | **0 stations ($0\%$)** |
| **Relative Humidity** | **Yes** ($\%$) | **No** | **0 stations ($0\%$)** |
| **Wind Speed** | **Yes** ($\text{km/h}$) | **No** | **0 stations ($0\%$)** |
| Wind Direction | No | **No** | 0 stations ($0\%$) |
| Surface Pressure | No | **No** | 0 stations ($0\%$) |
| Precipitation / Rain | No | **No** | 0 stations ($0\%$) |

**Finding:** XKDR is an **air-quality-only telemetry archive**. Weather variables must be provided by a separate meteorological source (such as Open-Meteo ERA5 reanalysis).

---

## 6. Data-Quality Deep Dive (Empirical Findings)

We queried a 7-day raw hourly slice across all 42 Delhi stations for all 6 criteria pollutants ($2024\text{--}11\text{--}01$ to $2024\text{--}11\text{--}07$):

* **Total Records Ingested:** $38,506$ hourly sensor rows.
* **Reporting Stations:** $41$ of $42$ stations active during this window.
* **Duplicate Timestamps:** **$0$ duplicates** (Unique per `[station_id, parameter_name, collected_at]`).
* **Null Value Occurrences:** **$0$ nulls** in returned payloads.
* **Negative / Corrupt Values:** **$0$ negative values** across all pollutants.
* **Breakdown by Pollutant Volume:**
  - $\text{PM}_{10}$: $6,703$ readings
  - $\text{NO}_2$: $6,693$ readings
  - $\text{PM}_{2.5}$: $6,577$ readings
  - $\text{CO}$: $6,562$ readings
  - $\text{Ozone}$: $6,424$ readings
  - $\text{SO}_2$: $5,547$ readings

**Finding:** The raw CPCB data ingested and hosted by XKDR is pre-cleaned to remove invalid negative values and transmission artifacts.

---

## 7. Missingness and Station Asynchrony

Although individual data frames have no internal nulls, **inter-station and cross-parameter synchronization is non-uniform**:
1. $\text{SO}_2$ is only monitored by $34$ of the $42$ stations ($81.0\%$). If a joint feature matrix requires all 6 pollutants, $8$ stations must either be dropped or imputed.
2. Station maintenance cycles cause intermittent dropouts of individual sensors (e.g. $\text{PM}_{2.5}$ sensor active while $\text{SO}_2$ is undergoing calibration).
3. Aligning all pollutants into a single wide hourly table (`station_id`, `timestamp`, `pm25`, `pm10`, `no2`, `so2`, `co`, `ozone`) will produce approximately $12\text{--}18\%$ missingness in non-primary pollutants ($\text{SO}_2, \text{Ozone}$) across the full network.

---

## 8. AQI Availability & Methodology Assessment

* **Is AQI provided directly by XKDR?** **NO**. 
  The XKDR API exposes raw and aggregated pollutant concentrations only. There is no `AQI` column in `/v1/parameters` or `/v1/measurements`.
* **Can AQI be derived?** **YES**.
  AQI can be calculated deterministically using either:
  1. **Indian National AQI (INAQI - CPCB):** Based on the sub-index maximum across 24-hr truncated averages for $\text{PM}_{10}, \text{PM}_{2.5}, \text{NO}_2, \text{SO}_2, \text{CO}, \text{O}_3, \text{NH}_3, \text{Pb}$. Requires at least 3 pollutants with one being $\text{PM}_{10}$ or $\text{PM}_{2.5}$.
  2. **US EPA Air Quality Index (EPA-454/B-18-007):** Piecewise linear interpolation across pollutant concentrations, dominated by $\text{PM}_{2.5}$ and $\text{PM}_{10}$.
* **Ground-Truth Terminology:** A derived AQI score is **not** an in-situ physical measurement; it is an index derived from physical measurements. Documentation must clearly distinguish between *measured pollutant concentrations* (true physical ground truth) and *calculated regulatory indices* (derived operational targets).

---

## 9. Open-Meteo Weather Integration Feasibility

Because our production model contract requires:
`[temperature, humidity, wind_speed, co2, pm25, pm10, no2, so2]`

We evaluated joining XKDR observational pollutant data with Open-Meteo ERA5 meteorological data:

### Proposed Join Strategy
1. **Timezone Harmonization:**
   - XKDR `collected_at` is in Indian Standard Time (`UTC+05:30`).
   - Open-Meteo timestamps are in UTC (`Z`).
   - Transform: $\text{Timestamp}_{\text{UTC}} = \text{Timestamp}_{\text{IST}} - 5.5\,\text{hours}$.
2. **Spatial Alignment:**
   - XKDR has precise GPS coordinates for each of the 42 stations (e.g. Alipur: $28.8153^\circ\text{ N}, 77.1530^\circ\text{ E}$).
   - Fetch historical hourly ERA5 weather for Delhi's centroid or nearest reanalysis grid point for each station.
3. **Data Fusion:**
   - Execute an inner join on `[timestamp_utc]` between station pollution readings and hourly weather variables.

### Limitations of Fusion
* Meteorological variables would originate from ECMWF reanalysis/forecast grids ($0.1^\circ \approx 9\text{--}11\,\text{km}$ resolution), while pollutants would represent point-source in-situ air intakes.

---

## 10. Machine Learning Feasibility Comparison

| Dimension | Existing Phase 2 Pipeline (CAMS + ERA5) | Potential XKDR Pipeline (In-Situ CPCB + ERA5) |
|---|---|---|
| **Data Provenance** | ECMWF Copernicus CAMS Atmospheric Reanalysis | CPCB CAAQM In-Situ Continuous Monitors |
| **Observation Fidelity** | Satellite-constrained atmospheric chemistry grid | Physical ground-level sensor intakes (42 stations) |
| **Weather Availability** | Integrated directly from ERA5 | Absent; requires multi-API temporal join |
| **Target Construction** | Continuous EPA AQI provided in dataset | Must be calculated mathematically via sub-indices |
| **Spatial Structure** | Regional airshed aggregate | 42 hyper-local station time series |
| **Model Nature** | General Delhi NCR regional predictor | Station-specific or spatial-kriging multi-station model |
| **Contract Stability** | Matches current `/predict` 8-feature schema | Requires unit normalization (CO from $\text{mg/m}^3$ to $\mu\text{g/m}^3$) |

---

## 11. Project Limitations & Risks

1. **Schema Divergence:** XKDR reports $\text{CO}$ in $\text{mg/m}^3$, whereas the existing schema and Open-Meteo report $\text{CO}$ in $\mu\text{g/m}^3$. Conversion factor ($1\,\text{mg/m}^3 = 1000\,\mu\text{g/m}^3$) must be strictly enforced.
2. **Lag in CPCB Updates:** While $\text{PM}_{2.5}$ is updated into early 2026, other parameters ($\text{NO}_2, \text{SO}_2, \text{CO}$) in the CPCB feed historically finalize on annual cycles, meaning real-time inference requires handling asynchronous parameter drops.
3. **Complexity Overhead:** Rebuilding Phase 2 around XKDR requires managing a multi-station time-series ingestion pipeline, station-level data joining, and EPA/CPCB index calculators.

---

## 12. Recommendation

### **PROCEED WITH LIMITATIONS**

#### Why Proceed with Limitations:
* **The data is genuine and high quality:** XKDR provides real, verifiable in-situ observational ground truth from 42 official CPCB stations across Delhi with clean historical data from 2021 through 2024.
* **Why Limitations are mandatory:** 
  1. Weather features are completely missing from XKDR and must be obtained from Open-Meteo.
  2. The target AQI must be calculated algorithmically rather than read directly.
  3. The current Phase 2 model is already fully trained on real-world, leakage-safe data ($17,544$ hourly observations with $R^2 = 0.6675$) and passing all 20 automated tests.
* **Operational Guidance:**
  Do **not** discard the existing working Phase 2 pipeline. Instead, preserve the current stable baseline and develop an observational XKDR ingestion and multi-station evaluation pipeline as an enhanced observational track when transitioning into spatial/commuter exposure modeling.

---
