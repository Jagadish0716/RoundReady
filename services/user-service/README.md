# User service

The user service owns candidate profiles and resume metadata only. It never reads auth-service
tables and stores no passwords, token material, or interviewer profiles.

The API gateway supplies `X-User-ID`, `X-User-Role`, `X-User-Email`, and
`X-Internal-Identity-Secret` after authenticating the public request. The service rejects
missing or invalid internal credentials and derives every self-service lookup key from the
forwarded identity. The service must be reachable only over the private service network.

Apply migrations and start locally:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8002
```

Resume uploads accept PDF, DOC, and DOCX files up to 5 MB. Local Compose stores private
objects in the `roundready-resume-data` volume and stores only an opaque object reference,
safe filename, MIME type, size, and checksum in PostgreSQL. Downloads are authorized from
the authenticated user identity rather than a public URL.

`LocalResumeStorage` implements the storage interface for development. Production must
replace it with private object storage, malware scanning, encryption/KMS controls, retention
and deletion policies, backups, and short-lived authenticated download delivery.
