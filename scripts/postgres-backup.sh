#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: postgres-backup.sh --url DATABASE_URL --service SERVICE --output-dir DIRECTORY

Creates one PostgreSQL custom-format dump. Supply credentials through DATABASE_URL or
the PostgreSQL client environment; this script never stores them.
EOF
}

database_url=""
service=""
output_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) database_url="$2"; shift 2 ;;
    --service) service="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$database_url" || -z "$service" || -z "$output_dir" ]]; then
  usage >&2
  exit 2
fi

umask 077
mkdir -p "$output_dir"
database="${database_url##*/}"
database="${database%%\?*}"
client_url="${database_url/postgresql+asyncpg:/postgresql:}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="${output_dir}/${timestamp}_${service}_${database}.dump"

pg_dump --dbname="$client_url" --format=custom --no-owner --no-acl --file="$backup_path"
printf 'created %s\n' "$backup_path"