# Interviewer service

Owns interviewer professional profiles, domains/skills, verification state, recurring weekly
availability, UTC blockouts, rating summaries, and reliability metadata. It contains no
booking, authentication, or candidate-profile tables.

The API trusts gateway-forwarded identity only when the internal identity secret matches.
Public networking must terminate at the API gateway; this service belongs on the private
service network.

Apply migrations and run the API from this directory:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8003
```

Run the transactional outbox publisher separately:

```bash
python -m app.workers.outbox
```

Weekly rules describe local wall-clock availability with an IANA timezone. Blockouts use
timezone-aware instants. The booking service will consume `AvailabilityChanged` and remains
responsible for generating slots and owning bookings.
