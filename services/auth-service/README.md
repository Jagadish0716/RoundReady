# Auth service

The auth service owns credentials, roles, refresh-token families, access-token revocation,
and its transactional event outbox. It does not own candidate or interviewer profiles.

Run the API with `uvicorn app.main:app` from this directory after applying migrations:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

Run the durable outbox publisher separately:

```bash
python -m app.workers.outbox
```

`JWT_SIGNING_KEY` must be at least 32 random bytes for HS256. For RS256, set
`JWT_ALGORITHM=RS256`, put the PEM private key in `JWT_SIGNING_KEY`, and the PEM public key in
`JWT_VERIFICATION_KEY`. Secrets must come from the environment or secret manager.

Public registration permits candidate and interviewer roles only. Admin credentials require
an audited bootstrap/administrative provisioning process.

## Initial admin provisioning

Admin registration is never public. Explicitly run the idempotent bootstrap command inside the
auth-service environment after migrations have completed:

```bash
ROUNDREADY_ADMIN_EMAIL=admin@example.in \
ROUNDREADY_ADMIN_PASSWORD='use-a-secret-manager-value' \
python -m app.scripts.create_admin
```

Omit `ROUNDREADY_ADMIN_PASSWORD` to enter it securely at the prompt. Re-running the command for an
existing admin leaves its password and account unchanged. It refuses to promote an existing
Candidate or Interviewer account.
