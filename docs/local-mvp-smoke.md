# RoundReady Local MVP Smoke

This repo now includes a local end-to-end smoke script for the core RoundReady MVP flow.

## Start the backend

From the repository root:

```bash
docker-compose --env-file .env -f infrastructure/docker-compose.yml up --build
```

Wait until the API gateway and services are healthy. The booking service applies Alembic migrations on startup, including `0005_eligibility_tombstone`.

## Start the frontend

From `frontend/`:

```bash
npm run dev -- --hostname 127.0.0.1
```

The local frontend should use the existing `.env.local` development settings. The landing page uses `/images/founder/jagadish.jpg` for the founder photo and falls back to a neutral placeholder until that file is uploaded at `frontend/public/images/founder/jagadish.jpg`.

## Run the smoke script

From the repository root, with the backend running:

```bash
.venv/bin/python scripts/local-e2e.py
```

The script creates disposable local users and exercises:

- interviewer registration, profile, evidence, admin approval, suspension, reactivation, and deletion checks
- weekly availability propagation into public booking slots
- anonymous public discovery
- candidate registration and profile setup
- slot hold, booking, and idempotent booking behavior
- ₹200 development payment order creation and completion
- scheduled interview session join, attendance, completion, feedback, and notifications
- negative checks for stranger payment, client-supplied price, duplicate feedback, notification ownership, active-booking deletion, and nonexistent booking payment

The script uses local development helpers only. It does not delete Docker volumes and does not call cloud services.

## Product Notes

- Discovery is anonymous; users sign in only when they are ready to book.
- Public landing cards are intentionally compact. Full bio, full skills, and slot lists live on `/interviewers/[id]`.
- Public pages do not show interviewer contact details, professional evidence URLs, object references, or internal review state.
- The pricing page copy describes the intended product rule: ₹200 total, ₹150 to the interviewer, ₹50 for RoundReady platform/infrastructure. The current payment service records a fixed ₹200 INR order; it does not yet model payout accounting records for the ₹150/₹50 split.
