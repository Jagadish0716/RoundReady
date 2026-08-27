#!/bin/sh
set -eu

create_service_database() {
  database_name="$1"
  database_user="$2"
  database_password="$3"

  psql --set=ON_ERROR_STOP=1 \
    --set=db_name="$database_name" \
    --set=db_user="$database_user" \
    --set=db_password="$database_password" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" <<-'SQL'
	SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'db_user', :'db_password')
	WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'db_user') \gexec
	SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_user')
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name') \gexec
	SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db_name') \gexec
	SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO %I', :'db_name', :'db_user') \gexec
	SQL
}

create_service_database "$AUTH_DB_NAME" "$AUTH_DB_USER" "$AUTH_DB_PASSWORD"
create_service_database "$USER_DB_NAME" "$USER_DB_USER" "$USER_DB_PASSWORD"
create_service_database \
  "$INTERVIEWER_DB_NAME" "$INTERVIEWER_DB_USER" "$INTERVIEWER_DB_PASSWORD"
create_service_database "$BOOKING_DB_NAME" "$BOOKING_DB_USER" "$BOOKING_DB_PASSWORD"
create_service_database "$PAYMENT_DB_NAME" "$PAYMENT_DB_USER" "$PAYMENT_DB_PASSWORD"
create_service_database "$INTERVIEW_DB_NAME" "$INTERVIEW_DB_USER" "$INTERVIEW_DB_PASSWORD"
create_service_database \
  "$NOTIFICATION_DB_NAME" "$NOTIFICATION_DB_USER" "$NOTIFICATION_DB_PASSWORD"
