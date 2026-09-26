# Phase 3B — Observational Data Quality & Missingness Audit

**Dataset:** XKDR India Air Quality Observational Cache (Delhi NCR)  
**Time Horizon:** January 1, 2020 00:00:00 IST to December 31, 2024 23:00:00 IST ($5$ Full Years)  
**Total Canonical Wide Records:** $1,732,402$ station-hours  
**Total Raw Measurements Ingested:** $9,511,574$ rows across 60 monthly chunks  
**Active Monitoring Stations:** 42 continuous stations (CPCB CAAQM & US Embassy)  

---

## 1. Executive Summary

This report documents the empirical data quality, physical bounds, timestamp integrity, unit conversions, and missingness characteristics of the Phase 3B observational dataset.

The dataset preserves **observational truth**:
* **Zero synthetic interpolation:** Missing pollutant values remain strictly null (`NaN`).
* **Zero forward/backward filling:** Intermittent station dropouts are preserved as gaps.
* **Exact timestamp synchronization:** IST naive timestamps were mapped to timezone-aware IST and converted to UTC, with zero conversion drift across $1,732,402$ records.

---

## 2. Ingestion & Quality Filtering Statistics

| Ingestion Category | Measurement Count | Percentage | Handling Rule |
|---|---|---|---|
| **Total Raw Observational Rows** | $9,511,574$ | $100.0\%$ | Ingested via month-by-month chunked API requests |
| **Negative Values Detected** | $14$ | $<0.0002\%$ | **Rejected & Dropped** (Sensor transmission artifacts / electrical error) |
| **Core Null Records** | $0$ | $0.0\%$ | None detected in primary identification tuples |
| **Duplicate Tuples Detected** | $0$ | $0.0\%$ | Checked on `(station_id, timestamp_utc, parameter)` |
| **Unit Normalization ($\text{CO}$)** | $1,601,008$ | $16.8\%$ | Converted from $\text{mg/m}^3$ to canonical $\mu\text{g/m}^3$ ($\times 1000$) |
| **Retained Clean Measurements** | $9,511,560$ | $99.9998\%$ | Transformed into canonical wide analytical table |

---

## 3. Pollutant Missingness & Statistical Distributions

| Pollutant | Canonical Unit | Observed Hours | Missing Hours | Missingness Rate | Mean | Median | Observed Max | Physical Range Notes |
|---|---|---|---|---|---|---|---|---|
| **$\text{PM}_{2.5}$** | $\mu\text{g/m}^3$ | **1,681,736** | 50,666 | **$2.92\%$** | $99.95$ | $67.00$ | $1,000.00$ | Highly complete ($>97\%$); severe winter smog spikes up to $1000\,\mu\text{g/m}^3$ preserved |
| **$\text{PM}_{10}$** | $\mu\text{g/m}^3$ | **1,609,219** | 123,183 | **$7.11\%$** | $203.47$ | $167.70$ | $1,000.00$ | Mechanical dust and regional coarse particulates |
| **$\text{NO}_2$** | $\mu\text{g/m}^3$ | **1,625,331** | 107,071 | **$6.18\%$** | $38.86$ | $28.41$ | $499.40$ | Vehicular emission marker |
| **$\text{SO}_2$** | $\mu\text{g/m}^3$ | **1,369,041** | 363,361 | **$20.97\%$** | $12.18$ | $9.20$ | $200.00$ | Missingness higher because 8 stations do not equip $\text{SO}_2$ optical sensors |
| **$\text{CO}$** | $\mu\text{g/m}^3$ | **1,601,008** | 131,394 | **$7.58\%$** | $1,317.51$ | $1,030.00$ | $48,280.00$ | Normalized from $\text{mg/m}^3$; traffic congestion indicator |
| **$\text{O}_3$ (Ozone)** | $\mu\text{g/m}^3$ | **1,625,225** | 107,177 | **$6.19\%$** | $30.67$ | $18.63$ | $489.40$ | Photochemical secondary pollutant |

---

## 4. Station Continuity & Coverage Distribution

Across the 42 Delhi stations over the 5-year span ($43,848$ total possible hours):
* **Top Continuous Stations ($>98\%$ Temporal Density):**
  - `site_113` (Shadipur, Delhi - CPCB): $43,636$ observed hours ($99.5\%$ density)
  - `site_115` (NSIT Dwarka, Delhi - CPCB): $43,617$ observed hours ($99.5\%$ density)
  - `site_1430` (Rohini, Delhi - DPCC): $43,490$ observed hours ($99.2\%$ density)
  - `site_1429` (Nehru Nagar, Delhi - DPCC): $43,469$ observed hours ($99.1\%$ density)
  - `site_1421` (Dr. Karni Singh Range, Delhi - DPCC): $43,407$ observed hours ($99.0\%$ density)
  - `site_1562` (Sri Aurobindo Marg, Delhi - DPCC): $43,368$ observed hours ($98.9\%$ density)
  - `site_1422` (Dwarka Sector-8, Delhi - DPCC): $43,357$ observed hours ($98.9\%$ density)
  - `DS1010001` (US Embassy - New Delhi): $43,002$ observed hours ($98.1\%$ density, $100\%$ $\text{PM}_{2.5}$)
* **Stations with Lower Coverage / Commissioned Later:**
  - Several stations were commissioned in late 2020 or 2021; their temporal density within their active operational span remains $>90\%$, but total 5-year hours are lower.
  - Complete station-by-station breakdown is recorded in `coverage_report.csv`.

---

## 5. Timestamp Normalization Audit

* **Source Format:** Naive ISO-8601 strings (e.g. `2024-01-01T00:00:00`).
* **Source Timezone:** Indian Standard Time (IST, UTC+05:30), unadjusted for DST.
* **Target Schema:**
  - `timestamp_ist`: localized timezone-aware datetime (`Asia/Kolkata`).
  - `timestamp_utc`: derived timezone-aware datetime (`UTC`).
* **Independent Verification:**
  $$\Delta = |(\text{timestamp\_ist} \to \text{UTC}) - \text{timestamp\_utc}| = 0.000\,\text{seconds}$$
  Evaluated across all $1,732,402$ wide rows with **zero discrepancies**.

---

## 6. Unit Normalization Audit

* **Criteria Gas ($\text{CO}$):**
  - CPCB monitors report Carbon Monoxide in milligrams per cubic meter ($\text{mg/m}^3$).
  - Atmospheric chemistry models (CAMS) and our feature contracts use micrograms per cubic meter ($\mu\text{g/m}^3$).
  - Transformation applied:
    $$\text{Value}_{\mu\text{g/m}^3} = \text{Value}_{\text{mg/m}^3} \times 1000.0$$
  - Verification: Clean post-conversion mean for Delhi CO is $1,317.51\,\mu\text{g/m}^3$ ($1.32\,\text{mg/m}^3$), which precisely matches published CPCB annual urban averages.

---

## 7. Preservation of Extreme Smog Events

In accordance with Phase 3B hard constraints, **legitimate atmospheric pollution extremes were not clipped or smoothed**:
* Peak winter $\text{PM}_{2.5}$ readings during November episodes reach $800\text{--}1000\,\mu\text{g/m}^3$.
* Rather than treating these as sensor anomalies, they are retained as true physical ground conditions to train robust non-linear models that do not under-predict hazardous air emergencies.
