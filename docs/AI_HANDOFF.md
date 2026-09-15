# AI Handoff

Branch: `dev`

Starting HEAD: `7cfee4f`

No commits or pushes were made.

## Completed

- Added payment-to-booking contract validation so payment creation and development completion fail closed unless the booking is owned by the candidate, payable, and priced at ₹200 INR.
- Added interviewer eligibility tombstones and source-time event handling so stale approval/suspension events cannot resurrect deleted or newer eligibility state.
- Added booking availability synchronization from verified interviewer weekly availability/blockouts into 30-day public slots, with a default interview rubric.
- Added local interview attendance/dev room support and truthful frontend room UI.
- Improved interviewer verification evidence UI and evidence resubmission behavior.
- Reworked the public landing page into a discovery/catalog page with hero, workflow, compact interviewer cards, transparent ₹200 pricing, founder story, and final CTA.
- Added `/interviewers/[id]` as the richer public interviewer detail page.
- Added founder image support at browser path `/images/founder/jagadish.jpg`, backed by `frontend/public/images/founder/jagadish.jpg`, with a neutral fallback when the file is missing.
- Added `scripts/local-e2e.py` for the local MVP smoke flow.
- Redesigned `/login` as a responsive candidate/interviewer experience with RoundReady branding, benefits, founder story, an optional local candidate image, and a compact trust strip.
- Preserved the single authentication flow, backend-derived role routing, email-verification resend, disabled/loading behavior, and safe candidate booking `next` intent. Password reset and Google OAuth remain absent because those capabilities are not implemented.
- Added event-driven interviewer account access enforcement: Interviewer lifecycle remains authoritative, its transactional outbox feeds an Auth consumer, and Auth projects `active`, `blocked`, or terminal `disabled` state with source-time ordering and duplicate-event handling.
- Suspensions now require a controlled moderation category and use a proper Admin confirmation dialog. Private Admin notes stay in interviewer review history; only the safe category reaches Auth and may appear in the blocked-login message.
- Auth now revokes refresh tokens and rejects login, access-token introspection, and gateway-authenticated requests after suspension or deletion. Verified reactivation restores access; deletion cannot be reversed by delayed approval events.

## Validation

- Backend unit/integration suites previously passed across all 8 services; the changed Auth and Interviewer suites now pass 40 and 47 tests respectively.
- Strict mypy previously passed across all 8 service `app` and `tests` trees: 156 files.
- Frontend test suite passes: 23 files, 173 tests.
- Frontend lint passes with no warnings.
- Frontend typecheck passes.
- Frontend Prettier check passes.
- Frontend production build passes with:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.roundready.example NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS=false npm run build
```

- `git diff --check` passes.
- `ruff check scripts/local-e2e.py` passes.

## E2E Evidence

The latest full local smoke run passes all 13 grouped checks:

- Interviewer onboarding
- Verification
- Admin approval
- Availability
- Public slots
- Candidate onboarding
- Booking
- ₹200 local payment
- Booking confirmation
- Interview session
- Feedback
- Notifications
- Negative security and admin lifecycle checks

This fresh run includes the account-level moderation checks and completed successfully. It proves the real local outbox/RabbitMQ/Auth projection path for old access rejection, refresh rejection, stable blocked/disabled login errors, reactivation, deletion, public removal, and preserved historical workflow records.

## Remaining

- I could not start the live frontend dev server for a final browser pass because the approval reviewer rejected `npm run dev -- --hostname 127.0.0.1` after reporting a usage-limit failure. Frontend unit tests and production build passed, but a manual browser check of the landing and login pages remains unverified in this session.
- The optional login photograph is intentionally absent. Add it at `frontend/public/images/auth/candidate-login.jpg`; the current layered blue background remains polished when the file is missing.
- The current backend payment model stores the fixed ₹200 INR order. It does not yet store payout accounting rows for the landing-page ₹150 interviewer / ₹50 platform split.
- A previous full repo Ruff format check found an unrelated pre-existing formatting mismatch in `services/auth-service/app/scripts/create_admin.py`.
