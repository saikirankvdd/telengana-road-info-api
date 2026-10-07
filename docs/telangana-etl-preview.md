# Telangana Historical Procurement ETL — Phase 2 Validation Report

**Date**: 2026-10-05 13:49:56  
**Data Source**: `fireboy21/tenders_aoc` (Hugging Face SQLite dataset)  
**ETL Status**: READ-ONLY / DRY-RUN (0 database mutations)

---

## 1. Summary Statistics

| Metric | Value |
| :--- | :--- |
| **Total Scanned Records** | 5,000 |
| **Telangana Records Identified** | 4,968 |
| **Road & Project Relevant Records** | 0 |
| **Year Coverage Range** | N/A |
| **Records with Contractor Name** | 4,968 (100.0%) |
| **Records with Contract Value** | 965 (19.4%) |

---

## 2. Category Classification Breakdown

| Category | Record Count | Percentage |
| :--- | :--- | :--- |
| **HIGHWAY / ROAD** | 0 | 0.0% |
| **FLYOVER / GRADE SEPARATOR** | 0 | 0.0% |
| **INFRASTRUCTURE** | 0 | 0.0% |
| **OTHER** | 0 | 0.0% |

---

## 3. Data Quality & Completeness Status

| Quality Status | Count | Description |
| :--- | :--- | :--- |
| **VALID** | 0 | Complete record with Tender ID, Title, Org, Contractor, and Awarded Value |
| **INCOMPLETE** | 658 | Partial record missing contractor name or exact financial value |
| **POSSIBLE_DUPLICATE** | 4,226 | Record matching exact tender ID or reference number |
| **LOW_RELEVANCE** | 84 | Record outside core road/highway infrastructure focus |

---

## 4. Targeted Keyword Matches

| Targeted Query / Entity | Hits Found | Description / Example Findings |
| :--- | :--- | :--- |
| **Uppal / Uppal Elevated Corridor** | 0 | Infrastructure & road works in Uppal & Uppal-Ghatkesar corridor |
| **IIIT / Gachibowli** | 0 | Flyover, junction improvement & road works in Gachibowli / IIIT area |
| **GHMC** | 0 | Municipal road construction, resurfacing & SRDP flyover projects |
| **HMDA** | 0 | Outer Ring Road (ORR), radial roads & master plan infrastructure |
| **R&B (Roads & Buildings)** | 0 | State highway widening, bridge construction & district connectivity |
| **NHAI (RO Hyderabad)** | 2 | National Highway expansion, 4/6 laning & toll plaza infrastructure |

---

## 5. Major Contracting Organisations

- **BHEL Hyderabad**: 3,996 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||CE SC AND CE CHENNAI ZONE  - MES||CWE SECUNDERABAD - MES||GE (SOUTH) SECUNDERABAD - MES**: 63 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||ADG (OF and DRDO) AND CE (R and D) SECUNDERABAD - MES||GE (I) RND KANCHANBAGH - MES**: 59 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||CE SC AND CE CHENNAI ZONE  - MES||CWE SECUNDERABAD - MES||GE (NORTH) SECUNDERABAD - MES**: 55 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||ADG (OF and DRDO) AND CE (R and D) SECUNDERABAD - MES||GE (I) RND PASHAN - MES**: 50 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||ADG (OF and DRDO) AND CE (R and D) SECUNDERABAD - MES||GE (I) RND GIRINAGAR - MES**: 45 records
- **Bharat Heavy Electricals Limited||HPEP - Hyderabad**: 42 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||ADG (PROJECTS) CHENNAI AND CE CHENNAI ZONE  - MES||CWE SECUNDERABAD No 2 - MES||GE MCEME SECUNDERABAD - MES**: 40 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||ADG (OF and DRDO) AND CE (R and D) SECUNDERABAD - MES||GE (I) RND (E) BANGALORE - MES**: 40 records
- **E-IN-C BRANCH - MILITARY ENGINEER SERVICES||CESC AND CE (AF) BANGALORE - MES||CWE (AF) SECUNDERABAD - MES||GE(AF)HAKIMPET HYDERABAD - MES**: 40 records


---

## 6. Sample Extracted Records Preview

Below are sample normalized records extracted from the historical dataset:

### Sample 1: None
- **Tender Ref**: C7AYX00011
- **Organisation**: BHEL Hyderabad
- **Category**: NOT_RELEVANT
- **Contractor**: SIEMENS (Original: `SIEMENS  LIMITED`)
- **Awarded Value**: N/A
- **AOC Date**: 22-Dec-2025 09:00 AM
- **Quality Status**: `LOW_RELEVANCE`
- **Source URL**: https://eprocure.gov.in/cppp/aocfullview/MjA1MDkzMg==A13h1OGQ2NzAxYTMwZTJhNTIxMGNiNmEwM2EzNmNhYWZhODk=A13h1MTc4MTc0MDY5Nw==

### Sample 2: None
- **Tender Ref**: C7A1Y66429
- **Organisation**: BHEL Hyderabad
- **Category**: NOT_RELEVANT
- **Contractor**: SIEMENS (Original: `SIEMENS  LIMITED`)
- **Awarded Value**: N/A
- **AOC Date**: 22-Dec-2025 09:00 AM
- **Quality Status**: `POSSIBLE_DUPLICATE`
- **Source URL**: https://eprocure.gov.in/cppp/aocfullview/MjA1MDkzMQ==A13h1OGQ2NzAxYTMwZTJhNTIxMGNiNmEwM2EzNmNhYWZhODk=A13h1MTc4MTc0MDY5Nw==

### Sample 3: None
- **Tender Ref**: B9AYM01525
- **Organisation**: BHEL Hyderabad
- **Category**: NOT_RELEVANT
- **Contractor**: DOXA ENGINEERING WORKS (Original: `DOXA ENGINEERING WORKS`)
- **Awarded Value**: N/A
- **AOC Date**: 22-Dec-2025 09:00 AM
- **Quality Status**: `POSSIBLE_DUPLICATE`
- **Source URL**: https://eprocure.gov.in/cppp/aocfullview/MjA1MDkyNQ==A13h1OGQ2NzAxYTMwZTJhNTIxMGNiNmEwM2EzNmNhYWZhODk=A13h1MTc4MTc0MDY5Nw==

### Sample 4: None
- **Tender Ref**: B9AYM01526
- **Organisation**: BHEL Hyderabad
- **Category**: NOT_RELEVANT
- **Contractor**: RADHA KRISHNA ENGGWORKS (Original: `RADHA KRISHNA ENGG.WORKS`)
- **Awarded Value**: N/A
- **AOC Date**: 22-Dec-2025 09:00 AM
- **Quality Status**: `POSSIBLE_DUPLICATE`
- **Source URL**: https://eprocure.gov.in/cppp/aocfullview/MjA1MDkyNg==A13h1OGQ2NzAxYTMwZTJhNTIxMGNiNmEwM2EzNmNhYWZhODk=A13h1MTc4MTc0MDY5Nw==

### Sample 5: None
- **Tender Ref**: B9AYM01527
- **Organisation**: BHEL Hyderabad
- **Category**: NOT_RELEVANT
- **Contractor**: RADHA KRISHNA ENGGWORKS (Original: `RADHA KRISHNA ENGG.WORKS`)
- **Awarded Value**: N/A
- **AOC Date**: 22-Dec-2025 09:00 AM
- **Quality Status**: `POSSIBLE_DUPLICATE`
- **Source URL**: https://eprocure.gov.in/cppp/aocfullview/MjA1MDkyNw==A13h1OGQ2NzAxYTMwZTJhNTIxMGNiNmEwM2EzNmNhYWZhODk=A13h1MTc4MTc0MDY5Nw==

---
*Report generated automatically by Telangana Historical Procurement ETL Pipeline.*
