# Phase 3B — XKDR Observational Data Ingestion & Station Cache: Final Report

**Execution Date:** September 25, 2026  
**Pipeline Author:** Senior Data & ML Infrastructure Engineer  
**Dataset Version:** `xkdr_delhi_2020_2024_v1`  
**Storage Path:** `backend/datasets/xkdr/station_observations_2020_2024.parquet`  

---

## 1. Status

```text
COMPLETE
```

All acceptance criteria have been achieved. The dataset has been ingested, normalized, quality-audited, independently verified from disk, and tested.

---

## 2. Data Source & Provenance

* **Source:** Observational air-quality measurements from the Central Pollution Control Board (CPCB CAAQM) continuous monitoring network and the US Embassy monitor, retrieved via the **XKDR India Air Quality Database API** (`https://airquality.xkdr.org`).
* **Scientific Classification:** **Observational air-quality measurements**. (Per project constraints, these are physical field measurements subject to local sensor calibration and optical variance; they are never termed infallible "ground truth").
* **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).

---

## 3. Geographic Scope & Selection Rule

* **Exact Selection Rule:** All monitoring stations registered with `state_name == "Delhi"` in the CPCB CAAQM and US Embassy registry.
* **Geographic Coverage:** National Capital Territory of Delhi, India ($28.47^\circ\text{ N}$ to $28.82^\circ\text{ N}$, $77.05^\circ\text{ E}$ to $77.32^\circ\text{ E}$).
* **Total Discovered Stations:** **42 stations** (41 CPCB stations with `city == "Delhi"` + 1 US Embassy station with `city == "New Delhi"`).
* **Cross-Border NCR Monitors:** Stations outside Delhi state boundaries (e.g. Noida, Gurugram, Ghaziabad) were excluded from this initial Delhi catalog to prevent administrative geographic drift.

---

## 4. Date Range

* **Ingested Temporal Window (IST):** `2020-01-01 00:00:00 IST` to `2024-12-31 23:30:00 IST`
* **Ingested Temporal Window (UTC):** `2019-12-31 18:30:00 UTC` to `2024-12-31 18:00:00 UTC`
* **Duration:** Exactly $5$ full calendar years ($60$ continuous months, $43,848$ total hours).

---

## 5. Station Statistics

* **Total Registered Delhi Stations:** **42**
* **Successfully Ingested Stations:** **42 ($100.0\%$)**
* **Incomplete Stations:** **0** (All 42 stations have verified records in the dataset)
* **Failed Stations:** **0**
* **Active Station Span Distribution:**
  - $36$ stations active across $>90\%$ of the 5-year span.
  - $6$ stations commissioned during 2020–2021 active across $>90\%$ of their post-commissioning span.

---

## 6. Pollutant Statistics

| Pollutant | Stations Monitoring | Total Observed Hours | Missingness Rate | Canonical Unit | Primary Source Network |
|---|---|---|---|---|---|
| **$\text{PM}_{2.5}$** | **42 / 42 ($100\%$)** | $1,681,736$ | $2.92\%$ | $\mu\text{g/m}^3$ | CPCB CAAQM + US Embassy |
| **$\text{PM}_{10}$** | **41 / 42 ($97.6\%$)** | $1,609,219$ | $7.11\%$ | $\mu\text{g/m}^3$ | CPCB CAAQM |
| **$\text{NO}_2$** | **41 / 42 ($97.6\%$)** | $1,625,331$ | $6.18\%$ | $\mu\text{g/m}^3$ | CPCB CAAQM |
| **$\text{SO}_2$** | **34 / 42 ($81.0\%$)** | $1,369,041$ | $20.97\%$ | $\mu\text{g/m}^3$ | CPCB CAAQM |
| **$\text{CO}$** | **41 / 42 ($97.6\%$)** | $1,601,008$ | $7.58\%$ | $\mu\text{g/m}^3$ | CPCB CAAQM (converted from $\text{mg/m}^3$) |
| **$\text{O}_3$** | **41 / 42 ($97.6\%$)** | $1,625,225$ | $6.19\%$ | $\mu\text{g/m}^3$ | CPCB CAAQM |

---

## 7. Dataset Statistics

* **Total Raw Ingested Records:** $9,511,574$ rows across 60 monthly Parquet chunks
* **Total Canonical Wide Station-Hours:** **$1,732,402$ rows**
* **Total Clean Data Cells:** $10,394,412$ potential pollutant observation cells
* **Duplicate Count on `(station_id, timestamp_utc)`:** **$0$** (Strict unique key enforcement)
* **Negative Values Detected & Dropped:** **$14$** ($<0.0002\%$ of raw feed)
* **Missing Value Imputation:** **ZERO IMPUTATION APPLIED** (All missing values remain strictly `NaN` to preserve empirical observational truth)
* **Analytical Storage Footprint:** $26.94\,\text{MB}$ (`station_observations_2020_2024.parquet` with Snappy compression)

---

## 8. Unit Conversions

* **Carbon Monoxide ($\text{CO}$):**
  - Source Unit: $\text{mg/m}^3$ (milligrams per cubic meter)
  - Canonical Target Unit: $\mu\text{g/m}^3$ (micrograms per cubic meter)
  - Conversion Rule: $\text{Value}_{\mu\text{g/m}^3} = \text{Value}_{\text{mg/m}^3} \times 1000.0$
  - Records Converted: $1,601,008$ rows
  - Post-conversion Verification: Mean $= 1,317.51\,\mu\text{g/m}^3$ ($1.32\,\text{mg/m}^3$), conforming to official CPCB annual reports.
* **All Other Pollutants ($\text{PM}_{2.5}, \text{PM}_{10}, \text{NO}_2, \text{SO}_2, \text{O}_3$):**
  - Source units verified as $\mu\text{g/m}^3$; passed through without transformation.

---

## 9. Timestamp Handling

* **Source Reporting:** Naive timestamp in Indian Standard Time (IST, UTC+05:30).
* **Storage Schema:**
  1. `timestamp_ist`: localized timezone-aware datetime (`datetime64[ns, Asia/Kolkata]`).
  2. `timestamp_utc`: converted timezone-aware datetime (`datetime64[ns, UTC]`).
* **Validation Rule Enforced:**
  $$\text{timestamp\_utc} + 5.5\,\text{hours} == \text{timestamp\_ist}$$
  Verified with $100\%$ zero-drift compliance across all $1,732,402$ rows.

---

## 10. Data Limitations

1. **Weather Parameters Missing:** XKDR does not track meteorological variables ($\text{temperature}$, $\text{humidity}$, $\text{wind speed}$). Downstream forecasting models must merge these from Open-Meteo ERA5 / NWP reanalysis.
2. **Asynchronous $\text{SO}_2$ Coverage:** 8 stations do not equip optical sulfur dioxide sensors.
3. **Sensor Maintenance Dropouts:** Periodic maintenance causes unaligned gaps of 1–6 hours across individual monitors.

---

## 11. Files Created

1. `backend/ml_model/xkdr_ingestion.py` — Multi-year month-by-month chunked ingestion pipeline.
2. `backend/ml_model/validate_xkdr_cache.py` — Independent disk re-loader and verification auditor.
3. `backend/datasets/xkdr/station_catalog.csv` — Deterministic catalog of 42 Delhi stations.
4. `backend/datasets/xkdr/station_observations_2020_2024.parquet` — Canonical wide observational analytical dataset ($1,732,402$ rows, 26.94 MB).
5. `backend/datasets/xkdr/data_dictionary.json` — Formal machine-readable data dictionary.
6. `backend/datasets/xkdr/dataset_metadata.json` — Provenance and pipeline metadata.
7. `backend/datasets/xkdr/quality_report.json` — Comprehensive empirical quality audit summary.
8. `backend/datasets/xkdr/coverage_report.csv` — Station-by-station missingness and coverage table.
9. `backend/tests/test_xkdr_ingestion.py` — Automated tests for ingestion components.
10. `backend/tests/test_xkdr_data_quality.py` — Automated tests for data quality and independent verification.
11. `docs/PHASE_3B_DATA_QUALITY.md` — Detailed data quality and missingness documentation.
12. `docs/PHASE_3B_FINAL_REPORT.md` — This final report document.

---

## 12. Files Modified

1. `.gitignore` — Added `backend/datasets/xkdr/raw/` and `backend/datasets/xkdr/*.parquet` to keep multi-million-row binary artifacts out of Git history while preserving reproducibility.

---

## 13. Tests

```text
Phase 3B Dedicated Tests: 10 passed / 0 failed
Full Backend Test Suite: 34 passed / 0 failed
```

---

## 14. Existing Phase 2 System Integrity

* Production Model Artifacts (`best_model.pkl`, `scaler.pkl`, `metrics.pkl`): **UNCHANGED**
* Phase 2 Dataset (`real_aqi_dataset.csv`): **UNCHANGED**
* Production Endpoints (`/predict`, `/health`, `/metrics`, `/forecast`): **UNCHANGED**
* Phase 2 ML & API Smoke Tests (20 tests): **ALL 20 PASSING**

---

## 15. Security

* XKDR API Key was retrieved strictly from the environment.
* The API key was never logged, printed, or staged into git.
* `.env` remains untracked and clean.

---

## 16. Phase 3C Readiness

The observational dataset is **fully verified, validated, and ready** for:
```text
Phase 3C — Corridor Geometry & Exposure Feature Engineering
```
(No Phase 3C work has been initiated).
