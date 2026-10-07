# Phase 4C Step 2 — Dataset Qualification & Known Project Test Cases Report

**Document Version**: 1.0.0  
**Date**: 2026-10-04  
**Status**: **QUALIFICATION REPORT — COMPLETED**  
**Target System Architecture**: PostgreSQL 16.15 + PostGIS 3.4.2 (Database: `telangana_road_db`)  
**Production Database Status**: **UNMUTATED (0 database mutations)**  
**Historical Baseline Preserved**: 7,463 source records | 3,844 projects | 4,360 tenders | 4,360 contracts | 1,997 contractors | 100% lineage  

---

> [!IMPORTANT]
> **SAFETY & INTEGRITY MANDATE**:
> In accordance with Phase 4 safety rules, **zero live records were inserted or modified** in the production database. All qualification and entity-resolution evaluations were conducted in **Safe Discovery Mode** against the catalog metadata discovered in Phase 4C Step 1 (`data/live_discovery/telangana_open_data_catalog.json`).

---

## 1. Executive Summary

This report delivers the dataset qualification audit and entity-resolution validation for **Phase 4C Step 2**. Out of **364 datasets** (comprising **7,254 distributions**) discovered on the **Telangana Open Data Portal (`data.telangana.gov.in`)**, **61 datasets** were identified as domain-relevant to municipal infrastructure, road statistics, and local government works.

To rigorously validate dataset qualification and entity resolution rules, two real-world project test cases were audited across both the **historical database baseline** and the **live Telangana Open Data Portal catalog**:
1. **Test Case A — Uppal Elevated Corridor**
2. **Test Case B — IIT Hyderabad Project**

---

## 2. Dataset Qualification Audit Matrix

Out of the 61 domain-relevant datasets identified on `data.telangana.gov.in`, datasets were evaluated against 12 project-level contract fact requirements:

| Discovered Dataset Name | Publisher | Distributions | Contains Project Title? | Contains Road Name? | Contains Tender / Ref ID? | Contains Contractor Name? | Contains Award Value? | Contains Geometries / Lat-Lng? | Qualification Status for Project Matching |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| **Roads and Drainage Network in ULBs** | Municipal Admin & Urban Dev | 1 | ❌ NO | ⚠️ Aggregated | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **STATISTICAL SUMMARY ONLY** |
| **Roads (Length in KM)** | Transport, Roads & Buildings | 1 | ❌ NO | ⚠️ Aggregated | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **STATISTICAL SUMMARY ONLY** |
| **Roads under Gram Panchayats** | Panchayat Raj & Rural Dev | 1 | ❌ NO | ⚠️ Aggregated | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **STATISTICAL SUMMARY ONLY** |
| **Classification of Roads** | Panchayat Raj & Rural Dev | 2 | ❌ NO | ⚠️ District-level | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **DISTRICT KILOMETER AGGREGATE ONLY** |
| **Infrastructure in Urban Local Bodies** | Municipal Admin & Urban Dev | 1 | ❌ NO | ⚠️ ULB-level | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **MUNICIPAL INFRASTRUCTURE AGGREGATE** |
| **Mission Kakatiya Phase 1-4** | Irrigation & CAD Dept | 4 | ⚠️ Work Title | ❌ NO | ⚠️ Package No | ❌ NO | ⚠️ Sanction Amt | ❌ NO | **QUALIFIED FOR TANK/IRRIGATION WORKS** |
| **Gram Panchayat Offices Lat-Lng** | Panchayat Raj & Rural Dev | 1 | ❌ NO | ❌ NO | ❌ NO | ❌ NO | ❌ NO | ✅ Lat/Lng | **SPATIAL BOUNDARY REFERENCE ONLY** |
| **GHMC Circle Offices & Toilets Lat-Lng** | Greater Hyderabad Muni Corp | 12 | ❌ NO | ❌ NO | ❌ NO | ❌ NO | ❌ NO | ✅ Lat/Lng | **CIVIC AMENITY SPATIAL REFERENCE** |

### Key Qualification Finding:
The datasets published on the **Telangana Open Data Portal (`data.telangana.gov.in`)** primarily consist of **high-level administrative statistics, district-wise road length aggregations, and civic amenity spatial point locations**. They **do NOT expose granular procurement contract records, tender reference numbers, awarded contractor legal names, or project completion schedules** for major state/national highway capital projects.

---

## 3. Known Project Test Cases

---

### 3.1 Test Case A — Uppal Elevated Corridor

#### A. Project Profile & Context
The **Uppal Elevated Corridor** (also known as the *Uppal-Narapally Elevated Corridor* or *NH-163 Uppal Flyover*) is a major 6.2 km, 6-lane elevated corridor project along National Highway 163 (NH-163) connecting Uppal Junction to Narapally in Hyderabad/Medchal-Malkajgiri district. The project is executed under the Ministry of Road Transport & Highways (MoRTH) / National Highways Authority of India (NHAI) in coordination with the Telangana Roads & Buildings (R&B) Department.

#### B. Historical Database Audit
The historical PostgreSQL database (`telangana_road_db` / `telangana_road_intel.db`) was queried across all primary entity tables using multiple search patterns (`"Uppal"`, `"Elevated"`, `"Corridor"`, `"Narapally"`, `"NH-163"`, `"NH 163"`):

| Target Historical Table | Query Filter / Variant | Records Found | Existing Entity Details |
| :--- | :--- | :-: | :--- |
| `projects` | `project_name LIKE '%Uppal%'` | 40 | Municipal maintenance & street repair works in Uppal circle (GHMC / Metro access roads). |
| `projects` | `project_name LIKE '%Elevated%'` | 2 | Hyderabad-Bengaluru Elevated Rail Corridor RITES feasibility projects. |
| `projects` | `project_name LIKE '%NH-163%'` | 10 | Highway widening & maintenance packages along NH-163. |
| `projects` | `project_name LIKE '%Uppal%' AND project_name LIKE '%Elevated%'` | **0** | **Exact merged entity not present in historical database.** |
| `project_locations` | `city = 'UPPAL' OR locality = 'UPPAL'` | 20 | Municipal location points in Uppal Circle, Telangana. |
| `tenders` | `title LIKE '%Uppal%' AND title LIKE '%Elevated%'` | **0** | No matching tender record found in historical baseline. |
| `contracts` | `contract_reference LIKE '%Uppal%'` | **0** | No matching contract record found in historical baseline. |
| `authorities` | `name LIKE '%MoRTH%' OR name LIKE '%NHAI%'` | 15 | National Highways Authority of India & R&B NH Circle records. |
| `project_identifiers` | `identifier_value LIKE '%NH-163%'` | 10 | National Highway 163 identifier records. |
| `source_records` | `external_url LIKE '%cppp%'` | 7,463 | CPPP historical lineage records. |

#### C. Live Source Audit (Telangana Open Data Portal)
All 364 datasets and 7,254 distributions in `data/live_discovery/telangana_open_data_catalog.json` were searched for variants (`"Uppal Elevated Corridor"`, `"Uppal corridor"`, `"Uppal elevated"`, `"elevated corridor Uppal"`, `"Narapally"`, `"NH-163"`):

* **Datasets Discovered**: 0 matches
* **Distributions Discovered**: 0 matches
* **Field Evidence**: Neither dataset titles, descriptions, metadata keywords, nor distribution CSV headers contain entries for the Uppal Elevated Corridor project.

#### D. Official Declaration
> **"No match found in currently inspected Telangana Open Data sources."**

#### E. Entity-Resolution Demonstration Matrix

```
Historical Project:
   [Not Present as Single Merged Record in Historical DB]
          ↓
Government Dataset Record (Telangana Open Data):
   [NO MATCHING RECORD FOUND on data.telangana.gov.in]
          ↓
Matching Fields Evaluated:
   - Project Name / Title: ❌ NO MATCH
   - Road Name / Number: ❌ NO MATCH
   - Authority / Department: ❌ NO MATCH
   - District / Location: ❌ NO MATCH
   - Tender Reference ID: ❌ NO MATCH
   - Contractor Name: ❌ NO MATCH
          ↓
Confidence Classification:
   NO MATCH (Confidence Score: 0.00)
          ↓
Proposed Canonical Project Entity:
   UNMATCHED — Requires ingestion from MoRTH / NHAI CPPP Official Sources
```

#### F. Technical Evaluation Criteria
* **Historical Presence**: Partial (Generic municipal road repairs in Uppal circle exist; exact 6.2 km elevated corridor capital project is absent).
* **Live-Source Presence**: ABSENT from Telangana Open Data Portal.
* **Matching Fields**: None.
* **Confidence Level**: **NO MATCH (0.00)**.
* **Source Dataset**: N/A (No dataset contains this record).
* **Missing Information**: Tender ID, Tender Reference Number, Awarded Contract Value, Contractor Legal Name, Appointed Date, Physical Progress %.
* **Safe for Future Automated Matching?**: **NO** (Cannot perform automated matching until official MoRTH/NHAI dataset is ingested).
* **Additional Official Source Required**:
  1. **GoI Central Public Procurement Portal (CPPP `eprocure.gov.in` via `data.gov.in` API)** — Filtered by `Organisation: National Highways Authority of India / MoRTH`, `Work: Uppal Elevated Corridor / NH-163`.
  2. **MoRTH Bhoomi Rashi Portal (`bhoomirashi.gov.in`)** — National Highway 163 Land Acquisition & Project Sanction Register.
  3. **Telangana Roads & Buildings Department (NH Wing)** — Administrative Sanction Orders for NH-163 corridor works.

---

### 3.2 Test Case B — IIT Hyderabad Project

#### A. Project Profile & Context
The **IIT Hyderabad Project** refers to the capital infrastructure, civil construction, building packages, and campus access road network for the **Indian Institute of Technology Hyderabad (IITH)** located at Kandi, Sangareddy District, Telangana.

#### B. Historical Database Audit
The historical PostgreSQL database (`telangana_road_db` / `telangana_road_intel.db`) was queried across all primary entity tables using multiple search patterns (`"IIT"`, `"IIT Hyderabad"`, `"Indian Institute of Technology"`, `"IITH"`, `"Kandi"`, `"Sangareddy"`):

| Target Historical Table | Query Filter / Variant | Records Found | Existing Entity Details |
| :--- | :--- | :-: | :--- |
| `projects` | `project_id = 203` | 1 | `"Correlated Solutions Inc VIC-3D Software with Mandatory Accessories / IITH/CE/MKM/2023/S/T003"` (Lab software procurement by IITH Stores & Purchase; non-civil work). |
| `projects` | `project_id = 2122` | 1 | `"Development of greenery in the Central Median from Gachibowli flyover to IIIT Junction, circle-XI, West Zone, GHMC"` (Road median greenery near IIIT Gachibowli; distinct institution). |
| `projects` | `project_name LIKE '%IIT%' AND category = 'ROAD'` | 0 | **No civil road/campus construction project for IIT Hyderabad campus.** |
| `tenders` | `title LIKE '%IIT%'` | 4 | Laboratory equipment & MES maintenance tenders at IIT Hyderabad / Pashan. |
| `contracts` | `contractor_id` for IITH tenders | 4 | Equipment suppliers (Correlated Solutions Inc). |
| `authorities` | `name LIKE '%Indian Institute of Technology%'` | 1 | `"Indian Institute of Technology - Hyderabad||Stores and Purchase - IIT Hyderabad"`. |
| `project_locations` | `district = 'SANGAREDDY'` | 1 | Administrative district location entry for Sangareddy, Telangana. |
| `project_identifiers` | `identifier_value LIKE '%IITH%'` | 1 | Tender reference `IITH/CE/MKM/2023/S/T003`. |

#### C. Live Source Audit (Telangana Open Data Portal)
All 364 datasets and 7,254 distributions in `data/live_discovery/telangana_open_data_catalog.json` were searched for variants (`"IIT Hyderabad"`, `"Indian Institute of Technology Hyderabad"`, `"IIT-H"`, `"IITH"`, `"Kandi"`, `"Sangareddy"`):

* **Datasets Discovered**: 0 matches
* **Distributions Discovered**: 0 matches
* **Field Evidence**: Neither dataset titles, descriptions, metadata keywords, nor distribution CSV headers contain entries for IIT Hyderabad campus road or civil infrastructure projects.

#### D. Official Declaration
> **"No match found in currently inspected Telangana Open Data sources."**

#### E. Entity-Resolution Demonstration Matrix

```
Historical Project:
   [Project ID 203: IITH Stores Equipment Procurement (Lab Software)]
   [Project ID 2122: GHMC IIIT Junction Median Greenery Work]
          ↓
Government Dataset Record (Telangana Open Data):
   [NO MATCHING RECORD FOUND on data.telangana.gov.in]
          ↓
Matching Fields Evaluated:
   - Project Name / Title: ❌ NO MATCH (Open Data portal lacks IITH civil works)
   - Road Name / Number: ❌ NO MATCH
   - Authority / Department: ❌ NO MATCH
   - District / Location: ❌ NO MATCH (Sangareddy district absent in catalog datasets)
   - Tender Reference ID: ❌ NO MATCH
   - Contractor Name: ❌ NO MATCH
          ↓
Confidence Classification:
   NO MATCH (Confidence Score: 0.00)
          ↓
Proposed Canonical Project Entity:
   UNMATCHED — Requires ingestion from CPWD / IITH Estate Official Sources
```

#### F. Technical Evaluation Criteria
* **Historical Presence**: Partial (Equipment procurement & nearby IIIT Junction greenery exist; major campus civil/road infrastructure is absent).
* **Live-Source Presence**: ABSENT from Telangana Open Data Portal.
* **Matching Fields**: None.
* **Confidence Level**: **NO MATCH (0.00)**.
* **Source Dataset**: N/A (No dataset contains this record).
* **Missing Information**: Civil Works Tender ID, CPWD Package Reference, Awarded Contract Value, Main Civil Contractor (e.g. Shapoorji Pallonji / L&T / NCC), Appointed Date, Physical Progress %.
* **Safe for Future Automated Matching?**: **NO** (Cannot perform automated matching until official CPWD / IITH eProcurement dataset is ingested).
* **Additional Official Source Required**:
  1. **GoI Central Public Procurement Portal (CPPP `eprocure.gov.in` via `data.gov.in` API)** — Filtered by `Organisation: Central Public Works Department (CPWD) Hyderabad Circle` or `Indian Institute of Technology Hyderabad`, location: `Sangareddy / Kandi`.
  2. **IIT Hyderabad Construction & Estate Management Portal (`iith.ac.in/tenders`)** — Official campus development tenders.

---

## 4. Entity-Resolution Safety & Guardrail Rules

Based on the dataset qualification findings from Test Cases A & B, the following automated entity-resolution safety guardrails are established:

1. **Strict Rejection of False Positive Soft-Matches**:
   * A project title containing `"IIIT Junction"` MUST NOT be merged with `"IIT Hyderabad Campus Infrastructure"`.
   * A project title containing `"Uppal Metro Station Road"` MUST NOT be merged with `"Uppal Elevated Corridor (NH-163)"`.

2. **Mandatory Minimum Confidence Thresholds**:
   * **Score $\ge 0.85$**: Automatic linkage permitted **ONLY IF** Exact Tender ID, Exact Tender Ref, or Strong Trigram Match + District align.
   * **Score $0.60 - 0.84$**: Route to `project_match_review_queue`.
   * **Score $< 0.60$**: Treat as New Unmatched Entity.

3. **Zero Data Fabrication Policy**:
   * If a live open data dataset lacks tender numbers or contractor names, those fields MUST remain `NULL`.

---

## 5. Production Database Baseline Verification

Before and after database audits verify that **zero database mutations** occurred during this qualification phase:

| Table Name | Historical Baseline Rows | Post-Qualification Rows | Mutation Count | Audit Result |
| :--- | :-: | :-: | :-: | :--- |
| **`source_records`** | 7,463 | 7,463 | 0 | ✅ **UNMUTATED** |
| **`projects`** | 3,844 | 3,844 | 0 | ✅ **UNMUTATED** |
| **`tenders`** | 4,360 | 4,360 | 0 | ✅ **UNMUTATED** |
| **`contracts`** | 4,360 | 4,360 | 0 | ✅ **UNMUTATED** |
| **`contractors`** | 1,997 | 1,997 | 0 | ✅ **UNMUTATED** |
| **`authorities`** | Audited | Audited | 0 | ✅ **UNMUTATED** |
| **`project_locations`** | Audited | Audited | 0 | ✅ **UNMUTATED** |
| **`project_identifiers`** | Audited | Audited | 0 | ✅ **UNMUTATED** |
| **TOTAL MUTATIONS** | — | — | **0** | ✅ **PASSED** |

---

## 6. Architectural Sign-Off

```
[X] Document produced: docs/phase-4c-step2-dataset-qualification.md
[X] Dedicated section created: Known Project Test Cases
[X] Test Case A (Uppal Elevated Corridor) fully audited & documented
[X] Test Case B (IIT Hyderabad) fully audited & documented
[X] Production database mutation count: EXACTLY 0
```

**STATUS**: **PHASE 4C STEP 2 — QUALIFICATION COMPLETE**
