# RoundReady frontend user guide

This guide describes the frontend that currently exists in this repository. It is both a user guide and a manual test checklist. Features marked **Partial** need a backend event, seeded data, an external provider, or an API that is not exposed in the browser UI.

## 1. Local setup

### Prerequisites

- Docker and Docker Compose
- Node.js compatible with the lockfile and Next.js 16
- npm
- A repository-root `.env` configured from `.env.example`

Start the backend from the repository root:

```bash
docker-compose --env-file .env -f infrastructure/docker-compose.yml up -d
docker-compose --env-file .env -f infrastructure/docker-compose.yml ps
```

Wait for the API gateway and required services to become healthy. The local gateway is at `http://127.0.0.1:8000` (equivalent to `http://localhost:8000`).

Configure and run the frontend:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

The browser configuration contains no secrets:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS=true
```

- `NEXT_PUBLIC_API_BASE_URL` must be the gateway, not an individual service. Development defaults to `http://127.0.0.1:8000` if omitted; production requires an explicit HTTPS URL.
- `NEXT_PUBLIC_ENABLE_DEVELOPMENT_PAYMENTS=true` exposes the local payment-completion button outside production. Production refuses this setting.
- Restart `npm run dev` after changing `.env.local`.

### Authentication behavior and local limitations

Registration supports Candidate and Interviewer accounts. Admin accounts use the secure bootstrap described in [Admin account setup](#admin-account-setup). Login redirects to `/candidate`, `/interviewer`, or `/admin` according to the authenticated role. Logout ends the backend session and returns to `/login`.

Anonymous visitors can browse domains, verified interviewer profiles, safe trust badges, and available ₹200 slots from `/`. Profile management, slot holds, bookings, payment, interviews, feedback, and notifications require authentication. The product rule is: **Explore freely. Sign in when you're ready to book.**

Access and refresh tokens are held only in React memory. They are not stored in browser storage or cookies. A page reload therefore signs the user out. An authenticated request that receives one 401 attempts one shared refresh-token rotation and one retry; a failed refresh returns the user to login.

Local payments use the development provider. No real payment page is implemented. Interview-room access returns a LiveKit join URL and token, but this frontend displays them as text; it does not embed a LiveKit audio/video client.

## 2. Entry point and role access

The landing page at `/` says “Prepare for your next interview.” The public header provides **Browse interviewers**, **Login**, and **Register** links. Public interviewer results contain only verified profiles and safe professional/trust fields; contact details, evidence, reviewer notes, and administrative state are never included.

| Account     | Public registration | Home           | Access                                                                                                                   |
| ----------- | ------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Candidate   | Yes                 | `/candidate`   | Candidate profile, verified slot discovery, booking/payment, sessions, feedback report, notifications                    |
| Interviewer | Yes                 | `/interviewer` | Professional profile, skills, availability, verification evidence, assigned sessions, feedback submission, notifications |
| Admin       | No                  | `/admin`       | Interviewer verification review                                                                                          |

Opening a protected page while signed out redirects to `/login?next=...`. A logged-in user with the wrong role sees a forbidden state. Login only honors `next` when it remains inside that role’s area.

Selecting **Book interview** while signed out sends the visitor to login with the selected interviewer and slot IDs in the validated return URL. Registration preserves the same return intent. After candidate login, the frontend reloads the public slot, confirms it still belongs to the selected verified interviewer and remains available, and only then creates an authenticated hold. If revalidation fails, no hold, booking, or payment state is created and the candidate is asked to choose another slot.

## 3. Candidate guide

All candidate functionality is currently on `/candidate`, ordered as Notifications, Book a mock interview, Interview sessions, and Candidate profile.

### Register and sign in

1. Open `/register` and keep **Account type** set to **Candidate**.
2. Enter a syntactically valid email.
3. Enter a password between 12 and 128 characters and repeat it exactly.
4. Select **Create account**. Duplicate email registration displays an error.
5. At `/login?registered=1`, confirm “Account created,” enter the credentials, and select **Sign in**.
6. Expect a redirect to `/candidate`.

### Create or update the candidate profile

Scroll to **Candidate profile**. A new account initially has no profile; this is represented by the empty form rather than an error.

1. Enter **Full name** (required, maximum 160 characters).
2. Optionally enter phone in international E.164-like format, for example `+919876543210`.
3. Confirm the read-only account email, then optionally enter city, current role, target role, and LinkedIn URL.
4. Search for a country code and enter the numeric mobile number; RoundReady stores the combined number in E.164 format.
5. Enter experience between 0 and 20 years and choose one of the supported languages.
6. Optionally choose a PDF, DOC, or DOCX resume up to 5 MB. The upload occurs after the profile is saved.
7. Select **Save profile**.
8. Expect “Profile saved successfully.” Revisit the same section to view or update the saved values.

LinkedIn must use a `linkedin.com` hostname. Both UI and API validate phone, experience, language, resume size/type, required text, and LinkedIn. Resume content is private and is never represented by a user-entered public URL.

### Find a verified slot

In **Book a mock interview**:

1. Choose **From** and **To** dates (today through 30 days ahead by default).
2. Select **Find slots**.
3. Each result shows domain, topic, interviewer ID, date/time, 20-minute duration, availability, ₹200, and **RoundReady Verified**.
4. Select **Hold this slot**. The page displays the hold expiry.

Only interviewers present in the booking service’s verified eligibility projection appear. A non-verified or suspended interviewer is filtered from discovery and cannot be held or booked, even using a previously known slot ID.

Before signing in, the landing page provides verified interviewer discovery with headline, role, biography, experience, skills/domains, safe professional/screening trust indicators, price, and upcoming slots. Authenticated candidate discovery remains available in the candidate workspace.

### Create and pay for a booking

1. While the hold is valid, select **Create booking**.
2. Expect `PAYMENT PENDING` and “Booking created. Payment is required to confirm it.”
3. Select **Create ₹200 payment**. The UI verifies the authoritative amount is INR 20,000 paise (₹200).
4. With development payments enabled, select **Complete development payment**.
5. The frontend polls the booking up to 10 times, approximately once per second.
6. Expect `CONFIRMED` and “Your interview is confirmed.”

The booking and payment requests use stable idempotency keys during the current page lifetime, so a retry should return the same logical result. A page reload loses both the UI state and in-memory authentication.

If payment fails and the booking reaches `payment_failed`, the UI reports that the slot was released and asks the candidate to search again. There is no browser control that intentionally triggers a failed development payment.

### Candidate bookings

The page displays only the booking created during the current in-memory interaction. It shows booking ID, interviewer ID, schedule, duration, price, payment status, and booking status.

There is currently no candidate booking-list/history screen and no cancellation button, although owned-booking lookup and candidate cancellation exist in the backend. Another candidate cannot retrieve an owned booking through the protected API.

### Interview session and feedback report

The **Interview sessions** section lists sessions assigned to the current user and selects the first one. A confirmed booking is converted to a session asynchronously by the interview event worker.

- The card shows session, booking, candidate and interviewer IDs, schedule, duration, and state.
- **Enter interview room** appears only for `ready` or `in_progress` sessions and is restricted to the configured join window (normally 10 minutes before through 20 minutes after the scheduled end).
- Successful room access displays the join URL and token expiry and says recording is disabled. The user must use an external/compatible LiveKit client; this UI does not join the call itself.
- Candidate users cannot start or complete a session.
- After interviewer feedback is submitted and the session becomes `feedback_submitted`, candidates see the feedback report: total score, summary, readiness, criterion scores, strengths, and improvement areas.

There is no candidate feedback/rating form. Structured feedback is submitted by the interviewer.

### Notifications

The top section loads the current user’s notifications and shows unread count, subject/event label, body, timestamp, channel, and delivery status. Select **Mark read** on an unread item or **Refresh** to reload.

Recognized labels include booking confirmed/cancelled/rescheduled, payment confirmed/refunded, candidate/interviewer attendance updates, and feedback available. Other event types display their raw event name.

### Candidate restrictions

- Cannot access `/interviewer` or `/admin`.
- Cannot discover, hold, or book non-verified interviewers.
- Cannot manage sessions assigned to another user.
- Cannot access another candidate’s profile, booking, notifications, or feedback through authenticated APIs.

## 4. Interviewer guide

All interviewer functionality is on `/interviewer`, ordered as Notifications, Interview sessions, Interviewer profile/availability, and Verification.

### Register and create a profile

1. Register at `/register` with **Account type: Interviewer** and sign in.
2. On `/interviewer`, scroll to **Interviewer profile**.
3. Complete **Professional details**: headline (required), company, job title, experience (0–60), LinkedIn URL, GitHub URL, and bio.
4. Select **Save profile**.
5. Under **Skills and domains**, select **Add skill**. Choose DevOps, AWS, Azure, Backend, Full Stack, QA, or Tech Support; provide topic, skill, and experience; then **Save skills**. Every added row needs a topic and skill.

LinkedIn must use LinkedIn and GitHub must use GitHub. Profile company/title/experience remain self-entered claims until an administrator verifies evidence.

### Verification workflow

The **Verification** section appears after an interviewer profile exists.

1. Save any applicable evidence separately:
   - LinkedIn URL
   - Company email
   - GitHub or portfolio URL
   - Optional private supporting-document reference beginning `private-object://`
2. Confirm each row changes from “not submitted” to a review status such as `pending`.
3. Select **Submit for review**. The state becomes `UNDER REVIEW`.
4. An admin reviews the evidence and manually records the professional review and screening result.
5. The resulting state is verified, rejected, pending after a request for more evidence, or suspended.

The domain supports Email verified, Mobile verified, LinkedIn reviewed, Company email verified, Professional evidence reviewed, and Screening call passed checks. The current admin UI explicitly attests the last two during approval and displays previously recorded checks; it does not expose individual controls for recording the other four checks.

State behavior visible to the interviewer:

| State          | UI behavior                                                                                                                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `pending`      | Evidence editable; **Submit for review** available                                                                          |
| `under_review` | Status shown; submission button hidden; awaiting admin action                                                               |
| `rejected`     | Rejection/request-more reason shown; evidence editable; resubmission available                                              |
| `verified`     | Verified status shown; evidence inputs locked; eligible for slot discovery/booking once booking consumes the approval event |
| `suspended`    | Suspension reason shown; evidence inputs locked; removed from new discovery/booking                                         |

Email/mobile OTP does not exist. Company domains are not automatically trusted. Supporting-document upload/storage does not exist; the field accepts only a reference produced by a future private-storage integration. Screening is a manual process outside the product; no video-call scheduling is built for it. Government identifiers are not requested.

### Weekly availability and blockouts

Under **Weekly availability**:

1. Select **Add time**.
2. Choose weekday, start time, end time, and IANA timezone (default `Asia/Kolkata`).
3. Ensure start is before end and same-day/timezone ranges do not overlap.
4. Select **Save availability**.

Under **Availability blockouts**, enter timezone-aware local start/end date-times and an optional reason, then select **Add blockout**. Existing entries can be removed.

Important limitation: the frontend saves availability rules and blockouts, but it does not publish concrete booking slots. Slot generation currently exists only as an internal booking-service API and is blocked at the public gateway. Verification is enforced when that internal workflow generates slots. For manual booking tests, a verified interviewer’s concrete slot must already exist through an approved internal test/seeding workflow.

### Sessions and interviewer feedback

The interviewer **Interview sessions** section shows assigned sessions and loads the selected session’s rubric.

1. When a session is `ready`, select **Enter interview room** to obtain short-lived room access.
2. Select **Start interview** to move a ready session to `in_progress`.
3. Select **Complete interview** to finish it and reach `feedback_pending`.
4. Complete every rubric score within its displayed maximum.
5. Enter at least one strength and improvement area (one per line), a summary of at least 10 characters, and readiness: Not ready, Developing, Interview ready, or Strong.
6. Select **Submit feedback**. Expect “Feedback submitted” and `feedback_submitted`.

Duplicate feedback is rejected. Interviewers cannot manage another interviewer’s session. Candidate/session information is limited to IDs and schedule; no detailed candidate-profile panel is exposed here.

Notifications work exactly as described for candidates. Suspension or rejection does not delete the profile, availability, prior sessions, bookings, or history. It prevents new discovery/holds/bookings; the frontend does not describe or automate cancellation of existing bookings.

## 5. Admin guide

### Admin account setup

Admin registration is intentionally absent from `/register`; there is no default credential. After the auth migration is current, run the idempotent bootstrap inside the local auth container:

```bash
docker-compose --env-file .env -f infrastructure/docker-compose.yml exec auth-service python -m app.scripts.create_admin
```

Enter the admin email and a 12–128 character password at the prompts. Re-running for an existing admin leaves it unchanged and refuses to promote an existing candidate/interviewer account. Then sign in normally at `/login`; expect `/admin`.

### Admin dashboard and review

The current admin page contains only **Interviewer reviews**. It lists all interviewer profiles, not just pending submissions. Select a profile to view:

- Headline, status, experience, company, job title, bio, LinkedIn, and GitHub
- Submitted evidence values and evidence review status
- Previously recorded verification checks
- Screening status
- Review history with reviewer ID, time, transition, and notes

To genuinely approve an `under_review` interviewer:

1. Inspect the professional profile and every displayed evidence item.
2. Complete the manual screening outside RoundReady.
3. Check **I reviewed the professional evidence**.
4. Check **The interviewer passed the screening call**.
5. Optionally add reviewer notes.
6. Select **Approve** and confirm the browser dialog.
7. Expect “Verification status updated.” The state becomes `verified`; a minimal approval event makes the interviewer eligible for candidate discovery.

Available state actions are:

| Current state       | UI action                 | Required input                     | Result and discovery effect                                      |
| ------------------- | ------------------------- | ---------------------------------- | ---------------------------------------------------------------- |
| Pending or rejected | **Mark under review**     | Confirmation                       | `under_review`; still hidden                                     |
| Under review        | **Approve**               | Both attestations and confirmation | `verified`; eligible after event processing                      |
| Under review        | **Reject**                | Reviewer reason and confirmation   | `rejected`; hidden                                               |
| Under review        | **Request more evidence** | Reviewer reason and confirmation   | `pending`; hidden; interviewer sees reason and may edit/resubmit |
| Verified            | **Suspend**               | Reviewer reason and confirmation   | `suspended`; removed from new discovery/booking                  |
| Suspended           | **Reactivate**            | Confirmation                       | `verified`; eligible again after event processing                |

Every action is authorized server-side, audited with reviewer identity/time, and constrained by current state. Interviewer-role users cannot approve themselves. An admin identity whose user ID equals the interviewer ID is also forbidden from self-review. Candidate and interviewer roles receive 403 for admin APIs. Candidate-safe trust APIs never include evidence values, reviewer notes, or internal reasons.

### Backend capabilities not currently exposed in Admin UI

- Individual editing of email, mobile, LinkedIn, and company-email verification checks
- Independent accept/reject controls for each evidence record
- Detailed screening notes, communication assessment, and technical assessment inputs (approval records only generic reviewed values)
- Candidate administration, booking administration/transitions, payments/refunds, attendance/no-show management, notification administration, and system operations

These backend capabilities must not be treated as usable admin frontend features.

## 6. Complete RoundReady manual test

Because concrete slot publication is not exposed in the frontend, step 15 requires an approved internal seed/test mechanism. Session creation and notifications are asynchronous; refresh after workers process their events.

|   # | Role        | Route                  | Action                                                                                    | Expected result                                       |
| --: | ----------- | ---------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------- |
|   1 | Operator    | Terminal               | Start Compose and wait for healthy services                                               | Gateway responds at port 8000                         |
|   2 | Operator    | Terminal               | Start `npm run dev` in `frontend`                                                         | Landing page responds at port 3000                    |
|   3 | Candidate   | `/register`            | Register Candidate, then sign in                                                          | Redirect to `/candidate`                              |
|   4 | Candidate   | `/candidate`           | Complete Candidate profile                                                                | Success notice and persisted fields                   |
|   5 | Interviewer | `/register`            | Register Interviewer, then sign in                                                        | Redirect to `/interviewer`                            |
|   6 | Interviewer | `/interviewer`         | Save professional profile and skills                                                      | Both success notices appear                           |
|   7 | Interviewer | `/interviewer`         | Save LinkedIn/company-email/portfolio evidence                                            | Evidence shows `pending`                              |
|   8 | Interviewer | `/interviewer`         | Select **Submit for review**                                                              | Status becomes `under_review`                         |
|   9 | Operator    | Terminal               | Bootstrap admin using the documented command                                              | Admin is created or already exists                    |
|  10 | Admin       | `/login`, `/admin`     | Sign in and select the interviewer                                                        | Profile, evidence, screening, and history load        |
|  11 | Admin       | `/admin`               | Perform screening externally; tick both attestations                                      | **Approve** becomes enabled                           |
|  12 | Admin       | `/admin`               | Select **Approve** and confirm                                                            | Interviewer becomes `verified`                        |
|  13 | Interviewer | `/interviewer`         | Sign in again and save weekly availability/blockouts                                      | Availability persists; evidence is locked             |
|  14 | Operator    | Internal seed workflow | Seed a compatible rubric and generate a concrete future slot for the verified interviewer | Slot exists; this step has no public UI               |
|  15 | Candidate   | `/candidate`           | Sign in, choose dates, and **Find slots**                                                 | Verified slot and badge appear                        |
|  16 | Candidate   | `/candidate`           | **Hold this slot**, then **Create booking**                                               | Hold expiry, then `payment_pending`                   |
|  17 | Candidate   | `/candidate`           | **Create ₹200 payment**                                                                   | Payment order is pending                              |
|  18 | Candidate   | `/candidate`           | **Complete development payment**                                                          | Booking reaches `confirmed` after polling             |
|  19 | Operator    | Workers                | Allow booking event processing                                                            | Interview session is created asynchronously           |
|  20 | Both        | Role home pages        | Sign in separately and inspect Interview sessions                                         | Assigned session appears for each user                |
|  21 | Both        | Role home pages        | During join window, select **Enter interview room**                                       | Short-lived join URL/token details appear             |
|  22 | Interviewer | `/interviewer`         | **Start interview**, then **Complete interview**                                          | `in_progress`, then `feedback_pending`                |
|  23 | Interviewer | `/interviewer`         | Complete and submit Structured feedback                                                   | `feedback_submitted`; report displayed                |
|  24 | Candidate   | `/candidate`           | Sign in again and select the session                                                      | Feedback report appears                               |
|  25 | Both        | Role home pages        | Refresh Notifications and select **Mark read**                                            | Event notification appears and unread count decreases |

## 7. Negative manual tests

| Action                                                                    | Expected result                                                                        |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Signed-in Candidate opens `/admin`                                        | Forbidden state; admin data is not rendered                                            |
| Signed-in Interviewer opens `/admin`                                      | Forbidden state                                                                        |
| Unverified interviewer is used for internal slot generation               | Backend returns 409 `interviewer_not_verified`                                         |
| Candidate searches for or tries to hold a non-verified interviewer’s slot | Slot is absent; direct hold returns a conflict                                         |
| Interviewer calls an admin review action                                  | 403                                                                                    |
| Same-user admin identity attempts its own interviewer review              | 403                                                                                    |
| Another interviewer requests `/me/verification`                           | Their own missing profile/evidence returns 404; no cross-user evidence endpoint exists |
| Admin rejects or requests more evidence without a reason                  | UI blocks submission; API validation also rejects it                                   |
| Rejected interviewer resubmits                                            | Evidence remains editable; submission returns to `under_review`                        |
| Suspended interviewer is searched/booked                                  | Hidden from discovery; new hold/booking rejected; history remains                      |
| Interviewer submits feedback twice                                        | Second request is rejected as an invalid session state                                 |
| Reload page or use expired/invalid refresh token                          | In-memory session is lost or refresh fails; redirect to `/login`                       |
| Let a hold expire before booking                                          | 409; UI asks user to search and hold again                                             |
| Payment event reaches failure state                                       | Booking shows `payment_failed`; slot is released; search again                         |
| Repeat create-booking/payment within the same page interaction            | Stable idempotency key returns the same logical request result                         |

## 8. Frontend route reference

| Route          | Role                  | Purpose                                                                       | Authentication | Status                                         |
| -------------- | --------------------- | ----------------------------------------------------------------------------- | -------------- | ---------------------------------------------- |
| `/`            | Any                   | Landing page                                                                  | No             | Supported                                      |
| `/login`       | Any                   | Sign in and role redirect                                                     | No             | Supported                                      |
| `/register`    | Candidate/Interviewer | Public account creation                                                       | No             | Supported; no Admin option                     |
| `/candidate`   | Candidate             | Notifications, booking/payment, sessions/report, profile                      | Yes            | Supported; booking history/cancellation absent |
| `/interviewer` | Interviewer           | Notifications, sessions/feedback, profile, skills, availability, verification | Yes            | Supported; concrete slot publication absent    |
| `/admin`       | Admin                 | Interviewer verification review                                               | Yes            | Supported for verification only                |

There are no nested browser pages for individual bookings, sessions, profiles, or reviews.

## 9. Feature matrix

| Feature                       | Candidate         | Interviewer       | Admin                     | Status                                   |
| ----------------------------- | ----------------- | ----------------- | ------------------------- | ---------------------------------------- |
| Registration                  | Supported         | Supported         | Not exposed in UI         | Supported for public roles               |
| Login/logout                  | Supported         | Supported         | Supported                 | Supported                                |
| Role guard                    | Supported         | Supported         | Supported                 | Supported                                |
| Profile                       | Supported         | Supported         | Profile summary in review | Supported                                |
| Interviewer verification      | Trust badge only  | Supported         | Supported                 | Partial checks/provider integration      |
| Skills                        | Not applicable    | Supported         | Not exposed in UI         | Supported                                |
| Weekly availability/blockouts | Not applicable    | Supported         | Not exposed in UI         | Supported                                |
| Concrete slot publication     | Not applicable    | Not exposed in UI | Not exposed in UI         | Internal backend only                    |
| Slot discovery                | Supported         | Not applicable    | Not exposed in UI         | Verified slots only                      |
| Booking creation              | Supported         | Not applicable    | Not exposed in UI         | Supported in current page state          |
| Booking history/cancellation  | Not exposed in UI | Not exposed in UI | Not exposed in UI         | Backend capability only                  |
| Payment                       | Supported         | Not applicable    | Not exposed in UI         | Development completion only locally      |
| Interview room access         | Partial           | Partial           | Not applicable            | Token/URL shown; no embedded call client |
| Session start/complete        | Not applicable    | Supported         | Not exposed in UI         | Supported                                |
| Structured feedback           | Report only       | Supported         | Not exposed in UI         | Supported                                |
| Notifications/read state      | Supported         | Supported         | Not exposed in UI         | Supported                                |
| Admin verification            | Not applicable    | Not applicable    | Supported                 | Partial granular check editing           |

## 10. Current limitations

- Authentication is memory-only; browser reload signs out.
- Email and mobile OTP/challenge providers are not implemented.
- Private document upload/object storage is not implemented; only metadata references exist.
- Screening calls are manually performed outside the application.
- Admin approval records generic communication/technical “reviewed” values; detailed assessment editing is absent.
- Interviewer availability does not produce concrete slots through the UI.
- Candidate interviewer cards show ID and aggregate badge, not profile details or expanded trust claims.
- Candidate booking state is not restored after navigation/reload; no booking history or cancellation UI exists.
- Development payment completion is a local-only provider flow; no production checkout frontend is implemented.
- The frontend displays LiveKit access details but does not embed a room client.
- Session readiness is not manually controlled in the frontend; the session must already reach a UI-supported state.
- Admin UI is limited to interviewer verification.
- Notifications are loaded/refreshed manually; there is no real-time browser subscription.

## 11. Troubleshooting

| Symptom                           | Likely cause and action                                                                                                                                                                                                                                                |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend cannot reach gateway     | Confirm Compose health, open `http://127.0.0.1:8000/health`, and check gateway logs. Browser code must not target a service port.                                                                                                                                      |
| Wrong API base URL                | Set an absolute HTTP local gateway URL in `frontend/.env.local`, restart Next.js, and avoid credentials/trailing service paths.                                                                                                                                        |
| Port 3000 in use                  | Stop the existing process or run `npm run dev -- -p 3001`, then open that port.                                                                                                                                                                                        |
| Gateway unavailable               | Run Compose `ps`; inspect `docker-compose ... logs api-gateway` and the directly failing service.                                                                                                                                                                      |
| 401                               | Session/token expired or page was reloaded. Sign in again. A failed refresh intentionally clears the session.                                                                                                                                                          |
| 403                               | The account role does not own that page/resource, or a self-review was attempted. Use the correct account.                                                                                                                                                             |
| 404                               | A new profile may not exist, the selected resource is not owned, or an asynchronous session has not been created yet.                                                                                                                                                  |
| 409                               | Usually invalid state, expired/unavailable slot, duplicate feedback, incomplete verification checks, or closed join window. Read the displayed message and refresh authoritative state.                                                                                |
| 429                               | Do not merely increase limits. Check gateway logs for the request path/identity, Redis limiter keys/TTL, unexpected polling, repeated 401 refreshes, React request loops, or duplicate component requests. Health/readiness and OPTIONS should not consume user quota. |
| Redirected to login               | A reload erased the memory-only session, or access-token refresh failed. Sign in again.                                                                                                                                                                                |
| Payment remains pending           | Ensure development payments are enabled, select the completion button, and confirm payment/booking event workers and RabbitMQ are healthy. The poll lasts about 10 seconds.                                                                                            |
| Interviewer absent from discovery | They may not be verified, the approval event may not have reached booking eligibility, no concrete slot may exist, or the chosen date range excludes it.                                                                                                               |
| Verification remains pending      | Save a profile/evidence, select **Submit for review**, then have an admin mark it under review/approve. Screening and professional review are manual.                                                                                                                  |
| Interview session absent          | Booking may not be confirmed or the interview event worker/RabbitMQ may not have processed `booking.confirmed.v1`. Refresh after worker processing.                                                                                                                    |
| Room cannot be entered            | Session must be ready/in progress and inside the join window; valid LiveKit configuration is also required.                                                                                                                                                            |
| Notifications absent              | The relevant event may not have occurred or notification workers/RabbitMQ may be unhealthy. Select **Refresh** after processing.                                                                                                                                       |

For non-destructive local diagnostics, prefer targeted `docker-compose ... ps` and `docker-compose ... logs <service>` commands. Do not remove volumes as a routine troubleshooting step.
