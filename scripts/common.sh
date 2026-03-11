#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"

compose() {
  (
    cd "${ROOT_DIR}"
    docker compose "$@"
  )
}

log() {
  printf '[albdrinks] %s\n' "$*" >&2
}

warn() {
  printf '[albdrinks] WARNING: %s\n' "$*" >&2
}

wait_for_postgres() {
  local retries="${1:-30}"
  local attempt=1
  while [ "${attempt}" -le "${retries}" ]; do
    if compose exec -T postgres pg_isready -U postgres -d drinks4all >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
  return 1
}

check_http() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "${url}" >/dev/null
    return $?
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -q -O /dev/null "${url}"
    return $?
  fi
  warn "Neither curl nor wget is installed; skipping HTTP health check."
  return 0
}

wait_for_app() {
  local url="${1:-http://localhost:8000/}"
  local retries="${2:-30}"
  local attempt=1
  while [ "${attempt}" -le "${retries}" ]; do
    if check_http "${url}"; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
  return 1
}
