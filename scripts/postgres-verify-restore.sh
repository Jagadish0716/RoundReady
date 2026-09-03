#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: postgres-verify-restore.sh --url DATABASE_URL --service SERVICE_DIR

Checks connectivity, Alembic's current revision, and that the service database has tables.
The service directory must contain that service's alembic.ini.
EOF
}

database_url=""
service_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) database_url="$2"; shift 2 ;;
    --service) service_dir="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$database_url" || -z "$service_dir" || ! -f "$service_dir/alembic.ini" ]]; then
  usage >&2
  exit 2
fi

service_name="$(basename "$service_dir")"
case "$service_name" in
  auth-service) database_env=AUTH_DATABASE_URL ;;
  user-service) database_env=USER_DATABASE_URL ;;
  interviewer-service) database_env=INTERVIEWER_DATABASE_URL ;;
  booking-service) database_env=BOOKING_DATABASE_URL ;;
  payment-service) database_env=PAYMENT_DATABASE_URL ;;
  interview-service) database_env=INTERVIEW_DATABASE_URL ;;
  notification-service) database_env=NOTIFICATION_DATABASE_URL ;;
  *) echo "unsupported service directory: $service_dir" >&2; exit 2 ;;
esac

client_url="${database_url/postgresql+asyncpg:/postgresql:}"
psql --dbname="$client_url" --set=ON_ERROR_STOP=1 --tuples-only --no-align \
  --command="SELECT current_database(); SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public';"
env "$database_env=$database_url" PYTHONPATH="$service_dir:libs" \
  alembic -c "$service_dir/alembic.ini" current