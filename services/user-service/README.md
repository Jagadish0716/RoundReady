# User service

The user service owns candidate profiles and resume metadata only. It never reads auth-service
tables and stores no passwords, token material, or interviewer profiles.

The API gateway supplies `X-User-ID`, `X-User-Role`, and
`X-Internal-Identity-Secret` after authenticating the public request. The service rejects
missing or invalid internal credentials and derives every self-service lookup key from the
forwarded identity. The service must be reachable only over the private service network.

Apply migrations and start locally:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8002
```

Resume endpoints record metadata only. Object upload, malware scanning, signed URLs, and
storage-provider integration are intentionally outside this foundation.
