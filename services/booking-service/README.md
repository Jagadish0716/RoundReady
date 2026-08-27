# Booking service

PostgreSQL is authoritative for slots, bookings, time-overlap exclusion, idempotency, status
history, processed payment events, and the event outbox. Redis stores only expiring hold locks.
Losing Redis cannot create or confirm a booking without a matching locked PostgreSQL slot.

Slot generation accepts availability windows through the defined interviewer availability
contract. This service never reads the interviewer database. Materialized slots and all
booking lifecycle state are owned here.

Run migrations, API, and maintenance worker:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8004
python -m app.workers.maintenance
```

The worker releases expired database holds and publishes durable outbox events. Redis removes
distributed hold keys using its configured TTL independently.
