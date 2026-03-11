#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

db_backup="${1:-latest}"
uploads_backup="${2:-}"
env_backup="${3:-}"

latest_backup() {
  find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'albdrinks-db-*.sql.gz' | sort | tail -n 1
}

if [ "${db_backup}" = "latest" ]; then
  db_backup="$(latest_backup)"
fi

if [ -z "${db_backup}" ] || [ ! -f "${db_backup}" ]; then
  warn "Database backup not found: ${db_backup}"
  exit 1
fi

if [ -z "${uploads_backup}" ]; then
  candidate="${db_backup/albdrinks-db-/albdrinks-uploads-}"
  candidate="${candidate/.sql.gz/.tar.gz}"
  if [ -f "${candidate}" ]; then
    uploads_backup="${candidate}"
  fi
fi

if [ -z "${env_backup}" ]; then
  candidate="${db_backup/albdrinks-db-/albdrinks-env-}"
  candidate="${candidate/.sql.gz/.env}"
  if [ -f "${candidate}" ]; then
    env_backup="${candidate}"
  fi
fi

log "Stopping app service before restore."
compose stop app >/dev/null || true
compose up -d postgres >/dev/null

if ! wait_for_postgres 30; then
  warn "PostgreSQL did not become ready in time."
  exit 1
fi

log "Restoring database from ${db_backup}."
gunzip -c "${db_backup}" | compose exec -T postgres psql -U postgres -d drinks4all >/dev/null

if [ -n "${uploads_backup}" ] && [ -f "${uploads_backup}" ]; then
  log "Restoring uploads from ${uploads_backup}."
  docker run --rm \
    -v drinks4all_uploads:/target \
    -v "${BACKUP_DIR}:/backup" \
    busybox sh -c "rm -rf /target/* && mkdir -p /target && tar -xzf /backup/$(basename "${uploads_backup}") -C /target"
fi

if [ -n "${env_backup}" ] && [ -f "${env_backup}" ]; then
  log "Restoring .env from ${env_backup}."
  cp "${env_backup}" "${ROOT_DIR}/.env"
fi

log "Starting full stack after restore."
compose up -d >/dev/null
compose ps
