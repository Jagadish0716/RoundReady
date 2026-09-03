#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: postgres-restore.sh --backup FILE --target-url DATABASE_URL [--allow-production-target]

Restores a custom-format dump into the explicitly named target database. The target must
already exist and be empty or a recovery/staging database. Production-like target names
require --allow-production-target as an additional deliberate safeguard.
EOF
}

backup=""
target_url=""
allow_production_target=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup) backup="$2"; shift 2 ;;
    --target-url) target_url="$2"; shift 2 ;;
    --allow-production-target) allow_production_target=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$backup" || -z "$target_url" || ! -f "$backup" ]]; then
  usage >&2
  exit 2
fi

target_database="${target_url##*/}"
target_database="${target_database%%\?*}"
client_url="${target_url/postgresql+asyncpg:/postgresql:}"
if [[ "$allow_production_target" != true && "$target_database" =~ (prod|production|live) ]]; then
  echo "refusing production-like target database: $target_database" >&2
  exit 1
fi

pg_restore --dbname="$client_url" --exit-on-error --no-owner --no-acl "$backup"
printf 'restored %s into %s\n' "$backup" "$target_database"