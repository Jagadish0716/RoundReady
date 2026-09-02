# RoundReady architecture

## Context and principles

RoundReady coordinates paid, real-human, 15–20 minute technical mock interviews for the
Indian market. Candidates pay ₹200 (stored as 20,000 paise in INR). The platform has
Candidate, Interviewer, and Admin roles and initially supports DevOps, AWS, Azure, Backend,
Full Stack, QA, and Tech Support. Services follow 12-factor configuration, use UUID primary
keys and UTC timestamps, and never access another service's database.

## Service boundaries

| Service | Owns | Does not own |
| --- | --- | --- |
| API gateway | Public proxy routing, auth introspection, correlation IDs, Redis rate limiting | Identity records or business data |
| Auth | Credentials, password hashes, roles, access/refresh token lifecycle and revocation | User or interviewer profiles |
| User | Candidate account and profile information | Credentials, bookings, or payments |
| Interviewer | Interviewer profile, domain skills, verification and availability | Booking decisions or sessions |
| Booking | Slots consumed for bookings, temporary holds, scheduling, state transitions, reschedule/no-show policy | Payment capture or video rooms |
| Payment | ₹200 payment records, idempotency keys, webhook receipts and refunds | Booking state or candidate profiles |
| Interview | Sessions, room references, attendance, rubrics and feedback reports | Scheduling or payment settlement |
| Notification | Email/WhatsApp delivery records, retry attempts and event consumers | Business workflow state |

Each stateful service has its own SQLAlchemy metadata, session factory, Alembic environment,
database URL and PostgreSQL database. Cross-service foreign identifiers are plain UUIDs, not
database foreign keys. This prevents accidental joins and preserves ownership.

## Communication

The gateway is the only public backend entry point. It validates tokens through auth-service,
strips supplied identity headers, and constructs trusted `X-User-ID`, `X-User-Role`, and
`X-Correlation-ID` headers. Internal REST calls
are reserved for queries requiring an immediate response, such as fetching availability or
creating a checkout. They use bounded timeouts, propagate correlation IDs, and must not form
long synchronous chains.

RabbitMQ topic events carry the shared `EventEnvelope`. Initial contracts planned for
versioned implementation are:

- `interviewer.availability.changed.v1`
- `booking.held.v1`, `booking.confirmed.v1`, `booking.cancelled.v1`, `booking.no_show.v1`
- `payment.captured.v1`, `payment.failed.v1`, `payment.refunded.v1`
- `interview.room_created.v1`, `interview.completed.v1`, `feedback.submitted.v1`
- `notification.delivery_failed.v1`

Publishers use a transactional outbox in their own database. Consumers deduplicate by `event_id`, acknowledge only after committing,
retry transient failures with exponential backoff, and dead-letter permanent failures.
Schema evolution is additive within an event version; breaking changes increment the
version. Payload schemas remain owned and documented by the producer.

## Security boundaries

TLS terminates at the production edge and service-to-service traffic uses private networking.
The gateway verifies short-lived JWT access tokens; auth alone signs tokens and stores only
hashed refresh tokens. Roles are coarse authentication claims; each service still performs
resource-level authorization. Provider webhook endpoints verify signatures against the raw
body, record provider event IDs, and process idempotently. Secrets come from environment or a
production secret manager and are never committed. Logs exclude credentials, tokens,
provider signatures, and personal data by default. Admin operations require explicit audit
events. PostgreSQL users and RabbitMQ credentials are separate per service in production.

## Reliability and observability

`/health` reports process liveness and `/ready` is the readiness contract. JSON logs include
UTC timestamps, service name where emitted, and correlation IDs. OpenTelemetry FastAPI
instrumentation is switchable by configuration; production supplies an OTLP exporter and
sampling policy. Network operations need timeouts, retry budgets, and circuit breaking at
call sites. Payment, booking, and notification commands require idempotency keys.

## Local development

Copy `.env.example` to `.env`, install Python 3.12 and the `dev` extra, then start
`infrastructure/docker-compose.yml`. Compose runs PostgreSQL 16, Redis 7, RabbitMQ 3, all APIs,
and the aio-pika/outbox workers. Only the gateway exposes an application port; API containers run
migrations before startup. `scripts/check.sh` formats-checks,
lints, strictly type-checks, and tests every service in isolation, avoiding import collisions
between deliberately independent `app` packages.

Gateway identity and service-to-service credentials are separate, environment-configured secrets.
aio-pika is the deliberate messaging implementation; Celery is not required by the current
acknowledgement, durable queue, reconnect and dead-letter design.

## Future production deployment

Container images will be built once per service, scanned, signed, and promoted through
environments. A managed PostgreSQL cluster may host separate databases initially, with
separate credentials and migration jobs; high-volume services can later receive dedicated
clusters. Use managed Redis and RabbitMQ, multiple stateless replicas, autoscaling, disruption
budgets, network policies, external secret management, centralized telemetry, backups with
restore drills, and multi-AZ placement. Kubernetes manifests are intentionally deferred until
runtime traffic, scaling, and operational requirements are known.
