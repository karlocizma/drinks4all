#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

example_file="${1:-${ROOT_DIR}/.env.example}"
env_file="${2:-${ROOT_DIR}/.env}"

if [ ! -f "${example_file}" ]; then
  warn "Example env file not found: ${example_file}"
  exit 1
fi

if [ ! -f "${env_file}" ]; then
  warn "Local env file not found: ${env_file}"
  exit 1
fi

extract_keys() {
  local file="$1"
  grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "${file}" | cut -d= -f1 | sort -u
}

missing_keys="$(comm -23 <(extract_keys "${example_file}") <(extract_keys "${env_file}") || true)"
extra_keys="$(comm -13 <(extract_keys "${example_file}") <(extract_keys "${env_file}") || true)"

status=0

if [ -n "${missing_keys}" ]; then
  warn "Your .env is missing keys that exist in .env.example:"
  printf '%s\n' "${missing_keys}" >&2
  status=1
fi

if [ -n "${extra_keys}" ]; then
  log "Your .env has extra keys not present in .env.example:"
  printf '%s\n' "${extra_keys}" >&2
fi

if [ "${status}" -eq 0 ]; then
  log "Environment file check passed."
fi

exit "${status}"
