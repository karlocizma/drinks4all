#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

mkdir -p "${BACKUP_DIR}"

timestamp="$(date +%Y%m%d-%H%M%S)"
db_backup="${BACKUP_DIR}/albdrinks-db-${timestamp}.sql.gz"
uploads_backup="${BACKUP_DIR}/albdrinks-uploads-${timestamp}.tar.gz"
env_backup="${BACKUP_DIR}/albdrinks-env-${timestamp}.env"

log "Ensuring PostgreSQL is running for backup."
compose up -d postgres >/dev/null

if ! wait_for_postgres 30; then
  warn "PostgreSQL did not become ready in time."
  exit 1
fi

log "Creating database backup at ${db_backup}."
compose exec -T postgres pg_dump -U postgres -d drinks4all --clean --if-exists --no-owner --no-privileges | gzip > "${db_backup}"

if [ -f "${ROOT_DIR}/.env" ]; then
  log "Copying environment file to ${env_backup}."
  cp "${ROOT_DIR}/.env" "${env_backup}"
else
  warn "No .env file found, skipping env backup."
  env_backup=""
fi

if docker volume inspect drinks4all_uploads >/dev/null 2>&1; then
  log "Creating uploads backup at ${uploads_backup}."
  if ! docker run --rm \
    -v drinks4all_uploads:/source:ro \
    -v "${BACKUP_DIR}:/backup" \
    busybox sh -c "cd /source && tar -czf /backup/$(basename "${uploads_backup}") ."; then
    warn "Uploads backup failed. Database backup is still available."
    uploads_backup=""
  fi
else
  warn "Uploads volume not found, skipping uploads backup."
  uploads_backup=""
fi

printf 'DB_BACKUP=%s\n' "${db_backup}"
printf 'UPLOAD_BACKUP=%s\n' "${uploads_backup}"
printf 'ENV_BACKUP=%s\n' "${env_backup}"
