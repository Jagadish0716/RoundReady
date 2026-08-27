# Local development infrastructure

The local stack contains PostgreSQL 16, Redis 7, and RabbitMQ 3.13 with its management UI.
Application containers are intentionally not part of this Compose file; run each FastAPI
service from its own directory or with its existing Dockerfile.

## Configure the environment

From the repository root:

```bash
cp .env.example .env
```

The checked-in example contains local-only placeholder credentials. Change them in `.env` if
the machine is shared. `.env` is ignored by Git. Compose requires the PostgreSQL role
passwords, Redis password, and RabbitMQ credentials to be present rather than silently using
insecure defaults.

Database URLs in `.env.example` use `localhost`, for applications running directly on the
host. An application running in a container attached to `roundready-local-network` must use
`roundready-postgres`, `roundready-redis`, and `roundready-rabbitmq` as hostnames.

Redis is one shared instance with logical database allocation:

| Logical DB | Owner/usage |
| --- | --- |
| 0 | API gateway rate limiting |
| 1 | Auth token lifecycle |
| 2 | Booking holds |
| 3 | Payment idempotency/cache |
| 4 | Notification retry/cache |

Keys should additionally start with `<service-name>:`. Logical databases prevent key
collisions for local development; they are not security boundaries.

RabbitMQ exchange, dead-letter exchange, and queue names are environment variables. Services
declare their own durable queues and bindings when consumers are implemented; infrastructure
does not predeclare business topology.

## Start infrastructure

```bash
docker-compose --env-file .env -f infrastructure/docker-compose.yml up -d
docker-compose --env-file .env -f infrastructure/docker-compose.yml ps
```

Wait for all three containers to report `healthy`. Data survives container recreation in
the named `roundready-*-data` volumes.

## Stop infrastructure

Stop containers while retaining data:

```bash
docker-compose --env-file .env -f infrastructure/docker-compose.yml down
```

## Reset infrastructure

This permanently deletes local PostgreSQL, Redis, and RabbitMQ data, then recreates it:

```bash
docker-compose --env-file .env -f infrastructure/docker-compose.yml down --volumes
docker-compose --env-file .env -f infrastructure/docker-compose.yml up -d
```

The PostgreSQL initialization script runs only when its data volume is empty. Reset the stack
after changing database names, owners, or passwords.

## Inspect PostgreSQL

List databases and owners:

```bash
docker exec -it roundready-postgres psql -U roundready_admin -d postgres -c '\l'
```

Connect with a service owner (the command prompts for the password from `.env`):

```bash
docker exec -it roundready-postgres psql -W -U roundready_booking -d roundready_booking
```

Verify isolation by attempting another database; it must fail after entering the booking
password:

```bash
docker exec -it roundready-postgres psql -W -U roundready_booking -d roundready_payment
```

Replace example usernames if they were changed in `.env`.

## Inspect RabbitMQ

Open `http://localhost:15672` and sign in with `RABBITMQ_USER` and `RABBITMQ_PASSWORD`.
The configured virtual host is `RABBITMQ_VHOST`. CLI status is available with:

```bash
docker exec roundready-rabbitmq rabbitmq-diagnostics -q check_running
docker exec roundready-rabbitmq rabbitmqctl list_queues -p roundready
```

## Inspect Redis

Use the password from `.env`; this avoids placing it in shell history:

```bash
docker exec -it roundready-redis redis-cli
AUTH <REDIS_PASSWORD>
PING
SELECT 2
SCAN 0 MATCH booking-service:*
```

## Environment variables

- `POSTGRES_ADMIN_*` and `POSTGRES_PORT`: initialization administrator and host port.
- `<SERVICE>_DB_NAME`, `<SERVICE>_DB_USER`, `<SERVICE>_DB_PASSWORD`: isolated database ownership.
- `<SERVICE>_DATABASE_URL`: application SQLAlchemy connection string.
- `REDIS_PASSWORD`, `REDIS_PORT`, and service-specific `*_REDIS_URL`: Redis access/namespaces.
- `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`, and RabbitMQ ports: broker access.
- `RABBITMQ_EXCHANGE`, `RABBITMQ_DEAD_LETTER_EXCHANGE`, and `*_EVENT_QUEUE`: topology names.

## Troubleshooting

- **Port already allocated:** change `POSTGRES_PORT`, `REDIS_PORT`, or RabbitMQ port variables.
- **Container is unhealthy:** inspect `docker logs roundready-postgres`,
  `docker logs roundready-redis`, or `docker logs roundready-rabbitmq`.
- **Role/database changes are ignored:** initialization is first-run only; perform the reset
  procedure after confirming local data may be deleted.
- **Authentication fails:** ensure the URL password matches the corresponding service role
  password and that special URL characters are percent-encoded.
- **Application cannot resolve a hostname:** use `localhost` from the host; use deterministic
  container names only from a container attached to `roundready-local-network`.
- **RabbitMQ URL fails:** encode the virtual host in the URL and ensure the service uses the
  same `RABBITMQ_VHOST` configured for the broker.
- **Redis keys collide:** use the assigned logical database and `<service-name>:` key prefix.
