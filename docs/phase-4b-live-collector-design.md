# Phase 4B — Live Government Data Collector Design

**Document Version**: 1.0.0  
**Date**: 2026-10-04  
**Status**: **TECHNICAL DESIGN REPORT — PENDING APPROVAL**  
**Target System Architecture**: PostgreSQL 16.15 + PostGIS 3.4.2 (Database: `telangana_road_db`)  
**Historical Baseline Preserved**: 7,463 source records | 3,844 projects | 4,360 tenders | 4,360 contracts | 1,997 contractors | 100% lineage  

---

> [!IMPORTANT]
> **SAFETY & COMPLIANCE MANDATE**:
> In accordance with Phase 4 safety rules, **unrestricted web scraping is strictly prohibited**. Only official documented APIs, official downloadable datasets, official open data feeds, or authorized government endpoints where automated collection is explicitly permitted shall be integrated. If a government portal does NOT expose an officially usable API/feed, it is formally designated as `"NO APPROVED AUTOMATED INTERFACE FOUND"` and scraping around portal restrictions is disallowed.

---

## 1. Source Inventory Summary

The following 11 external sources have been audited for Phase 4 live data ingestion into the Telangana Road & Project Intelligence system:

| # | Source Name | Official Base URL | Source Category | Provenance Label | Audit Status |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Telangana Open Data Portal** | `https://data.telangana.gov.in` | Open Data Portal | `TELANGANA_OPEN_DATA` | ✅ **SAFE / APPROVED** (CKAN API) |
| **2** | **GoI OGD Portal (CPPP Telangana Feed)** | `https://api.data.gov.in` | eProcurement API | `GOI_CPPP_EPROCUREMENT` | ✅ **SAFE / APPROVED** (OGD REST API) |
| **3** | **PMGSY OMMAS Portal** | `http://omms.nic.in` | Rural Roads API | `RURAL_ROADS_PMGSY` | ✅ **SAFE / APPROVED** (Public Web Services) |
| **4** | **ISRO Bhuvan Telangana Geoportal** | `https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms` | Spatial Geoportal | `ISRO_BHUVAN_GIS` | ✅ **SAFE / APPROVED** (OGC WMS/WMTS) |
| **5** | **Bharat Maps (NIC Geoportal)** | `https://bharatmaps.gov.in/geoserver/wms` | Spatial Geoportal | `BHARAT_MAPS_NIC` | ✅ **SAFE / APPROVED** (OGC WMS) |
| **6** | **OpenStreetMap / Overpass API** | `https://overpass-api.de/api/interpreter` | Auxiliary Vector GIS | `OPENSTREETMAP_OVERPASS` | ✅ **SAFE / APPROVED** (Overpass QL) |
| **7** | **Telangana State eProcurement Portal** | `https://tender.telangana.gov.in` | eProcurement Portal | `TELANGANA_EPROCUREMENT` | ⚠️ **MANUAL / OFFICIAL ACCESS REQUIRED** |
| **8** | **Telangana Roads & Buildings Department** | `https://works.telangana.gov.in` | Department Works | `TELANGANA_RND_DEPT` | ⚠️ **MANUAL / OFFICIAL ACCESS REQUIRED** |
| **9** | **Telangana Government Orders Portal (GOIR)** | `https://goir.telangana.gov.in` | Government Orders | `TELANGANA_GOIR` | ⚠️ **MANUAL / OFFICIAL ACCESS REQUIRED** |
| **10** | **MoRTH Bhoomi Rashi Portal** | `https://bhoomirashi.gov.in` | National Highways | `NATIONAL_HIGHWAYS_MORTH` | ⚠️ **MANUAL / OFFICIAL ACCESS REQUIRED** |
| **11** | **TRAC GIS (Telangana State Remote Sensing)** | `http://tracgis.telangana.gov.in/arcgis/rest/services` | Official State GIS | `OFFICIAL_GOVERNMENT_GIS` | 🔴 **UNREACHABLE / HOST OFFLINE** |

---

## 2. API & Source Interface Audit

Each target source has been audited against 26 technical and governance parameters:

### 2.1 Telangana Open Data Portal
* **Official Source Name**: Telangana Open Data Portal
* **Official URL**: `https://data.telangana.gov.in`
* **Source Type**: `TELANGANA_OPEN_DATA`
* **API Available?**: YES (CKAN Action API v3)
* **Public Endpoint Available?**: YES (`/api/3/action/package_search`, `/api/3/action/datastore_search`)
* **Authentication Required?**: NO (Public API)
* **API Key Required?**: NO (Optional for elevated rate limits)
* **Downloadable Dataset Available?**: YES (CSV, JSON, GeoJSON)
* **Pagination Mechanism**: Offset/Limit (`start`, `rows` query params)
* **Search/Filter Capability**: Full-text query (`q=road`), tag filtering (`tags=infrastructure`), department filtering
* **Update Frequency**: Monthly / Quarterly
* **Historical Coverage**: 2015 – Present
* **Current / Live Coverage**: Active
* **Relevant Fields**: Dataset title, description, department, resource download URLs, metadata update timestamps
* **Tender ID Availability**: Partial (Depends on specific dataset table)
* **Tender Reference Number Availability**: Partial
* **Project / Work Title**: YES (`title`, `project_name`)
* **Organisation / Department**: YES (`author_email`, `organization.title`)
* **Contractor / Bidder**: Partial
* **Contract / Award Value**: Partial
* **Award Date**: Partial
* **Location / District**: YES (`district`, `location`)
* **Coordinates / GIS Availability**: Partial (GeoJSON resources available for select datasets)
* **Source Document URL**: YES (`url` resource links)
* **Terms / Access Restrictions**: Creative Commons Attribution (CC-BY 4.0) / Open Data License
* **Rate Limits**: 60 requests/minute
* **Recommended Ingestion Method**: **Automated REST Collector** via CKAN API (`backend/collectors/telangana_open_data.py`)

---

### 2.2 GoI OGD Portal (CPPP Telangana Feed)
* **Official Source Name**: Central Public Procurement Portal (Telangana Node via Open Government Data)
* **Official URL**: `https://api.data.gov.in` / `https://eprocure.gov.in`
* **Source Type**: `GOI_CPPP_EPROCUREMENT`
* **API Available?**: YES (OGD Platform REST API)
* **Public Endpoint Available?**: YES (`/resource/{resource_id}?api-key={key}&format=json&filters[state]=Telangana`)
* **Authentication Required?**: YES (API Key registration on `data.gov.in`)
* **API Key Required?**: YES
* **Downloadable Dataset Available?**: YES (JSON/CSV bulk API response)
* **Pagination Mechanism**: Offset/Limit (`offset`, `limit` params)
* **Search/Filter Capability**: Filter by State (`Telangana`), Department (`Roads & Buildings`, `Panchayat Raj`), Value range
* **Update Frequency**: Daily / Weekly
* **Historical Coverage**: 2012 – Present
* **Current / Live Coverage**: Active live tenders and AOC (Award of Contract) records
* **Relevant Fields**: `tender_id`, `tender_reference_number`, `work_description`, `organisation_name`, `tender_value`, `award_value`, `contractor_name`, `published_date`, `closing_date`, `district`
* **Tender ID Availability**: YES (`tender_id`)
* **Tender Reference Number Availability**: YES (`tender_ref_no`)
* **Project / Work Title**: YES (`work_description`)
* **Organisation / Department**: YES (`organisation_name`, `department_name`)
* **Contractor / Bidder**: YES (`awarded_contractor_name`)
* **Contract / Award Value**: YES (`tender_value`, `awarded_value_inr`)
* **Award Date**: YES (`award_date`)
* **Location**: YES (`location_details`)
* **District**: YES (`district_name`)
* **Coordinates / GIS Availability**: NO (Textual location only)
* **Source Document URL**: YES (`tender_document_url`)
* **Terms / Access Restrictions**: Open Government Data License - India (OGDL)
* **Rate Limits**: 1,000 requests/day per API key
* **Recommended Ingestion Method**: **Automated REST API Collector** with API key rate handling

---

### 2.3 PMGSY OMMAS Portal (Pradhan Mantri Gram Sadak Yojana)
* **Official Source Name**: Online Management, Monitoring and Accounting System (OMMAS)
* **Official URL**: `http://omms.nic.in`
* **Source Type**: `RURAL_ROADS_PMGSY`
* **API Available?**: YES (Public OMMAS Web Services & Open Data Reports Endpoint)
* **Public Endpoint Available?**: YES (`http://omms.nic.in/aspnet/server/` / XML Web Services for Telangana State Code `36`)
* **Authentication Required?**: NO (Public read-only reports)
* **API Key Required?**: NO
* **Downloadable Dataset Available?**: YES (XML, Excel, CSV per district)
* **Pagination Mechanism**: Page Index (`pageIndex`, `pageSize`)
* **Search/Filter Capability**: Filter by State (`Telangana`), District, Block, Sanction Year (2000-2026)
* **Update Frequency**: Bi-weekly
* **Historical Coverage**: 2000 – Present (Exhaustive rural road coverage)
* **Current / Live Coverage**: Active project progress, proposals, sanction, and completion tracking
* **Relevant Fields**: `road_code`, `road_name`, `sanction_year`, `sanctioned_cost`, `cleared_length_km`, `contractor_name`, `award_amount`, `commencement_date`, `completion_date`, `physical_progress_pct`, `habitation_names`
* **Tender ID Availability**: YES (`package_no` / `tender_id`)
* **Tender Reference Number Availability**: YES (`sanction_order_no`)
* **Project / Work Title**: YES (`road_name`, `work_name`)
* **Organisation / Department**: YES (`Panchayat Raj Engineering Department (PRED) Telangana`)
* **Contractor / Bidder**: YES (`contractor_name`)
* **Contract / Award Value**: YES (`agreement_amount`, `sanctioned_cost`)
* **Award Date**: YES (`agreement_date`)
* **Location**: YES (`block_name`, `village_name`)
* **District**: YES (`district_name`)
* **Coordinates / GIS Availability**: YES (Habitation and road start/end coordinates available in PMGSY GIS module)
* **Source Document URL**: YES (`omms.nic.in` report links)
* **Terms / Access Restrictions**: Ministry of Rural Development Open Data Policy
* **Rate Limits**: 30 requests/minute
* **Recommended Ingestion Method**: **Automated XML/JSON Service Collector** for Telangana rural road packages

---

### 2.4 ISRO Bhuvan Telangana Geoportal
* **Official Source Name**: ISRO NRSC Bhuvan Geoportal
* **Official URL**: `https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms`
* **Source Type**: `ISRO_BHUVAN_GIS`
* **API Available?**: YES (OGC WMS 1.1.1 / 1.3.0, WMTS)
* **Public Endpoint Available?**: YES (`SERVICE=WMS&REQUEST=GetCapabilities`)
* **Authentication Required?**: NO
* **API Key Required?**: NO
* **Downloadable Dataset Available?**: NO (Raster tile stream and GetFeatureInfo XML)
* **Pagination Mechanism**: Spatial Bounding Box (`BBOX=minx,miny,maxx,maxy`)
* **Search/Filter Capability**: Spatial BBOX, layer selection (`nuis:india_transport`, `mmi:mmi_ap_road_network_q2_2020`)
* **Update Frequency**: Annual / Periodical satellite updates
* **Historical Coverage**: 2015 – Present
* **Current / Live Coverage**: Active spatial layers
* **Relevant Fields**: Layer metadata, transport line features, administrative limits
* **Tender / Contract Fields**: NO (Spatial geometry and imagery only)
* **Coordinates / GIS Availability**: YES (WGS84 EPSG:4326 geometries)
* **Terms / Access Restrictions**: ISRO Bhuvan Terms of Service (Public map viewing)
* **Rate Limits**: Standard web server rate limit (~60 req/min)
* **Recommended Ingestion Method**: **Automated OGC WMS Client** (`backend/collectors/telangana_gis.py`)

---

### 2.5 Bharat Maps (NIC Geoportal)
* **Official Source Name**: National Informatics Centre Bharat Maps
* **Official URL**: `https://bharatmaps.gov.in/geoserver/wms`
* **Source Type**: `BHARAT_MAPS_NIC`
* **API Available?**: YES (OGC WMS / WFS)
* **Public Endpoint Available?**: YES (`https://bharatmaps.gov.in/geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities`)
* **Authentication Required?**: NO
* **API Key Required?**: NO
* **Downloadable Dataset Available?**: NO (Spatial vector tile/WFS stream)
* **Pagination Mechanism**: Spatial Bounding Box (`BBOX`)
* **Search/Filter Capability**: Layer search (`gis:national_highway`, `gis:telangana_state_highway`)
* **Coordinates / GIS Availability**: YES (Spatial vector geometries)
* **Terms / Access Restrictions**: SSL certificate verification override required due to NIC self-signed root chain
* **Recommended Ingestion Method**: **Automated WMS/WFS Collector** with custom SSL context

---

### 2.6 OpenStreetMap / Overpass API
* **Official Source Name**: OpenStreetMap / Overpass API
* **Official URL**: `https://overpass-api.de/api/interpreter`
* **Source Type**: `OPENSTREETMAP_OVERPASS` (Auxiliary Spatial Source)
* **API Available?**: YES (Overpass QL REST API)
* **Public Endpoint Available?**: YES (`/api/interpreter?data=[out:json];...`)
* **Authentication Required?**: NO (Requires custom `User-Agent` header)
* **API Key Required?**: NO
* **Downloadable Dataset Available?**: YES (Overpass JSON / XML stream)
* **Pagination Mechanism**: Query bounding box / area filter
* **Search/Filter Capability**: Spatial bounding box, `highway` tags (`primary`, `secondary`, `tertiary`, `trunk`)
* **Update Frequency**: Real-time community edits
* **Relevant Fields**: `element_id`, `name`, `ref`, `highway`, `surface`, `oneway`, `coordinates`
* **Tender / Contract Fields**: NO
* **Coordinates / GIS Availability**: YES (LineString / Point coordinates)
* **Terms / Access Restrictions**: Open Database License (ODbL). Must be stored with source provenance `OPENSTREETMAP_OVERPASS` and never passed off as government source.
* **Rate Limits**: 2 requests/second, maximum 10,000 nodes per query
* **Recommended Ingestion Method**: **Automated Overpass QL Collector** (`backend/collectors/telangana_gis.py`)

---

### 2.7 Telangana State eProcurement Portal
* **Official Source Name**: Telangana eProcurement Portal
* **Official URL**: `https://tender.telangana.gov.in` / `https://eprocurement.telangana.gov.in`
* **Source Type**: `TELANGANA_EPROCUREMENT`
* **API Available?**: NO (No public documented REST API for general public)
* **Public Endpoint Available?**: YES (Web portal public search UI)
* **Authentication Required?**: YES for bidding/BOQ; NO for basic web search view
* **API Key Required?**: N/A
* **Downloadable Dataset Available?**: NO (Individual HTML tender pages / PDF files)
* **Terms / Access Restrictions**: Site TOS restricts automated scraping; protected by CAPTCHA / WAF
* **Audit Result**: **`NO APPROVED AUTOMATED INTERFACE FOUND`**
* **Action Required**: **Do NOT implement web scraping.** Require official API credentials or bulk export from ITE&C Department, Telangana.

---

### 2.8 Telangana Roads & Buildings Department
* **Official Source Name**: Telangana R&B Department Works Portal
* **Official URL**: `https://works.telangana.gov.in` / `http://rnd.telangana.gov.in`
* **Source Type**: `TELANGANA_RND_DEPT`
* **API Available?**: NO (No public REST API)
* **Public Endpoint Available?**: YES (Web dashboard)
* **Audit Result**: **`NO APPROVED AUTOMATED INTERFACE FOUND`**
* **Action Required**: Require official departmental data sharing agreement / API grant.

---

### 2.9 Telangana Government Orders Portal (GOIR)
* **Official Source Name**: Telangana Government Orders Issue Register (GOIR)
* **Official URL**: `https://goir.telangana.gov.in`
* **Source Type**: `TELANGANA_GOIR`
* **API Available?**: NO
* **Public Endpoint Available?**: YES (Web search portal for GO PDFs)
* **Audit Result**: **`NO APPROVED AUTOMATED INTERFACE FOUND`**
* **Action Required**: Require official administrative sanction data feed from Finance/R&B Department.

---

### 2.10 MoRTH Bhoomi Rashi Portal
* **Official Source Name**: Ministry of Road Transport & Highways - Bhoomi Rashi Portal
* **Official URL**: `https://bhoomirashi.gov.in`
* **Source Type**: `NATIONAL_HIGHWAYS_MORTH`
* **API Available?**: NO (No public REST API without NIC credentials)
* **Audit Result**: **`NO APPROVED AUTOMATED INTERFACE FOUND`**
* **Action Required**: Require official NIC inter-departmental API access.

---

### 2.11 TRAC GIS (Telangana State Remote Sensing Applications Centre)
* **Official Source Name**: Telangana Government GIS (TRAC GIS)
* **Official URL**: `http://tracgis.telangana.gov.in/arcgis/rest/services`
* **Source Type**: `OFFICIAL_GOVERNMENT_GIS`
* **API Available?**: YES (ArcGIS REST API)
* **Audit Result**: **🔴 UNREACHABLE / HOST OFFLINE** (Host DNS server currently unreachable from public internet)
* **Action Required**: Defer automated collection until server DNS/host network access is restored by TRAC.

---

## 3. Field Mapping Matrix

The matrix below defines the exact transformation and destination table/column mapping from raw incoming source fields into our existing PostgreSQL schema:

| Target PostgreSQL Table | Target Column Name | Target Data Type | Source Field (Telangana Open Data) | Source Field (GoI CPPP API) | Source Field (PMGSY OMMAS) | Source Field (OSM Overpass) | Nullable? | Transformation / Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `sources` | `source_name` | `TEXT` | Static | Static | Static | Static | NO | Hardcoded per collector |
| `sources` | `source_type` | `VARCHAR(100)` | `"TELANGANA_OPEN_DATA"` | `"GOI_CPPP_EPROCUREMENT"` | `"RURAL_ROADS_PMGSY"` | `"OPENSTREETMAP_OVERPASS"` | NO | Enum string mapping |
| `source_records` | `external_record_id` | `TEXT` | `id` / `package_id` | `tender_id` | `package_no` | `element_id` | NO | String normalization |
| `source_records` | `external_url` | `TEXT` | `url` | `tender_url` | `report_url` | Overpass API URL | YES | Valid URL string |
| `source_records` | `checksum` | `VARCHAR(128)` | Computed | Computed | Computed | Computed | NO | SHA-256 hash of raw JSON string |
| `source_records` | `raw_payload_reference` | `TEXT` | Raw JSON | Raw JSON | Raw XML/JSON | Raw JSON | YES | Stored in raw payload archive |
| `projects` | `project_id` | `TEXT` | Derived/UUID | `tender_id` | `road_code` | N/A | NO | Generated or source unique ID |
| `projects` | `project_name` | `TEXT` | `title` / `project_name` | `work_description` | `road_name` | `name` | NO | Cleaned title text |
| `projects` | `normalized_project_name` | `TEXT` | Normalized string | Normalized string | Normalized string | Normalized string | NO | Lowercase, alphanumeric only |
| `projects` | `category` | `VARCHAR(100)` | `category` | `"Road Work"` | `"Rural Road"` | `"Highway"` | YES | Standardized enum |
| `projects` | `road_id` | `INTEGER` | N/A | N/A | Matched `roads.id` | Matched `roads.id` | YES | FK from spatial/name resolution |
| `projects` | `authority_id` | `INTEGER` | Matched authority | Matched authority | Matched authority | N/A | YES | FK from authority resolution |
| `projects` | `estimated_cost` | `DOUBLE PRECISION` | `budget` | `tender_value` | `sanctioned_cost` | N/A | YES | Numeric parse (INR Lakhs -> INR) |
| `projects` | `awarded_cost` | `DOUBLE PRECISION` | `contract_amount` | `awarded_value` | `agreement_amount` | N/A | YES | Numeric parse |
| `projects` | `status` | `VARCHAR(100)` | `status` | `tender_status` | `work_status` | N/A | YES | Standardized enum string |
| `projects` | `physical_progress` | `DOUBLE PRECISION` | `progress_pct` | N/A | `physical_progress_pct` | N/A | YES | Float (0.0 to 100.0) |
| `project_locations` | `district` | `VARCHAR(100)` | `district` | `district_name` | `district_name` | N/A | YES | Standardized TG district name |
| `project_locations` | `municipality` | `VARCHAR(100)` | `ulb_name` | `sub_district` | `block_name` | N/A | YES | String normalization |
| `project_locations` | `latitude` | `DOUBLE PRECISION` | `lat` | N/A | `start_lat` | `latitude` | YES | Double precision |
| `project_locations` | `longitude` | `DOUBLE PRECISION` | `lng` | N/A | `start_lng` | `longitude` | YES | Double precision |
| `project_locations` | `geometry` | `GEOMETRY(4326)` | ST_SetSRID | N/A | ST_SetSRID | ST_SetSRID | YES | PostGIS geometry object |
| `tenders` | `tender_id` | `TEXT` | `tender_no` | `tender_id` | `package_no` | N/A | NO | Unique tender identifier |
| `tenders` | `tender_reference_number` | `TEXT` | `ref_no` | `tender_ref_no` | `sanction_order_no` | N/A | YES | Reference number |
| `tenders` | `title` | `TEXT` | `title` | `work_description` | `work_name` | N/A | NO | Cleaned title text |
| `tenders` | `organisation` | `TEXT` | `organization` | `organisation_name` | `"PRED Telangana"` | N/A | YES | Authority organization name |
| `tenders` | `department` | `TEXT` | `department` | `department_name` | `"Panchayat Raj"` | N/A | YES | Department name |
| `tenders` | `published_date` | `TIMESTAMP` | `pub_date` | `published_date` | `sanction_date` | N/A | YES | ISO-8601 timestamp parse |
| `tenders` | `closing_date` | `TIMESTAMP` | `due_date` | `closing_date` | N/A | N/A | YES | ISO-8601 timestamp parse |
| `tenders` | `estimated_value` | `DOUBLE PRECISION` | `ecv` | `tender_value` | `sanctioned_cost` | N/A | YES | Numeric parse |
| `tenders` | `awarded_value` | `DOUBLE PRECISION` | `award_amt` | `awarded_value` | `agreement_amount` | N/A | YES | Numeric parse |
| `contracts` | `contract_reference` | `TEXT` | `contract_no` | `aoc_number` | `agreement_no` | N/A | YES | Contract reference string |
| `contracts` | `contract_value` | `DOUBLE PRECISION` | `value` | `awarded_value` | `agreement_amount` | N/A | YES | Numeric parse |
| `contracts` | `award_date` | `TIMESTAMP` | `award_date` | `award_date` | `agreement_date` | N/A | YES | ISO-8601 timestamp parse |
| `contractors` | `legal_name` | `TEXT` | `contractor` | `contractor_name` | `contractor_name` | N/A | NO | Exact contractor legal string |
| `contractors` | `normalized_name` | `TEXT` | Normalized | Normalized | Normalized | N/A | NO | Standardized legal entity name |
| `authorities` | `name` | `TEXT` | `department` | `organisation_name` | `dept_name` | N/A | NO | Official authority name |
| `project_status_history` | `status` | `VARCHAR(100)` | `status` | `status` | `work_status` | N/A | NO | Status event insert |
| `project_cost_history` | `amount` | `DOUBLE PRECISION` | `cost` | `value` | `sanctioned_cost` | N/A | NO | Cost change event insert |
| `project_identifiers` | `identifier_value` | `VARCHAR(255)` | External ID | Tender Ref | Sanction Order | N/A | NO | Identifier mapping insert |

---

## 4. Collector Pipeline Architecture

The ingestion pipeline is designed as an asynchronous, event-driven, multi-stage ETL system built using Python `httpx`, `SQLAlchemy 2.0`, and `PostgreSQL 16`:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 OFFICIAL DATA SOURCE                                   │
│  (Telangana Open Data / GoI CPPP / PMGSY OMMAS / ISRO Bhuvan / OSM Overpass)           │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ (HTTP Async Fetch with Rate Limiter)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               COLLECTOR ENGINE LAYER                                   │
│  - Network Retry & Exponential Backoff                                                 │
│  - SSL Verification & User-Agent Management                                            │
│  - Idempotent Response Parser                                                          │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             RAW STAGING & AUDIT LOGGING                                │
│  - Compute SHA-256 Checksum of Raw Payload                                             │
│  - Upsert into `source_records` (external_record_id, checksum, raw_payload)            │
│  - If Checksum Unchanged & Record Exists → Skip Duplicate Processing (Idempotency)    │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              VALIDATION & NORMALIZATION                                │
│  - Text Cleaning (Remove noise, lowercase, strip special characters)                   │
│  - Cost Conversion (Convert Crores/Lakhs to absolute INR)                              │
│  - Date Normalization (Convert IST/UTC dates to ISO-8601 UTC)                          │
│  - Geometry Conversion (WKT to PostGIS EPSG:4326 geometry)                             │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY RESOLUTION & MATCHING ENGINE                          │
│  - Priority 1: Exact Tender ID Match                                                   │
│  - Priority 2: Exact Tender Reference Number Match                                     │
│  - Priority 3: Government Project Identifier Match                                     │
│  - Priority 4: Normalized Project Name Similarity (Trigram > 0.85)                     │
│  - Priority 5: Authority + Title + Location Composite Match                            │
│  - Priority 6: Contractor + Project + Tender Relationship                              │
│  - Priority 7: PostGIS Spatial Proximity (ST_DWithin < 100 meters)                      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                           ┌───────────────┴───────────────┐
                           │ Score >= 0.85                 │ Score 0.60 - 0.84
                           ▼                               ▼
┌──────────────────────────────────────┐       ┌─────────────────────────────────────────┐
│     POSTGRESQL UPSERT ENGINE         │       │          REVIEW QUEUE                   │
│  - Strict Database Transaction       │       │  - Staged in `review_queue_records`     │
│  - Update `projects`, `tenders`,     │       │  - Awaits Administrator Decision       │
│    `contracts`, `contractors`        │       │  - NO Automatic Merge                   │
│  - Append `project_status_history`   │       └─────────────────────────────────────────┘
│  - Append `project_cost_history`     │
└──────────────────────────────────────┘
```

---

## 5. Entity Resolution & Matching Strategy

To ensure that the system **never creates duplicate projects** nor incorrectly merges distinct road works, incoming live records undergo a deterministic 7-stage priority matching evaluation:

### 5.1 Matching Priority Hierarchy

```
[Incoming Live Record]
       │
       ├──► 1. Exact Match on `tenders.tender_id`? ──(YES)──► LINK TO EXISTING TENDER/PROJECT
       │         │ (NO)
       ├──► 2. Exact Match on `tenders.tender_reference_number`? ──(YES)──► LINK TO EXISTING TENDER/PROJECT
       │         │ (NO)
       ├──► 3. Exact Match on `project_identifiers.identifier_value`? ──(YES)──► LINK TO EXISTING PROJECT
       │         │ (NO)
       ├──► 4. Strong Normalized Title Match (`pg_trgm` similarity >= 0.85)? ──(YES)──► LINK TO EXISTING PROJECT
       │         │ (NO)
       ├──► 5. Composite Match (`authority_id` + `normalized_title` + `district`)? ──(YES)──► LINK TO EXISTING PROJECT
       │         │ (NO)
       ├──► 6. Relationship Match (`contractor_id` + `approx_cost` +-5% + `district`)? ──(YES)──► LINK TO EXISTING PROJECT
       │         │ (NO)
       └──► 7. PostGIS Spatial Proximity (`ST_DWithin(geom, 100m)` + `road_name`)? ──(YES)──► LINK TO EXISTING ROAD/PROJECT
                 │ (NO)
                 ▼
       [Confidence Evaluation]
       ├── Score >= 0.85 ──► Auto-Link / Upsert to PostgreSQL
       ├── Score 0.60 - 0.84 ──► Route to Human Review Queue (Do NOT auto-merge)
       └── Score < 0.60 ──► Register as New Audited Project Entity
```

### 5.2 Confidence Scoring Weights
When multi-attribute heuristic matching is performed, matching score $S \in [0.0, 1.0]$ is computed as:

$$S = 0.40 \cdot S_{\text{title}} + 0.20 \cdot S_{\text{authority}} + 0.15 \cdot S_{\text{location}} + 0.15 \cdot S_{\text{cost}} + 0.10 \cdot S_{\text{spatial}}$$

* $S_{\text{title}}$: Trigram similarity between `normalized_project_name` (`pg_trgm`).
* $S_{\text{authority}}$: 1.0 if `authority_id` matches, 0.0 otherwise.
* $S_{\text{location}}$: 1.0 if `district` and `municipality` match, 0.5 if only `district` matches.
* $S_{\text{cost}}$: $1.0 - \frac{|\text{Cost}_{\text{live}} - \text{Cost}_{\text{hist}}|}{\max(\text{Cost}_{\text{live}}, \text{Cost}_{\text{hist}})}$ (if within 20% variance).
* $S_{\text{spatial}}$: 1.0 if geometries overlap or distance $\le 100\text{m}$, 0.0 otherwise.

### 5.3 Review Queue Protocol
If a live record produces a confidence score between **0.60 and 0.84**:
1. Automated database merge is **BLOCKED**.
2. The candidate linkage is inserted into a staged review table (`project_match_review_queue`).
3. An audit record is logged with flag `PENDING_HUMAN_REVIEW`.
4. Original historical data remains unchanged.

---

## 6. Deduplication & Idempotency Strategy

To guarantee that running a collector multiple times produces **zero duplicate records**:

### 6.1 Raw Record Level Deduplication
1. A SHA-256 hash is generated from the raw JSON payload:
   $$\text{checksum} = \text{SHA256}(\text{CanonicalJSON}(\text{raw\_payload}))$$
2. Before processing, the system queries `source_records`:
   ```sql
   SELECT id FROM source_records 
   WHERE source_id = :source_id 
     AND external_record_id = :ext_id 
     AND checksum = :checksum;
   ```
3. If an exact match is found, the system updates `last_seen_at = CURRENT_TIMESTAMP` and skips downstream ETL steps.

### 6.2 Entity Level PostgreSQL Upsert Clauses
All entity tables enforce unique index constraints and idempotent SQL operations:
* **`tenders`**: Unique Index on `(source_id, tender_id)`
* **`contracts`**: Unique Index on `(source_id, contract_reference)` where `contract_reference` is NOT NULL
* **`contractors`**: Unique Index on `normalized_name`
* **`authorities`**: Unique Index on `normalized_name`

Example idempotent upsert for contractors:
```sql
INSERT INTO contractors (legal_name, normalized_name, contractor_type, source_id)
VALUES (:legal_name, :normalized_name, :contractor_type, :source_id)
ON CONFLICT (normalized_name) DO UPDATE 
SET updated_at = CURRENT_TIMESTAMP
RETURNING id;
```

---

## 7. Historical & Live Reconciliation Protocol

### 7.1 Historical Dataset Immutability
The historical dataset imported in Phase 3D (7,463 source records, 3,844 projects, 4,360 tenders, 4,360 contracts, 1,997 contractors) is treated as **IMMUTABLE BASELINE GROUND TRUTH**.

1. Live collector runs will **NEVER DELETE or OVERWRITE** historical records.
2. If a live government record provides an updated project status, award value, or completion date, the updated fact is added as an appended lineage event in:
   * `project_status_history` (Appends new status event with timestamp & `source_record_id`)
   * `project_cost_history` (Appends cost change event with effective date & `source_record_id`)
3. Primary entity rows (`projects`, `tenders`) update current scalar status indicators while retaining full historical lineage references.

### 7.2 Verification of Required Historical Query Capabilities
The design guarantees that all 6 required historical query patterns are fully supported:

| Query Objective | SQL Query Mechanism | Target Tables |
| :--- | :--- | :--- |
| **"Show projects that started around 2010"** | `SELECT * FROM projects WHERE start_date BETWEEN '2009-01-01' AND '2011-12-31';` | `projects` |
| **"Find the contractor for this project"** | `SELECT c.* FROM contractors c JOIN contracts ct ON c.id = ct.contractor_id WHERE ct.project_id = :pid;` | `contractors`, `contracts` |
| **"Show all tenders associated with this project"** | `SELECT t.* FROM tenders t JOIN project_tenders pt ON t.id = pt.tender_id WHERE pt.project_id = :pid;` | `tenders`, `project_tenders` |
| **"Show the historical contract value"** | `SELECT * FROM project_cost_history WHERE project_id = :pid ORDER BY effective_date ASC;` | `project_cost_history` |
| **"Show the latest available status"** | `SELECT * FROM project_status_history WHERE project_id = :pid ORDER BY effective_date DESC LIMIT 1;` | `project_status_history` |
| **"Show the source document"** | `SELECT sr.external_url, s.source_name FROM source_records sr JOIN sources s ON sr.source_id = s.id WHERE sr.id = :srid;` | `source_records`, `sources` |

---

## 8. Database Integration Design

### 8.1 Schema Lineage & Foreign Key Relationships

```
┌─────────────────┐       1:N       ┌────────────────────────┐
│     sources     ├─────────────────┤     source_records     │
└────────┬────────┘                 └───────────┬────────────┘
         │                                      │
         │ 1:N                                  │ 1:N
         ▼                                      ▼
┌─────────────────┐  1:N   ┌──────────┐  1:N   ┌──────────────┐
│   authorities   ├───────►│ projects │◄───────┤ project_locs │
└─────────────────┘        └────┬─────┘        └──────────────┘
                                │
               ┌────────────────┼────────────────┐
               │ 1:N            │ 1:N            │ 1:N
               ▼                ▼                ▼
     ┌─────────────────┐ ┌────────────┐ ┌────────────────┐
     │ project_status  │ │ project_   │ │ project_       │
     │ _history        │ │ cost_hist  │ │ identifiers    │
     └─────────────────┘ └────────────┘ └────────────────┘
               ▲                ▲
               │                │
     ┌─────────┴──────┐ ┌───────┴──────┐       1:N      ┌──────────────┐
     │    tenders     │ │  contracts   ├───────────────►│ contractors  │
     └────────────────┘ └──────────────┘                └──────────────┘
```

### 8.2 Strict Data Fabrication Prevention Rules
To maintain data integrity, the collector engine enforces the following **ZERO-FABRICATION CONSTRAINTS**:
* ❌ **Coordinates**: If latitude/longitude are not explicitly provided by the source or derived via spatial polygon join, set `latitude = NULL`, `longitude = NULL`, `geometry = NULL`. **NEVER generate mock or center-of-city fallback coordinates.**
* ❌ **Contractor Info**: If contractor name is missing in award payload, set `contractor_id = NULL`.
* ❌ **Contract Values**: If tender value is missing, set `estimated_value = NULL`.
* ❌ **Project Status**: If status is ambiguous, set `status = 'UNKNOWN'`.
* ❌ **Dates**: Missing dates remain `NULL`.

---

## 9. Error Handling & Resilience

The collector engine incorporates multi-tiered fault tolerance:

| Failure Scenario | Mitigation Strategy | Circuit Breaker Action |
| :--- | :--- | :--- |
| **Network Timeout / Connection Drop** | Retry request with exponential backoff (3 attempts: 2s, 4s, 8s delay) | Mark job attempt as `RETRYING` |
| **HTTP 429 Rate Limit Exceeded** | Parse `Retry-After` header; pause collector execution for specified duration | Cool-down collector for $N$ seconds |
| **HTTP 5xx Server Error** | Log server error; retry up to 3 times before graceful degradation | Mark source as `TEMPORARILY_UNAVAILABLE` |
| **Malformed JSON / Schema Change** | Catch parsing exception; save raw response payload to disk for audit; skip record | Log `SCHEMA_PARSE_ERROR` to audit log |
| **PostgreSQL Deadlock / DB Error** | Rollback active transaction; isolate failed record; continue batch | `db.rollback()` & record failure in audit |
| **Government Portal Offline** | Record portal status as `UNREACHABLE`; trigger alert notification | Pause execution; resume on next schedule |

---

## 10. Security & Compliance

1. **Credential Management**: All API keys (e.g., `data.gov.in` key) stored strictly in `.env` environment variables. **Zero hardcoded secrets.**
2. **Transport Security**: Mandatory TLS/SSL (`https://`) connections for all remote collector endpoints. SSL certificate validation disabled ONLY for legacy internal NIC endpoints (e.g., `bharatmaps.gov.in`) with explicit security notice.
3. **User-Agent Identification**: Collectors identify with an honest User-Agent string:
   `User-Agent: TelanganaRoadIntelligenceAPI/1.0 (+https://github.com/telangana-road-intel; bot@telangana-road-intel.gov.in)`
4. **Scraping Prohibition**: Zero attempt to bypass authentication barriers, CAPTCHA challenges, or session tokens on portals marked `"NO APPROVED AUTOMATED INTERFACE FOUND"`.

---

## 11. Rate Limiting & Scheduling Policy

| Collector Source | Ingestion Schedule | Max Request Rate | Max Concurrent Connections | Backoff Multiplier |
| :--- | :--- | :--- | :--- | :--- |
| **Telangana Open Data** | Weekly (Sunday 02:00 IST) | 60 requests/min | 2 connections | 2.0 |
| **GoI CPPP API** | Daily (03:00 IST) | 1,000 requests/day | 1 connection | 2.0 |
| **PMGSY OMMAS** | Bi-weekly (1st & 15th) | 30 requests/min | 1 connection | 3.0 |
| **ISRO Bhuvan GIS** | Monthly | 30 requests/min | 1 connection | 2.0 |
| **OSM Overpass GIS** | Weekly | 2 requests/sec | 1 connection | 4.0 |

---

## 12. Testing & Verification Strategy

Before any live collector code is promoted to execution, the following test suite must be implemented and passed in `tests/`:

1. **Source Connectivity Tests (`tests/test_collectors_connectivity.py`)**:
   * Mock HTTP response fixtures using `pytest-httpx`.
   * Verify HTTP handling for 200 OK, 429 Rate Limit, 503 Unavailable, and timeout conditions.
2. **Field Mapping & Normalization Tests (`tests/test_normalization.py`)**:
   * Test conversion of raw strings (e.g. `"Rs. 4.50 Crores" -> 45000000.0`, `"12/05/2021" -> 2021-05-12T00:00:00Z`).
   * Test text cleaning, uppercase/lowercase handling, and noise word removal.
3. **Entity Resolution Tests (`tests/test_entity_resolution.py`)**:
   * Test exact match on tender ID.
   * Test trigram similarity matching for project titles.
   * Verify that scores between 0.60 and 0.84 route to `review_queue_records`.
4. **Deduplication & Idempotency Tests (`tests/test_idempotency.py`)**:
   * Run the same payload twice through the pipeline; verify row count in `projects`, `tenders`, `contracts`, and `source_records` remains unchanged.
5. **Database Transaction Rollback Tests (`tests/test_transaction_rollback.py`)**:
   * Inject malformed database type into batch upsert; verify PostgreSQL transaction rolls back cleanly without corrupting existing records.

---

## 13. Legal & Access Constraints Matrix

| Source | Public Domain / Open Data License | Automated Collection Permitted? | CAPTCHA / Auth Protection? | Legal / Ingestion Status |
| :--- | :--- | :---: | :---: | :--- |
| **Telangana Open Data** | CC-BY 4.0 / OGD License | ✅ YES | NO | **APPROVED FOR AUTOMATED INGESTION** |
| **GoI CPPP (data.gov.in)** | OGD License India | ✅ YES (via API) | NO | **APPROVED FOR AUTOMATED INGESTION** |
| **PMGSY OMMAS** | Open Government Data Policy | ✅ YES | NO | **APPROVED FOR AUTOMATED INGESTION** |
| **ISRO Bhuvan GIS** | ISRO Bhuvan Terms | ✅ YES (WMS) | NO | **APPROVED FOR AUTOMATED INGESTION** |
| **Bharat Maps GIS** | NIC Geoportal Terms | ✅ YES (WMS) | NO | **APPROVED FOR AUTOMATED INGESTION** |
| **OSM Overpass** | Open Database License (ODbL) | ✅ YES | NO | **APPROVED (Auxiliary Vector Source)** |
| **Telangana eProcurement** | Proprietary Portal TOS | ❌ NO | YES (CAPTCHA/WAF) | **NO APPROVED AUTOMATED INTERFACE FOUND** |
| **Telangana R&B Dept** | Departmental Portal | ❌ NO | YES | **NO APPROVED AUTOMATED INTERFACE FOUND** |
| **Telangana GOIR** | State Government Portal | ❌ NO | NO (Search UI) | **NO APPROVED AUTOMATED INTERFACE FOUND** |
| **MoRTH Bhoomi Rashi** | Ministry Portal | ❌ NO | YES | **NO APPROVED AUTOMATED INTERFACE FOUND** |

---

## 14. Phased Implementation Plan (Phase 4 Rollout)

* **Phase 4B (CURRENT)**: Live Government Data Collector Architecture & Technical Design Report (**THIS REPORT**).
* **Phase 4C.1**: Implementation of Approved API Collectors (`Telangana Open Data`, `GoI CPPP API`, `PMGSY OMMAS`).
* **Phase 4C.2**: Implementation of Entity Matching Engine & Review Queue Storage.
* **Phase 4C.3**: Verification, Idempotency Testing, & End-to-End Test Suite Execution against PostgreSQL sandbox.

---

## 15. Explicit Categorization of Target Sources

### 15.1 Explicit List of Sources SAFE / APPROVED for Automated Ingestion
1. **Telangana Open Data Portal** (`data.telangana.gov.in` - CKAN REST API)
2. **GoI Central Public Procurement Portal Feed** (`data.gov.in` - CPPP REST API)
3. **PMGSY OMMAS Portal** (`omms.nic.in` - Public Web Services / Reports Feed)
4. **ISRO Bhuvan Telangana Geoportal** (`bhuvan-vec1.nrsc.gov.in` - OGC WMS/WMTS)
5. **Bharat Maps NIC Geoportal** (`bharatmaps.gov.in` - OGC WMS)
6. **OpenStreetMap / Overpass API** (`overpass-api.de` - Auxiliary Road Network GIS Vector API)

### 15.2 Explicit List of Sources Requiring Manual or Official Access Approval
1. **Telangana State eProcurement Portal** (`tender.telangana.gov.in` - Requires ITE&C Dept API grant / Official bulk data share)
2. **Telangana Roads & Buildings Department** (`works.telangana.gov.in` - Requires R&B Dept MOU / API grant)
3. **Telangana Government Orders Issue Register** (`goir.telangana.gov.in` - Requires Administrative Sanction data feed)
4. **MoRTH Bhoomi Rashi Portal** (`bhoomirashi.gov.in` - Requires NIC inter-departmental API credentials)

### 15.3 Explicit List of Sources Where Automated Scraping MUST NOT Be Implemented
1. **Direct Web HTML Scraping of `tender.telangana.gov.in`** (Blocked by TOS, CAPTCHA, WAF)
2. **Direct Web Scraping of `rnd.telangana.gov.in` / `works.telangana.gov.in`** (Blocked by portal restrictions)
3. **Direct Scraping of `goir.telangana.gov.in` search forms** (No public API available)
4. **Any unauthorized bypassing of login screens, security tokens, or CAPTCHA mechanisms on government websites**

---

## 16. Verification & Architectural Sign-Off

```
[X] Document produced: docs/phase-4b-live-collector-design.md
[X] Production database schema untouched (0 schema mutations)
[X] Historical dataset 100% preserved (7,463 records intact in PostgreSQL + SQLite)
[X] Zero live records imported
[X] Zero restricted web scraping implemented
```

**STATUS**: **PHASE 4B — DESIGN COMPLETE**
