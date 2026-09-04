# Production configuration

RoundReady reads configuration from environment variables. The root `.env.example` and
`frontend/.env.example` are local-development templates only: **never reuse their values as
production credentials**. Production values must be injected into each process at runtime.
EKS runtime delivery uses AWS Secrets Manager through EKS Pod Identity and the AWS Secrets Store
CSI provider. CSI synchronization creates service-owned Kubernetes Secrets dynamically because
the applications consume environment variables; no secret values are stored in Git.

## Runtime behavior

`ENVIRONMENT` accepts only `development`, `test`, or `production`. In production, backend
services fail at startup when required URLs or credentials are missing, weak, placeholders, or
point to localhost. Development and test retain their local defaults. The supplied Compose file
is explicitly development-only and pins application containers to `ENVIRONMENT=development`.

The frontend follows Next.js `NODE_ENV`. A production build requires an explicit HTTPS
`NEXT_PUBLIC_API_BASE_URL`, rejects localhost and embedded URL credentials, and refuses a build
that enables development payment completion.

## Required production configuration

Secret values below must be generated independently and delivered through runtime injection.
Non-secret identifiers and URLs must still be explicit in production.

| Group             | Variables                                                                                                                                                                   | Classification                                                           |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Runtime           | `ENVIRONMENT=production`, `LOG_LEVEL`                                                                                                                                       | Non-secret; environment is required                                      |
| JWT/Auth          | `JWT_SIGNING_KEY`, `JWT_VERIFICATION_KEY` for RS256                                                                                                                         | Secret; signing key required, verification key required for RS256        |
| JWT/Auth          | `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_AUDIENCE`, `ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_SECONDS`                                                                      | Non-secret; issuer and audience must be explicit                         |
| PostgreSQL        | `AUTH_DATABASE_URL`, `USER_DATABASE_URL`, `INTERVIEWER_DATABASE_URL`, `BOOKING_DATABASE_URL`, `PAYMENT_DATABASE_URL`, `INTERVIEW_DATABASE_URL`, `NOTIFICATION_DATABASE_URL` | Secret-bearing URLs; the owning service receives only its own URL        |
| Redis             | `REDIS_URL` for the gateway, `BOOKING_REDIS_URL` for booking                                                                                                                | Secret-bearing URLs; authenticated and non-local                         |
| RabbitMQ          | `RABBITMQ_URL`                                                                                                                                                              | Secret-bearing URL; required by each event-producing/consuming service   |
| RabbitMQ          | `RABBITMQ_EXCHANGE`, service event queue, `RABBITMQ_DEAD_LETTER_EXCHANGE`                                                                                                   | Non-secret topology names; defaults may be retained                      |
| Internal services | `INTERNAL_IDENTITY_SECRET`, `INTERNAL_SERVICE_SECRET`, `NOTIFICATION_INTERNAL_IDENTITY_SECRET`                                                                              | Secrets; gateway/service values must match their intended trust boundary |
| Gateway routing   | `AUTH_SERVICE_URL`, `USER_SERVICE_URL`, `INTERVIEWER_SERVICE_URL`, `BOOKING_SERVICE_URL`, `PAYMENT_SERVICE_URL`, `INTERVIEW_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`        | Non-secret, explicit non-local service URLs                              |
| Gateway policy    | `CORS_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `HSTS_ENABLED`, `MAX_REQUEST_BODY_BYTES`                                                                                           | Non-secret                                                               |
| Gateway abuse     | `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_REQUESTS`, `AUTH_RATE_LIMIT_WINDOW_SECONDS`                                                          | Non-secret                                                               |
| Payment           | `PAYMENT_PROVIDER`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_BASE_URL`, `RAZORPAY_TEST_MODE`                                          | Provider selector non-secret; provider credentials/webhook secret secret |
| Interview         | `VIDEO_PROVIDER`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_TEST_MODE`, `PARTICIPANT_TOKEN_TTL_SECONDS`                                              | URL/mode/TTL non-secret; API credentials secret                          |
| Notifications     | `EMAIL_PROVIDER`, `RESEND_API_BASE_URL`, `RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`                                                                                             | Selector/URL/sender non-secret; API key secret                           |
| Notifications     | `WHATSAPP_PROVIDER`, `WHATSAPP_API_BASE_URL`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEMPLATE_NAME`, `WHATSAPP_TEMPLATE_LANGUAGE`                   | Selector/URL/template metadata non-secret; access token secret           |
| Notifications     | `USER_SERVICE_URL`, `INTERNAL_SERVICE_SECRET`, `PROVIDER_TIMEOUT_SECONDS`                                                                                                   | URL/timeout non-secret; internal credential secret                       |
| Frontend          | `NEXT_PUBLIC_API_BASE_URL`                                                                                                                                                  | Public, non-secret; required HTTPS gateway URL                           |
| Frontend          | `NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS`                                                                                                                                   | Public, non-secret; must not be enabled in production                    |

Database administrator variables and individual database owner variables in `.env.example` are
inputs to the local Compose PostgreSQL initializer. In a production deployment, provision each
database separately and inject only the resulting service-owned database URL into that service.
Likewise, `REDIS_PASSWORD`, `RABBITMQ_USER`, and `RABBITMQ_PASSWORD` are local Compose inputs;
production applications consume provider-issued connection URLs rather than this template.
Pool sizing, readiness, and explicit migration execution are covered in the
[PostgreSQL production guide](postgresql-production.md).

Redis and RabbitMQ production URLs must use authenticated, non-local endpoints. Use `rediss://`
for Redis TLS and `amqps://` for RabbitMQ TLS. Clients enforce bounded connection and socket
timeouts, Redis health checks, and RabbitMQ reconnect backoff. Redis-dependent API readiness
checks include a Redis ping; liveness remains independent of dependencies.

AWS environments use private ElastiCache Valkey-compatible endpoints and private Amazon MQ
RabbitMQ endpoints. Terraform generates their credentials and stores them in Secrets Manager;
plaintext credentials are never output. Because both managed-service APIs require credential
values during provisioning, those values remain sensitive Terraform state. The S3 backend must be
encrypted and access restricted to infrastructure operators. EKS workloads retrieve credentials
through least-privilege Pod Identity and the single approved Secrets Store CSI/AWS provider path.
Synchronized Kubernetes Secrets require encrypted etcd, restricted RBAC, and coordinated pod
restarts after rotation.

Before workload deployment, the managed credential secret versions must be extended with
application-ready authenticated `rediss://` and `amqps://` URLs built from their private endpoints
and credentials. Do not fall back to plaintext protocols. Redis is used only
for ephemeral coordination; RabbitMQ remains the durable asynchronous transport and application
code continues to declare its exchange, queue, retry, and dead-letter topology.

## AWS workload identity and secret ownership

Production secret delivery follows this path:

```text
provider operator or database bootstrap
  -> environment-specific AWS Secrets Manager secret
  -> exact secret ARN in one service IAM policy
  -> EKS Pod Identity association
  -> matching Kubernetes ServiceAccount
  -> workload runtime configuration
```

Terraform creates secret containers for each service database, JWT signing and verification,
gateway identity, notification-to-user internal authentication, Razorpay, LiveKit, Resend, and Meta
WhatsApp. It creates no placeholder secret versions and never retrieves their values. Provider
operators populate provider bundles; controlled database bootstrap populates service database
credentials. Public endpoints, issuer names, TTLs, queue names, and other non-secret configuration
remain normal runtime configuration rather than Secrets Manager values.

Workload access is service-specific:

- API gateway: JWT verification, gateway identity, and Redis credentials.
- Auth: auth database, JWT signing/verification, gateway identity, and RabbitMQ credentials.
- User: user database, gateway identity, and notification-to-user internal credential.
- Interviewer: interviewer database, gateway identity, and RabbitMQ credentials.
- Booking: booking database, gateway identity, Redis, and RabbitMQ credentials.
- Payment: payment database, gateway identity, Razorpay, and RabbitMQ credentials.
- Interview: interview database, gateway identity, LiveKit, and RabbitMQ credentials.
- Notification: notification database, both internal trust credentials, Resend, Meta WhatsApp, and
  RabbitMQ credentials.

Each IAM role trusts only `pods.eks.amazonaws.com` and the exact EKS cluster ARN, configured
namespace, and ServiceAccount session tags. Its policy grants only `DescribeSecret` and
`GetSecretValue` for its listed ARNs. There are no application IAM users, access keys, shared
workload roles, wildcard secret permissions, or EC2 trust. AWS-side Pod Identity associations may
exist before ServiceAccounts; future Kubernetes deployment must create the exact names and install
the Pod Identity Agent.

The RDS master secret is exclusively for controlled bootstrap and is not granted to application
roles. Bootstrap creates the seven logical databases and isolated roles, stores each service URL in
its own empty Terraform-created secret container, runs Alembic once, and only then deploys workloads.
Terraform never runs SQL or stores those service passwords.

Terraform state is not the application secret-delivery mechanism. Redis and RabbitMQ provisioning
APIs require generated credentials in Terraform state, so the remote S3 state must be encrypted and
restricted to infrastructure operators; plaintext credentials must never be output or logged.
Runtime workloads resolve Secrets Manager values using temporary Pod Identity credentials rather
than baking secrets into images or manifests.

Rotation remains coordinated rather than automatic in this phase. Provider credentials follow the
provider's rotation process; database roles rotate with service connection rollout; Redis AUTH uses
the supported staged token process; RabbitMQ rotation updates the broker and secret together before
consumers are restarted. Automatic rotation Lambdas are intentionally deferred.

The gateway's production `CORS_ORIGINS` must be a non-empty list of exact HTTPS frontend
origins; wildcard and localhost origins are rejected. `CORS_ALLOW_CREDENTIALS` is explicit and
must match the frontend authentication design. `HSTS_ENABLED` should be enabled only when the
public gateway is served exclusively over HTTPS. The gateway does not trust client-supplied
`X-Forwarded-*` headers; deployment must provide the actual peer address, scheme, and host at
the trusted edge. Public login, registration, and refresh requests use their own bounded Redis
rate-limit window, while authenticated traffic uses the general gateway limit. Oversized
request bodies are rejected by `MAX_REQUEST_BODY_BYTES` (default 1 MiB).

## Observability

Production backend logs are JSON with UTC timestamps, level, service, environment, message,
correlation ID, and request method/path/status/duration when applicable. Health probes are kept
quiet at normal request-log level. `X-Correlation-ID` is accepted only when bounded and composed
of safe identifier characters; invalid or oversized values are replaced with a generated ID and
the ID is returned and propagated downstream. The business `correlation_id` in event envelopes
remains distinct from an OpenTelemetry trace ID.

Set `TELEMETRY_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` to export traces. Telemetry is
disabled by default and does not require a collector unless explicitly enabled. FastAPI,
outbound HTTPX, and RabbitMQ publishing are instrumented where configured; exporter failures do
not stop application requests. Never log passwords, tokens, authorization headers, cookies,
provider secrets/signatures, database or broker credentials, or request/response bodies.

## Development-only behavior

Development payment completion is available only when explicitly enabled in development/test.
Production disables it at both frontend and payment-service boundaries. Mock notification
delivery, the development payment provider, Razorpay test mode, and local/test video behavior
cannot activate in production. The browser receives no JWT signing material, internal service
credentials, database/Redis/RabbitMQ credentials, webhook secret, LiveKit secret, or messaging
provider secret; it communicates only with the configured API gateway.

Prometheus metrics are available at `/metrics` for each backend service. In production this
endpoint must be restricted to the internal monitoring network at the deployment edge; it is
not a public API. Development scraping remains available locally. HTTP metrics use only method,
normalized route template, and status class labels, never user, booking, payment, email, phone,
or raw URL values. Health and readiness probes are excluded to avoid scrape noise.

Minimum dashboards should show request rate, 5xx rate, latency, readiness, outbox backlog and
publish failures, consumer failures/requeues/DLQ activity, plus bookings, payment outcomes,
completed interviews, feedback submissions, and notification failures. Application metrics do
not replace PostgreSQL, Redis, RabbitMQ, host, or container exporters.

Initial alert guidance, to tune after real traffic: readiness failing for 5 minutes; 5xx above
5% for 10 minutes; p95 API latency above 1 second for 10 minutes; outbox backlog growing for
15 minutes; sustained broker publish/consumer failures or requeues for 10 minutes; any DLQ
activity; payment failures above 10% for 10 minutes; and notification failures above 10% for
10 minutes. These are starting thresholds, not paging integrations.

## Intentional production provider blockers

Razorpay, LiveKit, Resend email, and Meta WhatsApp Cloud API production adapters are available
with their required runtime configuration. Their development/test modes remain unavailable in
production and must not be substituted during deployment.
