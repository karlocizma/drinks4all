#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

keep="${1:-10}"

mkdir -p "${BACKUP_DIR}"

prune_pattern() {
  local pattern="$1"
  mapfile -t files < <(find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${pattern}" | sort -r)
  if [ "${#files[@]}" -le "${keep}" ]; then
    return 0
  fi
  for file in "${files[@]:${keep}}"; do
    rm -f "${file}"
    log "Removed old backup ${file}"
  done
}

prune_pattern 'albdrinks-db-*.sql.gz'
prune_pattern 'albdrinks-uploads-*.tar.gz'
