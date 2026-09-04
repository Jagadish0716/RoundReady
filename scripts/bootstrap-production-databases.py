#!/usr/bin/env python3
"""Bootstrap isolated RoundReady databases and populate service runtime secrets.

Requires the AWS CLI and psql. Secret values are passed through process stdin or
environment variables and are never written to disk or command-line arguments.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit


@dataclass(frozen=True)
class ServiceDatabase:
    key: str
    database: str
    role: str


SERVICE_DATABASES = (
    ServiceDatabase("auth_database", "roundready_auth", "roundready_auth"),
    ServiceDatabase("user_database", "roundready_user", "roundready_user"),
    ServiceDatabase("interviewer_database", "roundready_interviewer", "roundready_interviewer"),
    ServiceDatabase("booking_database", "roundready_booking", "roundready_booking"),
    ServiceDatabase("payment_database", "roundready_payment", "roundready_payment"),
    ServiceDatabase("interview_database", "roundready_interview", "roundready_interview"),
    ServiceDatabase("notification_database", "roundready_notification", "roundready_notification"),
)
ALLOWED_ENVIRONMENTS = {"dev", "staging", "production"}
RDS_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]+\.rds\.amazonaws\.com$")
ACCOUNT_PATTERN = re.compile(r"^[0-9]{12}$")
REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+$")


def run(command: list[str], *, stdin: str | None = None, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(  # noqa: S603 - fixed executables and validated identifiers
        command,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {command[0]} (secret output suppressed)")
    return completed.stdout.strip()


def aws(region: str, arguments: list[str], *, stdin: str | None = None) -> str:
    return run(["aws", "--region", region, *arguments], stdin=stdin)


def load_secret(region: str, secret_id: str) -> dict[str, Any]:
    raw = aws(
        region,
        [
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_id,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
    )
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Secret payload must be a JSON object")
    return value


def secret_has_version(region: str, secret_id: str) -> bool:
    count = aws(
        region,
        [
            "secretsmanager",
            "list-secret-version-ids",
            "--secret-id",
            secret_id,
            "--query",
            "length(Versions)",
            "--output",
            "text",
        ],
    )
    return int(count) > 0


def existing_password(
    payload: dict[str, Any], service: ServiceDatabase, host: str, port: int
) -> str:
    raw_url = payload.get("database_url")
    if not isinstance(raw_url, str):
        raise ValueError(f"Existing {service.key} secret lacks database_url")
    parsed = urlsplit(raw_url)
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname != host
        or parsed.port != port
        or unquote(parsed.username or "") != service.role
        or parsed.path != f"/{service.database}"
        or parsed.password is None
    ):
        raise ValueError(f"Existing {service.key} secret does not match the requested environment")
    return unquote(parsed.password)


def sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def validate_secret_arn(
    secret_arn: str, *, region: str, account_id: str, expected_name: str | None = None
) -> None:
    fields = secret_arn.split(":", 6)
    if (
        len(fields) != 7
        or fields[0] != "arn"
        or fields[2] != "secretsmanager"
        or fields[3] != region
        or fields[4] != account_id
        or fields[5] != "secret"
    ):
        raise ValueError("Secret ARN does not match the selected AWS region/account")
    if expected_name is not None:
        actual_name = fields[6]
        if actual_name != expected_name and not actual_name.startswith(f"{expected_name}-"):
            raise ValueError("Service secret ARN does not match the selected environment")


def reconcile_database(
    *,
    host: str,
    port: int,
    master_user: str,
    master_password: str,
    service: ServiceDatabase,
    password: str,
) -> None:
    role = sql_identifier(service.role)
    database = sql_identifier(service.database)
    password_literal = sql_literal(password)
    sql = f"""
SELECT format('CREATE ROLE %I LOGIN', {sql_literal(service.role)})
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = {sql_literal(service.role)}) \\gexec
ALTER ROLE {role} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION PASSWORD {password_literal};
SELECT format(
  'CREATE DATABASE %I OWNER %I',
  {sql_literal(service.database)}, {sql_literal(service.role)}
)
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = {sql_literal(service.database)}) \\gexec
ALTER DATABASE {database} OWNER TO {role};
REVOKE ALL ON DATABASE {database} FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE {database} TO {role};
"""
    process_env = os.environ.copy()
    process_env["PGPASSWORD"] = master_password
    run(
        [
            "psql",
            "--no-psqlrc",
            "--set=ON_ERROR_STOP=1",
            "--host",
            host,
            "--port",
            str(port),
            "--username",
            master_user,
            "--dbname",
            "postgres",
        ],
        stdin=sql,
        env=process_env,
    )


def revoke_cross_service_access(
    *, host: str, port: int, master_user: str, master_password: str
) -> None:
    statements: list[str] = []
    for owner in SERVICE_DATABASES:
        for other in SERVICE_DATABASES:
            if owner != other:
                database = sql_identifier(owner.database)
                role = sql_identifier(other.role)
                statements.append(f"REVOKE ALL ON DATABASE {database} FROM {role};")
    process_env = os.environ.copy()
    process_env["PGPASSWORD"] = master_password
    run(
        [
            "psql",
            "--no-psqlrc",
            "--set=ON_ERROR_STOP=1",
            "--host",
            host,
            "--port",
            str(port),
            "--username",
            master_user,
            "--dbname",
            "postgres",
        ],
        stdin="\n".join(statements),
        env=process_env,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=sorted(ALLOWED_ENVIRONMENTS))
    parser.add_argument("--region", required=True)
    parser.add_argument("--expected-account-id", required=True)
    parser.add_argument(
        "--rds-endpoint", required=True, help="Private RDS DNS name, without scheme or port"
    )
    parser.add_argument("--master-secret-id", required=True)
    parser.add_argument(
        "--service-secret-map",
        required=True,
        help="Terraform application_secret_arns JSON file, or - for stdin",
    )
    parser.add_argument(
        "--execute", action="store_true", help="Perform changes; omission is a no-network dry run"
    )
    parser.add_argument("--confirm", help="Must exactly equal --environment when --execute is used")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not ACCOUNT_PATTERN.fullmatch(args.expected_account_id):
        raise ValueError("--expected-account-id must be a 12-digit AWS account ID")
    if not REGION_PATTERN.fullmatch(args.region):
        raise ValueError("--region is not a valid AWS region identifier")
    if not RDS_HOST_PATTERN.fullmatch(args.rds_endpoint) or args.rds_endpoint.startswith(
        "localhost"
    ):
        raise ValueError("--rds-endpoint must be a private AWS RDS DNS name")
    raw_map = (
        sys.stdin.read()
        if args.service_secret_map == "-"
        else Path(args.service_secret_map).read_text(encoding="utf-8")
    )
    secret_map = json.loads(raw_map)
    if not isinstance(secret_map, dict):
        raise ValueError("Service secret map must be a JSON object")
    expected_keys = {service.key for service in SERVICE_DATABASES}
    if not expected_keys.issubset(secret_map) or not all(
        isinstance(secret_map[key], str) for key in expected_keys
    ):
        raise ValueError("Service secret map must contain all seven database secret ARNs")
    validate_secret_arn(
        args.master_secret_id, region=args.region, account_id=args.expected_account_id
    )
    for service in SERVICE_DATABASES:
        validate_secret_arn(
            str(secret_map[service.key]),
            region=args.region,
            account_id=args.expected_account_id,
            expected_name=f"roundready-{args.environment}-{service.key.replace('_', '-')}",
        )

    if not args.execute:
        print(
            "Dry run validated seven isolated service database targets; "
            "no AWS or database calls made."
        )
        return 0
    if args.confirm != args.environment:
        raise ValueError("--confirm must exactly match --environment")
    account = aws(
        args.region, ["sts", "get-caller-identity", "--query", "Account", "--output", "text"]
    )
    if account != args.expected_account_id:
        raise ValueError("Active AWS account does not match --expected-account-id")

    master = load_secret(args.region, args.master_secret_id)
    host = master.get("host")
    port = master.get("port", 5432)
    master_user = master.get("username")
    master_password = master.get("password")
    if (
        host != args.rds_endpoint
        or port != 5432
        or not isinstance(master_user, str)
        or not isinstance(master_password, str)
    ):
        raise ValueError("RDS master secret does not match the explicitly selected RDS endpoint")

    resolved: list[tuple[ServiceDatabase, str, str]] = []
    for service in SERVICE_DATABASES:
        secret_id = str(secret_map[service.key])
        aws(
            args.region,
            [
                "secretsmanager",
                "describe-secret",
                "--secret-id",
                secret_id,
                "--query",
                "ARN",
                "--output",
                "text",
            ],
        )
        if secret_has_version(args.region, secret_id):
            password = existing_password(load_secret(args.region, secret_id), service, host, port)
        else:
            password = secrets.token_urlsafe(48)
        resolved.append((service, secret_id, password))

    for service, _secret_id, password in resolved:
        reconcile_database(
            host=host,
            port=port,
            master_user=master_user,
            master_password=master_password,
            service=service,
            password=password,
        )
    revoke_cross_service_access(
        host=host, port=port, master_user=master_user, master_password=master_password
    )

    for service, secret_id, password in resolved:
        user = quote(service.role, safe="")
        encoded_password = quote(password, safe="")
        database_url = (
            f"postgresql+asyncpg://{user}:{encoded_password}@{host}:{port}/{service.database}"
        )
        payload = json.dumps({"database_url": database_url}, separators=(",", ":"))
        aws(
            args.region,
            [
                "secretsmanager",
                "put-secret-value",
                "--secret-id",
                secret_id,
                "--secret-string",
                "file:///dev/stdin",
                "--query",
                "ARN",
                "--output",
                "text",
            ],
            stdin=payload,
        )
    print(
        "Bootstrap completed for seven isolated service databases; "
        "secret values were not displayed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
