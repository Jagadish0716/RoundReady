# PostgreSQL production usage

Each persistent RoundReady service owns a separate PostgreSQL database and receives only its own
`*_DATABASE_URL`. Never grant a service access to another service's database. Production URLs
must be injected at runtime, use the `postgresql+asyncpg` driver, include non-development
credentials, and point to non-local infrastructure. Never reuse `.env.example` credentials.

## Amazon RDS topology

Each environment uses one private Amazon RDS PostgreSQL instance to control early-stage cost while
retaining service ownership through separate logical databases and roles. The expected databases
are `roundready_auth`, `roundready_user`, `roundready_interviewer`, `roundready_booking`,
`roundready_payment`, `roundready_interview`, and `roundready_notification`. Every service receives
a distinct login that owns only its database; application processes never use the RDS master user.
Services can move to dedicated instances later if measured scale, compliance, or stronger physical
isolation requires it.

RDS is placed only in private data subnets and is never publicly accessible. Its security group
allows PostgreSQL 5432 only from the EKS application security group, with no CIDR-based public or
VPC-wide ingress. The current boundary is the EKS cluster security group associated with managed
nodes; pod-level security groups may narrow this further when Kubernetes workloads are introduced.
Applications use the RDS DNS endpoint, never an instance IP.

Terraform enables encrypted gp3 storage with autoscaling headroom and a rotating KMS key. RDS
generates and maintains the master password in Secrets Manager. Terraform exposes only the secret
ARN and never reads the credential value. A controlled bootstrap process retrieves that credential
at runtime; service passwords must likewise be generated and stored outside Terraform state.

The deployment order is:

1. Provision the RDS instance.
2. Securely retrieve the master credential for a one-time controlled bootstrap job.
3. Create each logical database and its isolated owner role; revoke unintended cross-database access.
4. Populate each service's environment-specific Terraform-created Secrets Manager container with
   only that service URL/credential.
5. Run each service's `alembic upgrade head` exactly once.
6. Deploy application replicas and verify their `/ready` endpoints.

Production uses Multi-AZ failover, deletion protection, 14-day automated backup retention, and a
required final snapshot. Development uses a smaller single-AZ instance, short retention, and may
skip its final snapshot. Application connection recovery after an RDS failover remains bounded by
the existing pool pre-ping, connection timeout, and retry behavior; `/ready` fails while PostgreSQL
is unavailable. Snapshots complement, but do not replace, tested logical restore procedures.

PostgreSQL log export, Enhanced Monitoring, and Performance Insights are enabled selectively by
environment to balance visibility with cost. Statement-level verbose logging is intentionally not
enabled. Major cost drivers are the instance class, Multi-AZ standby, gp3 allocation/autoscaling,
retained backup storage, monitoring retention, and cross-AZ/data-transfer traffic.

## Connections and pools

Every service uses the same bounded SQLAlchemy engine settings, configurable independently per
process:

| Variable                           | Default | Purpose                                                 |
| ---------------------------------- | ------: | ------------------------------------------------------- |
| `DATABASE_POOLING`                 |  `true` | Use SQLAlchemy's async queue pool; tests may disable it |
| `DATABASE_POOL_SIZE`               |     `5` | Persistent connections per process                      |
| `DATABASE_MAX_OVERFLOW`            |    `10` | Temporary connections above pool size                   |
| `DATABASE_POOL_TIMEOUT_SECONDS`    |    `30` | Maximum wait for a pooled connection                    |
| `DATABASE_POOL_RECYCLE_SECONDS`    |  `1800` | Recycle aged connections                                |
| `DATABASE_POOL_PRE_PING`           |  `true` | Detect stale connections before checkout                |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` |    `10` | Bound initial PostgreSQL connection attempts            |

Capacity must be calculated across all replicas before increasing pool limits. Request sessions
are closed after use and explicitly rolled back when request handling fails. `/health` remains a
process liveness check; `/ready` executes `SELECT 1` and returns `503` when PostgreSQL cannot
serve requests. Pool exhaustion and connection failures remain bounded and surface through the
normal standardized error handling; there is no infinite connection retry loop.

## Production migrations

Run migrations once as an explicit deployment step for each service, before starting or rolling
out application replicas:

```bash
PYTHONPATH=services/<service>:libs \
  alembic -c services/<service>/alembic.ini upgrade head
```

Supply that service's production database URL to the migration process. A non-zero migration
exit must block deployment. Do not run automatic downgrades. Production application replicas
must start the application directly and must not each execute Alembic. The repository's Docker
Compose file runs `alembic upgrade head` during container startup only because it is explicitly a
single-host development environment; this is not the production deployment strategy.

The current migration graph retains booking migration `0003_reusable_failed_slots` and
notification migration `20260902_0002_notification_ownership`. Each of the seven migration
directories currently has one head.

## Backups

Run a scheduled logical backup for each service-owned database. Use `pg_dump` per database;
use `pg_dumpall --globals-only` separately only when a controlled record of cluster roles and
tablespaces is required. Do not use a single application credential for all databases. Supply
the service URL through a runtime secret mechanism or `PGPASSFILE`; never put a password in a
script or committed environment file.

The repository helper creates a custom-format dump with a UTC timestamp, service, and database
in its filename:

```bash
scripts/postgres-backup.sh --url "$AUTH_DATABASE_URL" --service auth --output-dir /secure/backups
```

Store backups encrypted at rest and in transit, with access limited to recovery operators.
Choose retention with the operational owner; a practical starting point is daily backups for
at least 30 days and monthly backups for a longer business-required period. Record the source
cluster, service/database, timestamp, and backup verification result. Storage provisioning and
encryption-key management are deployment responsibilities, not part of this repository.

## Restore and verification

Create an empty database owned by the correct service role, then restore the custom dump into
the explicit target URL. For a recovery or staging database, use a distinct database name and
credentials; never point one service at another service's database:

```bash
scripts/postgres-restore.sh --backup /secure/backups/20260903T010203Z_auth_roundready_auth.dump \
  --target-url "$AUTH_RECOVERY_DATABASE_URL"
```

The restore helper refuses target names containing `prod`, `production`, or `live` unless
`--allow-production-target` is supplied deliberately. It does not clean an existing database,
so an empty target is required and accidental overwrite is avoided. Credentials are supplied
at runtime and are not printed or stored by the helper.

Verify every restore with connectivity, table presence, and the service's current Alembic
revision:

```bash
scripts/postgres-verify-restore.sh --url "$AUTH_RECOVERY_DATABASE_URL" \
  --service services/auth-service
```

The lightweight procedure is: create a dump, restore it into a temporary/test database, run
this verification helper, and confirm critical tables for that service. The helper's table
count is only a sanity check; recovery operators must also check the expected service tables.
Do not require production credentials for this procedure. A local smoke can use the Compose
database and a temporary database created with the local administrator role.

## Migration deployment and rollback

For every production release, use this order:

1. Create and record a database backup/checkpoint.
2. Run `alembic upgrade head` once for each service, as an explicit deployment job.
3. Verify the migration head and recovery checks.
4. Deploy application replicas.

A migration command failure stops deployment. Do not run migrations automatically in multiple
application replicas. The development Compose startup migration is a local-only exception.

Application rollback means deploying the previous application version when the schema remains
backward compatible. If a migration or data change cannot safely be reversed, use database
recovery from a verified backup into the planned target, then redirect the compatible previous
application version. Alembic downgrade is allowed only for a specific migration with a tested
safe downgrade; never automate destructive downgrades.

Future migrations should be additive first. Use expand/contract for breaking changes: add new
structures, deploy compatibility code, backfill separately when needed, and remove or rename
old columns only after no deployed version depends on them. Do not drop or rename a column in
the same deployment that removes compatibility.

## Recovery checklist

- Database is reachable with the intended service credential.
- Expected Alembic head is present.
- Critical service tables exist.
- Application `/ready` succeeds after the recovered database is attached.
- No cross-service database was restored or granted.
- Backup source, timestamp, target, and verification result are recorded.
