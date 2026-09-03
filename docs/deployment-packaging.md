# Production deployment packaging

RoundReady production deployments are intended for an external orchestrator. The repository's
Docker Compose file is local development and integration tooling only; it is not the final
production platform. Compose keeps useful local dependencies, startup ordering, and health
checks, including its development-only migration-on-start behavior.

## Image roles

Build one image per service from its Dockerfile and run one intended process per container:

- API images run one Uvicorn FastAPI process bound to `0.0.0.0:8000`.
- Worker images reuse the service image but run one explicit outbox, maintenance, event-consumer,
  or notification-consumer module.
- The frontend image runs the standalone Next.js server on port `3000`.

Do not add Uvicorn worker processes inside a container when the orchestrator is responsible for
replica scaling. API and worker roles remain separate. Worker containers are long-lived and
must be restarted by the orchestrator after an unexpected exit.

## Startup and migrations

Inject configuration and secrets into each container at runtime. Production images do not
contain `.env` files, credentials, application data, or persistent database files. Invalid
production configuration fails during process startup. Containers do not require interactive
input or development reload mode.

Run one explicit migration job per service before deploying replicas:

```text
backup/checkpoint -> alembic upgrade head once -> verify head/readiness -> deploy replicas
```

A migration failure stops deployment. Production API replicas start directly with Uvicorn and
must not run Alembic. See `docs/postgresql-production.md` for the migration and recovery
procedure.

## Probes and shutdown

Use `/health` for lightweight liveness, `/ready` for required dependency readiness, and
`/metrics` for internal monitoring only. The future orchestrator's probes are authoritative;
the local Compose health checks are not a production deployment contract.

On termination, allow the server or worker its graceful shutdown period. FastAPI closes request
resources, worker `finally` blocks close Redis/RabbitMQ resources, and telemetry exporters are
flushed/shut down when enabled. Workers acknowledge messages only after successful processing;
termination before acknowledgement leaves work for broker redelivery.

## Runtime behavior and naming

Containers write logs to stdout/stderr using the structured logging configuration. They run as
non-root users with a fixed `/app` working directory and no required application-source writes.
Temporary runtime files belong in `/tmp`; business data, uploads, secrets, and database files
belong in external managed services or volumes owned by the deployment.

Use immutable image versions, never `latest` in production:

```text
<registry>/<service>:<immutable-version>
```

Use a release version or Git commit SHA. Registry digest pinning, signing, and deployment
secret-manager integration remain CI/deployment responsibilities.