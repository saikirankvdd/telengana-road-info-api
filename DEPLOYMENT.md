# Production Deployment Guide

## Project Overview
**Telangana Road & Infrastructure Intelligence API**  
Production-Grade Backend REST API powered by Python 3.12, FastAPI, PostgreSQL/PostGIS, SQLAlchemy, Alembic, and Google Gemini API.

> **Note**: This is a backend/API-only deployment. There is no frontend or web application component.

---

## 1. Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.20+
- Python 3.12+ (for non-containerized execution)
- PostgreSQL 16+ with PostGIS extension (or containerized instance)
- Google Gemini API Key (`GEMINI_API_KEY`)

---

## 2. Environment Variables Configuration

Copy `.env.example` to `.env` and populate production credentials:

```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
|---|---|---|
| `ENVIRONMENT` | Deployment environment name | `production` |
| `DEBUG` | FastAPI debug flag (MUST be false in prod) | `false` |
| `PORT` | Container / Server HTTP listening port | `8000` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:secret@db:5432/telangana_road_db` |
| `REDIS_URL` | Redis URL for distributed rate limiting | `redis://redis:6379/0` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `JWT_SECRET` | Strong secret for signing access tokens | `custom_strong_secret_key` |
| `JWT_EXPIRE_MINUTES` | Access token expiration in minutes | `1440` (24 Hours) |
| `CORS_ORIGINS` | Comma-separated allowed CORS origins | `https://api.domain.gov.in` |

---

## 3. Deployment Options

### Option A: Production Docker Compose Deployment (Recommended)

1. Start all containerized services (PostgreSQL PostGIS, Redis, FastAPI backend):

```bash
docker-compose -f docker-compose.production.yml up -d --build
```

2. Run Database Migrations:

```bash
docker-compose -f docker-compose.production.yml exec api alembic upgrade head
```

3. Verify Health:

```bash
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready
```

### Option B: Bare-Metal / VM Native Deployment

1. Install Python dependencies:

```bash
pip install --no-cache-dir -r requirements.txt
```

2. Run Alembic Database Migrations:

```bash
alembic upgrade head
```

3. Start Application Server using Uvicorn:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
```

---

## 4. Health, Readiness & Metrics Endpoints

- **Health Probe**: `GET /health` (Returns 200 OK if FastAPI process is alive).
- **Readiness Probe**: `GET /ready` (Returns 200 OK if DB & configuration are fully connected, 503 if DB unavailable).
- **System Info**: `GET /api/v1/system/info` (Safe version & limits metadata).
- **Prometheus Metrics**: `GET /metrics` (Exposes request counters, error rates, and process uptime).

---

## 5. Security Controls & Request Tracing

- **Request Tracing**: All requests receive a unique `X-Request-ID` header.
- **SSRF Protection**: Outbound web requests to internal IP ranges (`127.0.0.1`, `10.0.0.0/8`, `169.254.169.254`) and unsupported schemes (`file://`, `ftp://`) are rejected automatically.
- **Prompt Injection Defense**: Untrusted webpage text is sanitized by `PromptGuard` and wrapped in `<UNTRUSTED_EXTERNAL_WEBPAGE_DATA>` tags.
- **Security Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`.

---

## 6. Database Backup & Restore Procedure

### Database Backup
Execute the automated backup script:

```bash
POSTGRES_PASSWORD=postgrespassword ./scripts/db_backup.sh
```
Backups are saved to `./data/backups/telangana_road_db_YYYYMMDD_HHMMSS.sql.gz`.

### Database Restore
Restore a snapshot into a target database:

```bash
POSTGRES_PASSWORD=postgrespassword ./scripts/db_restore.sh ./data/backups/telangana_road_db_20261005_034500.sql.gz
```

---

## 7. Operational Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| `/ready` returns 503 | Database connection refused | Verify PostgreSQL process, check `DATABASE_URL` credentials & network port |
| `JWT_SECRET` startup warning | Default JWT secret in production | Set custom `JWT_SECRET` in `.env` |
| Rate Limit HTTP 429 | Exceeded request quota | Wait 60 seconds or adjust `RATE_LIMITS` configuration |
| Gemini API error | Missing/Invalid API key | Verify `GEMINI_API_KEY` in environment variables |
