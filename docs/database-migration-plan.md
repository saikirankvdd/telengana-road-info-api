# Database Migration & Deployment Plan — Telangana Road Intelligence API

**Target Environment**: PostgreSQL 16 + PostGIS 3.4  
**Date**: 2026-10-03

---

## 1. Migration Strategy

1. **Version-Controlled DDL**:
   - Migration script `database/migrations/001_initial_schema.sql` defines idempotent `CREATE TABLE IF NOT EXISTS` statements with explicit foreign keys and spatial indexes.

2. **Idempotent Historical Import**:
   - `scripts/import_historical_to_postgres.py` checks existing records before insertion to guarantee zero duplicate creation during re-execution.

3. **Environment Security**:
   - Database connection string is managed strictly via `DATABASE_URL` environment variable. Zero credentials hardcoded in codebase.

4. **Rollback & Safety Guardrails**:
   - All migrations run within explicit SQL transactions. In `--dry-run` mode, `session.rollback()` is executed, resulting in **0 database mutations**.
