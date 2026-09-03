# Production configuration

RoundReady reads configuration from environment variables. The root `.env.example` and
`frontend/.env.example` are local-development templates only: **never reuse their values as
production credentials**. Production values must be injected into each process at runtime.
A deployment-specific secret-manager integration will be added with infrastructure deployment;
AWS Secrets Manager or another provider is not integrated yet.

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

## Intentional production provider blockers

Razorpay, LiveKit, Resend email, and Meta WhatsApp Cloud API production adapters are available
with their required runtime configuration. Their development/test modes remain unavailable in
production and must not be substituted during deployment.
