# RoundReady backend

Initial production-oriented microservice foundation for a real-human technical mock interview
platform. It includes eight independently runnable FastAPI applications, service-owned
PostgreSQL models and Alembic environments, Redis and RabbitMQ infrastructure, shared API and
event contracts, JSON logging, correlation IDs, and optional OpenTelemetry instrumentation.

## Quick start

Requirements: Python 3.12+, Docker, and Docker Compose.

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
docker-compose --env-file .env -f infrastructure/docker-compose.yml up -d
```

The infrastructure exposes PostgreSQL on 5432, Redis on 6379, AMQP on 5672, and RabbitMQ's
management UI on 15672 by default. Local credentials in `.env.example` are placeholders and
must not be reused outside local development. Applications run independently using their
existing service Dockerfiles or Python entry points.

Run all checks with `bash scripts/check.sh`. See [architecture](docs/architecture.md),
[API errors](docs/api-errors.md), and [events](docs/events.md).
Infrastructure lifecycle and inspection commands are in the
[local development guide](docs/local-development.md).
Production environment requirements and current provider blockers are documented in the
[production configuration guide](docs/production-configuration.md).
