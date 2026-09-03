# PostgreSQL production usage

Each persistent RoundReady service owns a separate PostgreSQL database and receives only its own
`*_DATABASE_URL`. Never grant a service access to another service's database. Production URLs
must be injected at runtime, use the `postgresql+asyncpg` driver, include non-development
credentials, and point to non-local infrastructure. Never reuse `.env.example` credentials.

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
notification migration `20260902_0002_notification_ownership`. Database backup, restore, PITR,
retention, and recovery testing are deferred to RoundReady 14E.3.
