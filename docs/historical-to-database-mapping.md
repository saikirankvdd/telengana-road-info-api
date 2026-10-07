# Historical CSV to PostgreSQL Database Mapping Specification

**Source CSV**: `data/processed/telangana_historical_all.csv`  
**Target Schema**: PostgreSQL 16 + PostGIS 3.4  
**Date**: 2026-10-03

---

## 1. Column-to-Table Field Mapping Matrix

| CSV Field Name | Destination Table | Destination Field | Data Type | Transformation / Normalization Rule |
| :--- | :--- | :--- | :--- | :--- |
| `project_candidate_key` | `projects` | `project_id` | `VARCHAR(255)` | Deterministic primary key identifier |
| `project_name` | `projects` | `project_name` | `VARCHAR(255)` | Title string as provided |
| `project_name` | `projects` | `normalized_project_name` | `VARCHAR(255)` | Upper-case, stripped whitespace |
| `work_description` | `projects` | `description` | `TEXT` | Detailed work scope description |
| `category` | `projects` | `category` | `VARCHAR(100)` | One of 18 fine-grained infrastructure categories |
| `organisation` | `authorities` | `name` | `VARCHAR(255)` | Government department or municipal body |
| `organisation` | `authorities` | `normalized_name` | `VARCHAR(255)` | Stripped upper-case name for exact lookup |
| `executing_authority` | `projects` | `authority_id` | `INTEGER (FK)` | Foreign key linking `authorities.id` |
| `state` | `project_locations` | `state` | `VARCHAR(100)` | Defaults to "Telangana" |
| `district` | `project_locations` | `district` | `VARCHAR(100)` | Extracted Telangana district or NULL |
| `city` | `project_locations` | `city` | `VARCHAR(100)` | Extracted municipality or city |
| `municipality` | `project_locations` | `municipality` | `VARCHAR(100)` | Municipal Corporation name |
| `locality` | `project_locations` | `locality` | `VARCHAR(100)` | Locality or zone name |
| `location_text` | `project_locations` | `address_text` | `TEXT` | Raw location string |
| `latitude` | `project_locations` | `latitude` | `DOUBLE PRECISION` | Geocoded latitude (NULL if unavailable) |
| `longitude` | `project_locations` | `longitude` | `DOUBLE PRECISION` | Geocoded longitude (NULL if unavailable) |
| `tender_id` | `tenders` | `tender_id` | `VARCHAR(255)` | e-Procurement Tender System ID |
| `tender_reference_number` | `tenders` | `tender_reference_number` | `VARCHAR(255)` | Notice Inviting Tender (NIT) reference |
| `tender_title` | `tenders` | `title` | `TEXT` | Full tender publication title |
| `tender_publication_date` | `tenders` | `published_date` | `TIMESTAMP` | Publication timestamp |
| `tender_closing_date` | `tenders` | `closing_date` | `TIMESTAMP` | Bid submission end timestamp |
| `selected_bidder` | `contractors` | `legal_name` | `VARCHAR(255)` | Exact legal name of awarded contractor |
| `contractor` | `contractors` | `normalized_name` | `VARCHAR(255)` | Stripped name without corporate suffixes |
| `contract_value` | `contracts` | `contract_value` | `DOUBLE PRECISION` | Parsed financial value in INR |
| `contract_value` | `project_cost_history` | `amount` | `DOUBLE PRECISION` | Initial AWARDED cost record |
| `award_date` | `contracts` | `award_date` | `TIMESTAMP` | Award of Contract (AOC) timestamp |
| `completion_period` | `contracts` | `completion_period_days` | `INTEGER` | Contract duration in days |
| `source_name` | `sources` | `source_name` | `VARCHAR(255)` | "fireboy21/tenders_aoc" |
| `source_type` | `sources` | `source_type` | `VARCHAR(100)` | "HISTORICAL_HF_DATASET" |
| `source_record_id` | `source_records` | `external_record_id` | `VARCHAR(255)` | SQLite internal record ID |
| `source_url` | `tenders` | `source_url` | `TEXT` | Direct CPP / e-Procurement document URL |

---

## 2. Integrity & Lineage Rules

1. **No Data Loss**: All original source strings (e.g. `selected_bidder`, `tender_reference_number`, `source_url`) are preserved un-truncated in `contractors.legal_name`, `tenders.tender_reference_number`, and `source_records.external_url`.
2. **Zero Hardcoding**: Unspecified contact info (email, phone, address) remains `NULL` until enriched from official government registers.
