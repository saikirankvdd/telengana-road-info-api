# Telangana Road & Project Intelligence API

A Python-based backend API acting as a unified integration layer to collect, normalize, combine, and expose road infrastructure and procurement data from multiple official Telangana and Government of India sources.

---

## 🏗 System Architecture

```mermaid
graph TD
    subgraph Data Sources
        GIS["Telangana GIS / ArcGIS REST Services"]
        TOD["Telangana Open Data Portal"]
        DGOV["data.gov.in (Government of India)"]
        EPROC["Telangana e-Procurement Portal"]
        HIST["Historical Procurement Datasets"]
    end

    subgraph Intelligence Core & Integration Layer
        COL["Collector Modules (HTTPX / Playwright)"]
        NORM["Normalization & Provenance Pipeline"]
        GIS_SRV["GIS Spatial Service"]
        SEARCH["Deterministic Search Engine"]
        SCHED["APScheduler (Periodic Collector)"]
    end

    subgraph Database Layer
        PG[("PostgreSQL + PostGIS")]
    end

    subgraph API Layer (FastAPI)
        V1["/api/v1/road-intelligence"]
        ROADS["/api/v1/roads"]
        PROJ["/api/v1/projects"]
        TEND["/api/v1/tenders"]
        AUTH["/api/v1/authorities"]
        CONT["/api/v1/contractors"]
        SRC["/api/v1/sources"]
    end

    GIS --> COL
    TOD --> COL
    DGOV --> COL
    EPROC --> COL
    HIST --> COL

    COL --> NORM
    NORM --> PG
    SCHED --> COL

    PG --> GIS_SRV
    PG --> SEARCH

    GIS_SRV --> V1
    SEARCH --> V1

    V1 --> CLIENT["Consuming Client Applications"]
    ROADS --> CLIENT
    PROJ --> CLIENT
    TEND --> CLIENT
    AUTH --> CLIENT
    CONT --> CLIENT
    SRC --> CLIENT
```

---

## 🛠 Technology Stack

* **Backend Core**: Python 3.12+, FastAPI, Uvicorn, Pydantic v2
* **Database & ORM**: PostgreSQL 16, PostGIS 3.4, SQLAlchemy 2.0, Alembic, GeoAlchemy2
* **Data & Scraping**: HTTPX, Playwright, Pandas, GeoPandas, Shapely
* **Scheduler**: APScheduler
* **Testing & DevOps**: Pytest, Pytest-Asyncio, Docker, Docker Compose

---

## 📂 Project Structure

```
telangana-road-intelligence-api/
├── backend/
│   ├── main.py                  # FastAPI Application Entrypoint
│   ├── api/
│   │   └── v1/                  # Version 1 REST API Routers
│   │       ├── roads.py
│   │       ├── projects.py
│   │       ├── tenders.py
│   │       ├── contractors.py
│   │       ├── authorities.py
│   │       ├── sources.py
│   │       └── intelligence.py  # Core Unified Intelligence Endpoint
│   ├── models/                  # SQLAlchemy ORM Models
│   │   ├── base.py
│   │   ├── road.py
│   │   ├── project.py           # Includes Multi-Authority & Contractor Junctions
│   │   ├── tender.py
│   │   ├── contractor.py
│   │   ├── authority.py
│   │   └── source.py
│   ├── schemas/                 # Pydantic Schemas & Data Contracts
│   │   ├── road.py
│   │   ├── project.py
│   │   ├── tender.py
│   │   ├── contractor.py
│   │   ├── authority.py
│   │   ├── source.py
│   │   └── intelligence.py
│   ├── services/                # Business Logic Services
│   │   ├── gis_service.py
│   │   ├── project_service.py
│   │   ├── tender_service.py
│   │   ├── contractor_service.py
│   │   └── intelligence_service.py
│   ├── collectors/              # External Source Collectors
│   │   ├── base.py
│   │   ├── telangana_gis.py
│   │   ├── telangana_open_data.py
│   │   └── eprocurement.py
│   ├── database/                # Database Engine & Connection Session
│   │   └── connection.py
│   └── core/                    # Settings & Security
│       ├── config.py
│       └── security.py
├── data/
│   ├── raw/                     # Raw fetched datasets
│   └── historical/              # Historical AOC procurement CSVs
├── tests/                       # Pytest Suite
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_projects.py
│   ├── test_roads.py
│   ├── test_intelligence.py   # Uppal & IIIT Junction Validation Tests
│   └── test_sources.py
├── scripts/
│   └── seed_data.py             # Proof-of-Data Seeder Script
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ⚡ Quick Start

### 1. Environment Setup

Clone the repository and copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 2. Local Virtual Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Application locally

```bash
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```

* **Interactive API Documentation (Swagger UI)**: `http://localhost:8000/docs`
* **Alternative Documentation (ReDoc)**: `http://localhost:8000/redoc`

---

## 🐳 Docker Deployment

To run PostgreSQL + PostGIS database and backend API in Docker containers:

```bash
docker compose up --build -d
```

---

## 🧪 Testing

Run test suite validating health, project search, spatial queries, and proof-of-data test cases:

```bash
PYTHONPATH=. pytest -v
```

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status |
| `GET` | `/api/v1/road-intelligence` | **Unified Intelligence Endpoint** (by `query`, `lat`/`lng`, or `project_id`) |
| `GET` | `/api/v1/nearby` | Spatial query for nearest road geometries |
| `GET` | `/api/v1/projects` | List or search registered projects |
| `GET` | `/api/v1/projects/{id}` | Detailed project record with authorities, contractors & tenders |
| `GET` | `/api/v1/roads` | List registered road network segments |
| `GET` | `/api/v1/roads/{id}` | Road record by ID |
| `GET` | `/api/v1/tenders` | List public procurement tender publications |
| `GET` | `/api/v1/contractors/{id}`| Contractor details (with fallback contact if unassigned) |
| `GET` | `/api/v1/authorities` | Government implementing authorities (MoRTH, GHMC, HMDA, R&B) |
| `GET` | `/api/v1/sources` | Data provenance audit logs |

---

## 🔑 Authentication

Protected endpoints require the `X-API-Key` HTTP header:

```http
GET /api/v1/projects HTTP/1.1
Host: localhost:8000
X-API-Key: tg_road_intel_secret_key_2026
```

---

## 📌 Data Provenance & Verification Principles

1. **No Hardcoded Answers**: If data is missing from connected sources, fields are returned as `null` with explicit `NOT_FOUND` status and descriptive explanations.
2. **Multi-Authority Support**: Projects support multiple roles (`PRIMARY_AUTHORITY`, `STATE_IMPLEMENTING_BODY`, `LOCAL_BODY`, `PLANNING_AUTHORITY`).
3. **Contractor Fallback Principle**: If contractor records are not explicitly available, the system returns responsible authority official contacts as fallback.
4. **Source Audit Trails**: Every record links back to its origin `source_id`, `source_url`, and timestamp.
