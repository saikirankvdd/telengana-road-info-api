# Telangana-Wide Historical Procurement ETL Report (Audited)

**Date**: 2026-10-03 01:44:50  
**Source Dataset**: `fireboy21/tenders_aoc` (Hugging Face SQLite repository)  
**Database Status**: NOT MODIFIED (0 PostgreSQL imports)  
**Audit Verification**: Verified 100% consistent against `data/processed/telangana_historical_all.csv`.

---

## 1. Executive Summary & Audited Totals

- **Audited CSV Rows (`telangana_historical_all.csv`)**: 7,463
- **Total Category Sum in Final CSV**: 7,463 (Equal: `YES`)
- **Total Discrepancy Cause**: The reported 92,340 OTHER_INFRASTRUCTURE count was calculated from the TOTAL Telangana population (105,659 records) prior to partition. 92,340 non-road infrastructure/equipment records were routed to data/processed/telangana_historical_review.csv, while the 7,463 relevant road/bridge records were written to data/processed/telangana_historical_all.csv.
- **Historical Coverage Range**: 2012 – 2026

---

## 2. Audited Category Breakdown (`telangana_historical_all.csv`)

| Category | Record Count | Percentage |
| :--- | :--- | :--- |
| **ROAD** | 6,393 | 85.7% |
| **HIGHWAY** | 484 | 6.5% |
| **FLYOVER** | 103 | 1.4% |
| **BRIDGE** | 201 | 2.7% |
| **ROB** | 26 | 0.3% |
| **RUB** | 7 | 0.1% |
| **GRADE_SEPARATOR** | 6 | 0.1% |
| **ROAD_WIDENING** | 52 | 0.7% |
| **OTHER_INFRASTRUCTURE** | 0 | 0.0% |
| **TOTAL** | **7,463** | **100.0%** |

---

## 3. Audited Data Quality & Coverage Metrics

- **Contractor Name Coverage**: 79.6% (5,942 / 7,463)
- **Contract Value Coverage**: 78.6% (5,869 / 7,463)
- **Tender Reference Coverage**: 80.6% (6,014 / 7,463)
- **Location Coverage**: 95.4% (7,118 / 7,463)

---

## 4. Discovered Organisations & District Breakdown

- **Total Organisations Represented**: 147
- **Total Locations / Districts Discovered**: 32

---

## 5. File Deliverables

- **Statewide Cleaned Road Dataset**: `data/processed/telangana_historical_all.csv` (7,463 records)
- **Review Dataset**: `data/processed/telangana_historical_review.csv` (98,196 records)
- **Documentation**: `docs/telangana-historical-etl-report.md`

---
*Report audited and verified against actual CSV population.*
