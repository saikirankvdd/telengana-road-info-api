#!/usr/bin/env bash
# Production PostgreSQL Database Backup Script
set -e

BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/telangana_road_db_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-telangana_road_db}"

echo "Starting PostgreSQL backup for database '${DB_NAME}' on host '${DB_HOST}:${DB_PORT}'..."

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -F c -b -v -f "${BACKUP_FILE}" "${DB_NAME}"

echo "Backup completed successfully: ${BACKUP_FILE}"
