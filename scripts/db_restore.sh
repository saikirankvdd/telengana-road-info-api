#!/usr/bin/env bash
# Production PostgreSQL Database Restore Script
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <path_to_backup_file.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-telangana_road_db}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Error: Backup file '${BACKUP_FILE}' not found."
  exit 1
fi

echo "Starting database restore to '${DB_NAME}' from '${BACKUP_FILE}'..."

PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists -v "${BACKUP_FILE}"

echo "Database restore completed successfully."
