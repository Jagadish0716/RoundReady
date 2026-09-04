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

Terraform creates separate private ECR repositories for the frontend, gateway, and each of the
seven backend services under the environment-qualified `roundready-<environment>/` namespace.
Workers reuse their service repository. Tags are immutable, images are encrypted at rest, and basic
scan-on-push is enabled. Lifecycle policies retain recent tagged releases for rollback while aging
out old untagged images. CI push permissions, image promotion, signing, and deployment remain future
work; Terraform creates no registry credentials and does not push images.

```text
developer or future CI -> immutable SHA/release image -> private ECR -> future EKS deployment
```

Vulnerability findings require review and policy; scanning does not guarantee that an image is
safe. Production retains 30 tagged images per component and disables forced deletion.

## Public ingress deployment order

Terraform first validates the existing Route 53 zone, completes ACM DNS validation, and exposes the
certificate and Load Balancer Controller IAM role ARNs. Kubernetes deployment then installs the EKS
Pod Identity Agent and AWS Load Balancer Controller, creates the controller ServiceAccount matching
Terraform's Pod Identity association, and applies the frontend/API-gateway Ingress. Only after the controller has
created the ALB should deployment automation create Route 53 alias records using the real ALB DNS
name and canonical zone ID. Set Terraform's `public_alb_dns_name` and
`public_alb_zone_id` together to create the two alias records. The complete
fail-closed render and handoff procedure is in `docs/public-ingress.md`.

The Ingress must use public subnets, HTTPS 443, the Terraform ACM certificate, a modern AWS TLS
policy, and `/ready` target checks. Optional port 80 is redirect-only. It routes only the configured
frontend and API gateway hostnames; backend services and workers remain private. Production gateway
`CORS_ORIGINS` must exactly match the frontend HTTPS origin, and the frontend API base URL must be
the configured HTTPS API hostname.

## AWS observability handoff

Terraform creates one environment-qualified CloudWatch log group for future application logs with
7-day dev, 30-day staging, and 90-day production retention. Kubernetes deployment will later add a
log collector that forwards container stdout/stderr JSON; Terraform does not install Fluent Bit,
CloudWatch Agent, Container Insights, or any workload add-on here.

```text
EKS workload stdout -> future log collector -> CloudWatch application log group
private /metrics -> future Prometheus scraper
application traces -> optional future OTLP collector -> selected telemetry backend
```

Production has initial AWS-native alarms for RDS CPU and free storage because their metrics and
dimensions exist independently of workload deployment. They publish to an SNS topic with no fake
email, phone, Slack, or paging subscription. Operations will attach real recipients later. Redis,
RabbitMQ, and application alarms remain deferred until metric dimensions/export paths are verified
in the deployed environment. `/metrics` remains private.

CloudWatch ingestion and retention, custom metrics, alarms, Container Insights, and trace volume are
material cost drivers. Retention is bounded and high-volume agents, custom metric export, enhanced
Inspector scanning, and tracing backends are not enabled blindly.
