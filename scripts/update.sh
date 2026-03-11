#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

with_pull="false"
branch=""
keep="10"
db_backup=""
uploads_backup=""
env_backup=""
services_started="false"

on_error() {
  local exit_code=$?
  warn "Update stopped because something went wrong."
  if [ -n "${db_backup}" ]; then
    warn "Database backup: ${db_backup}"
  fi
  if [ -n "${uploads_backup}" ]; then
    warn "Uploads backup: ${uploads_backup}"
  fi
  if [ -n "${env_backup}" ]; then
    warn "Env backup: ${env_backup}"
  fi
  if [ "${services_started}" = "true" ]; then
    warn "Stopping app service because the update did not complete cleanly."
    compose stop app >/dev/null || true
    compose logs --tail=120 app || true
  fi
  exit "${exit_code}"
}

trap on_error ERR

while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-pull)
      with_pull="true"
      ;;
    --skip-pull)
      with_pull="false"
      ;;
    --branch)
      branch="${2:-}"
      shift
      ;;
    --keep)
      keep="${2:-10}"
      shift
      ;;
    *)
      warn "Unknown argument: $1"
      exit 1
      ;;
  esac
  shift
done

backup_output="$("${SCRIPT_DIR}/backup.sh")"
printf '%s\n' "${backup_output}"
db_backup="$(printf '%s\n' "${backup_output}" | awk -F= '/^DB_BACKUP=/{print $2}')"
uploads_backup="$(printf '%s\n' "${backup_output}" | awk -F= '/^UPLOAD_BACKUP=/{print $2}')"
env_backup="$(printf '%s\n' "${backup_output}" | awk -F= '/^ENV_BACKUP=/{print $2}')"

if [ "${with_pull}" = "true" ]; then
  current_branch="${branch}"
  if [ -z "${current_branch}" ]; then
    current_branch="$(git -C "${ROOT_DIR}" branch --show-current)"
  fi
  log "Updating repository on branch ${current_branch}."
  git -C "${ROOT_DIR}" fetch --all --prune
  git -C "${ROOT_DIR}" checkout "${current_branch}"
  git -C "${ROOT_DIR}" pull --ff-only origin "${current_branch}"
fi

"${SCRIPT_DIR}/check_env.sh"

log "Rebuilding and starting Docker services."
compose up --build -d
services_started="true"

health_url="${APP_HEALTH_URL:-http://localhost:8000/}"
wait_for_app "${health_url}" 45

"${SCRIPT_DIR}/prune_backups.sh" "${keep}"
trap - ERR
log "Update complete."
compose ps
