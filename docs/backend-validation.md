# RoundReady backend validation

Validation date: 2026-08-27 (Asia/Kolkata)

## Overall verdict: FAIL

The individual domain services have substantial, passing PostgreSQL/Testcontainers coverage and
all eight corrected Docker images start. The repository is not yet a working integrated backend:
the API gateway neither proxies public APIs nor validates JWTs, Compose does not run applications,
and the required business-event chains are not connected end to end.

## Executed validation summary

| Area | Result | Evidence |
| --- | --- | --- |
| Ruff formatting and lint | Pass | Repository-wide `ruff format --check` and `ruff check` |
| MyPy strict mode | Pass | Each service checked independently by `scripts/check.sh` |
| Unit/integration tests | Pass | 95 passed, 0 failed, 0 skipped after audit additions |
| Service image builds | Pass after fix | All eight Dockerfiles built locally |
| Service startup | Pass | All eight images returned `/health`; seven persistent services returned `/ready` 200 |
| Compose model | Partial | Compose config is valid but declares only PostgreSQL, Redis and RabbitMQ |
| Infrastructure health | Pass | All three containers healthy before and after restart |
| Clean/repeatable migrations | Pass | Seven service chains upgraded, downgraded to base, and upgraded again |
| Database isolation | Pass | Seven distinct databases/owners; auth credential was denied CONNECT to user DB |
| API gateway | Fail | No proxy routes; malformed bearer token returned HTTP 200 |
| Cross-service workflows | Fail | Required consumers/contracts are absent or incompatible |
| Real provider operations | Not executed | Razorpay and LiveKit used mocks/development abstractions only; no payments/messages/recordings |

The only recurring test warning is an upstream FastAPI/Starlette TestClient deprecation warning.
Dependency installation consistency passed `pip check`; a CVE audit was not executed because no
dependency-audit tool or lock file is present.

## Service validation

### API gateway — fail

- `/health`, standardized local errors, and HTTP correlation headers work.
- `/v1/session` checks only that the header starts with `Bearer `.
- Executed negative check: `Bearer definitely-not-a-jwt` returned 200.
- No routes proxy auth, user, interviewer, booking, payment, or interview APIs.
- Identity headers are therefore not derived, stripped, or forwarded by the gateway.
- Redis-backed rate limiting is only a `Protocol`; no limiter is instantiated or enforced.
- Revocation and disabled-account enforcement cannot occur at the public boundary.
- No explicit CORS policy exists. Starlette's default is restrictive, but intended browser origins
  are not documented or tested.

### Auth — component pass

Registration, duplicate handling, validation, Argon2 password hashing, login failure/success,
issuer/audience/role JWT claims, expiry, refresh rotation, refresh reuse family revocation, logout,
access-token revocation, disabled users, authorization and persistence passed against PostgreSQL.
RabbitMQ-unavailable behavior now proves outbox events remain unpublished with attempt/error state.
These controls are not enforced by the current gateway.

### User — component pass

Candidate profile and resume metadata CRUD, ownership, spoofed identity rejection, admin-safe lookup,
validation, schema ownership and persistence passed. Direct callers still depend on the shared
internal identity secret because the gateway does not currently construct trusted identity headers.

### Interviewer — component pass

Profile ownership, skills, verification transitions, admin authorization, recurring availability,
blockouts, event records and schema ownership passed against PostgreSQL.

### Booking — component pass

Slot generation, Redis holds, expiry, idempotency, ₹20,000-paise constraint, lifecycle transitions,
candidate/interviewer overlap exclusion constraints and persistence passed. A new concurrent test
executes two candidate booking workflows for one slot and proves exactly one 201 and one 409.
Redis-unavailable errors are now mapped to standardized 503 service errors.

The configured default test hold TTL is two seconds; production/local application configuration
defaults to the required 300 seconds.

### Payment — component pass

Order creation at 20,000 paise, provider abstraction, Razorpay test-credential enforcement, HMAC
webhook verification, captured/failed/refunded transitions, replay deduplication, failed-webhook
retry, ownership and persistence passed. Tests use mocks and never perform a real payment.

### Interview — component pass

The LiveKit abstraction, development-credential guard, room-scoped short-lived token claims,
assignment checks, attendance/reconnect data, lifecycle/no-show/technical-failure transitions,
rubrics, feedback scoring/ownership and outbox records passed. No LiveKit server call or recording
was executed; recording is disabled in adapter metadata.

### Notification — component and RabbitMQ pass

Templates, email/WhatsApp development providers, delivery records, duplicate events, exponential
retry, exhaustion, dead-letter persistence, versioned booking aliases and correlation persistence
passed. A real RabbitMQ event was consumed and persisted as `sent` by the development email
provider; no external email or WhatsApp message was sent.

## Infrastructure and database evidence

- Compose services: `postgres`, `redis`, `rabbitmq` only.
- PostgreSQL 16, Redis 7 and RabbitMQ 3.13 management containers reached healthy state.
- Authenticated checks returned PostgreSQL results, Redis `PONG`, RabbitMQ running/no alarms, and a
  successful management API response.
- Restarting all three containers preserved data and returned each to healthy state.
- Databases and owners: `roundready_auth`, `roundready_user`, `roundready_interviewer`,
  `roundready_booking`, `roundready_payment`, `roundready_interview`, and
  `roundready_notification`, each owned by its matching role.
- Cross-database check: `roundready_auth` was denied CONNECT to `roundready_user`.
- Clean databases contained expected service tables and indexes after migration. Every migration
  chain completed upgrade → downgrade base → upgrade.
- Docker images initially failed parsing because continuation lines contained two backslashes.
  This was fixed, `.dockerignore` was added, and migration files were added to persistent-service
  images.
- Celery is not declared or implemented. Workers use asyncio/aio-pika loops. This contradicts the
  supplied architecture inventory but was not introduced as a product feature during this audit.

## Cross-service flow results

| Required trace | Result | Finding |
| --- | --- | --- |
| `PaymentCaptured → booking confirmation` | Fail | Payment publishes `PaymentCaptured`; booking has no RabbitMQ consumer and its REST handler expects `payment.captured.v1`. |
| `BookingConfirmed → downstream processing` | Fail | Booking publishes `booking.BookingConfirmed.v1`; interview has only an admin HTTP create endpoint and no event consumer. |
| `InterviewCompleted → feedback workflow` | Partial | Completing a session permits assigned-interviewer feedback locally, but no event-driven downstream workflow consumes `InterviewCompleted`. |
| `FeedbackSubmitted → candidate notification` | Fail | Notification binds the event, but the real interview payload has no recipient address. Actual-shaped RabbitMQ input was persisted as `recipient_missing` dead letter. |

Actual-shaped `booking.BookingConfirmed.v1` was also consumed and dead-lettered as
`recipient_missing`; it additionally lacks the schedule/rubric data needed to provision an interview
session. RabbitMQ inspection showed only the audit notification queue and no booking payment-event
consumer.

## Failure scenarios

| Scenario | Result |
| --- | --- |
| PostgreSQL unavailable | Initially unstructured 500; fixed readiness handlers to return standardized 503 and added regression coverage |
| Redis unavailable | Initially unstructured 500; fixed hold store to map Redis failures to standardized 503 |
| RabbitMQ unavailable | Outbox publisher failure retained for retry with attempt/error metadata; worker startup recovery was not proven |
| Duplicate requests/events | Passed in auth, booking, payment, interview and notification tests |
| Payment webhook replay/invalid signature | Passed |
| Invalid JWT at auth service | Passed |
| Invalid JWT at gateway | Failed; malformed token accepted |
| Unauthorized roles and IDOR | Passed at domain services; public gateway enforcement absent |
| Expired slot hold | Passed |
| Candidate/interviewer no-show | Passed interview lifecycle tests |
| Technical failure | Passed interview lifecycle tests |

## Security findings

Critical/high:

1. Gateway authentication is cosmetic and accepts arbitrary bearer strings.
2. Gateway routing and trusted identity-header construction are absent.
3. Internal APIs rely on one shared secret. This is adequate only on a private network with the
   gateway stripping client-supplied identity headers; that boundary does not yet exist.
4. End-to-end payment/booking/interview/notification workflows are disconnected.

Medium:

1. Application config contains development database URL defaults with known credentials. Compose
   correctly requires environment credentials, but production should reject missing service URLs.
2. No implemented rate limiter; only an interface seam exists.
3. No dependency lock file or automated vulnerability audit is present.
4. Worker readiness and RabbitMQ reconnection on initial startup were not validated.
5. Explicit production CORS policy is absent.

Positive controls:

- Passwords use Argon2 and refresh tokens are hashed.
- Razorpay webhooks verify HMAC over raw bodies and deduplicate provider event IDs.
- Live/provider secrets use `SecretStr` and are not returned.
- Static log inspection found no password/token/provider-secret logging. Worker logs include event
  IDs/types only; a logging processor defect that overwrote explicit event correlations was fixed.
- SQLAlchemy parameter binding is used for runtime database operations; no user-controlled SQL
  string interpolation was found.
- Service-level ownership/admin tests cover the principal IDOR paths.
- `.env`, virtual environments, caches and private-key patterns are excluded from Docker/Git.

## Bugs fixed during audit

1. Corrected invalid continuation syntax in all eight Dockerfiles.
2. Added `.dockerignore` to exclude local environments, caches, Git data and secrets.
3. Included Alembic files in seven persistent-service images.
4. Standardized low-level PostgreSQL readiness failures as HTTP 503.
5. Standardized Redis hold-store failures as HTTP 503.
6. Preserved explicit asynchronous event correlation IDs in structured logs.
7. Added a true two-candidate concurrent same-slot booking test.
8. Added PostgreSQL readiness and RabbitMQ outbox failure regression tests.
9. Corrected architecture documentation that incorrectly claimed Compose ran all applications.

## Remaining blockers

1. Implement gateway proxying, real authentication/introspection, trusted identity-header handling,
   correlation propagation and rate limiting.
2. Add application/worker services and health dependencies to Compose if Compose is intended to
   run the integrated backend.
3. Define one consistent versioned event naming scheme and executable schemas.
4. Implement idempotent consumers for payment → booking and booking → interview workflows.
5. Supply notification-safe recipient/routing data without leaking PII into logs, or introduce an
   authorized recipient-resolution contract.
6. Define the `InterviewCompleted` workflow contract.
7. Decide whether Celery is actually required; current architecture uses direct aio-pika workers.
8. Add locked dependencies and an automated vulnerability scan.

## Exact commands used

```bash
PATH=/Users/jagadishav/Projects/RoundReady/.venv/bin:/usr/local/bin:/usr/bin:/bin bash scripts/check.sh
docker-compose --env-file .env.example -f infrastructure/docker-compose.yml config --quiet
docker-compose --env-file .env.example -f infrastructure/docker-compose.yml config --services
docker-compose --env-file .env.example -f infrastructure/docker-compose.yml up -d --wait
docker-compose --env-file .env.example -f infrastructure/docker-compose.yml ps
docker-compose --env-file .env.example -f infrastructure/docker-compose.yml restart redis rabbitmq postgres
docker exec roundready-postgres psql -U roundready_admin -d postgres -Atc "SELECT datname || ':' || pg_get_userbyid(datdba) FROM pg_database WHERE datname LIKE 'roundready_%' ORDER BY datname"
docker exec roundready-redis redis-cli --no-auth-warning -a change-me-local-redis ping
docker exec roundready-rabbitmq rabbitmq-diagnostics -q check_running
docker exec roundready-rabbitmq rabbitmq-diagnostics -q check_local_alarms
curl -fsS -u roundready:change-me-local-rabbitmq http://127.0.0.1:15672/api/overview
.venv/bin/pip check
```

All seven services were also run with their service-specific `PYTHONPATH`, database environment
variable, and this repeatability sequence:

```bash
.venv/bin/alembic -c services/<service>/alembic.ini upgrade head
.venv/bin/alembic -c services/<service>/alembic.ini downgrade base
.venv/bin/alembic -c services/<service>/alembic.ini upgrade head
```

All images were built and started with:

```bash
docker build -f services/<service>/Dockerfile -t roundready-audit-<service>:local .
docker run --rm --network roundready-local-network [service environment] roundready-audit-<service>:local
```

RabbitMQ integration used `RabbitEventPublisher` against
`amqp://roundready:***@localhost:5672/roundready`, the notification consumer container, and direct
PostgreSQL verification of delivery/dead-letter rows. Provider credentials were examples or mocks;
no real payment, email, WhatsApp message, LiveKit room, or recording was created.
