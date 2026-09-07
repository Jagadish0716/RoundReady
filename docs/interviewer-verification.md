# Interviewer verification

RoundReady uses layered, manual verification. An interviewer is discoverable and bookable only after an administrator has reviewed professional evidence and recorded a passed screening call. Self-entered company, job, or experience data never grants verified status.

## Evidence and privacy

Interviewers may provide LinkedIn, company-email, GitHub/portfolio, and optional supporting-document references. Supporting documents are represented only by `private-object://` metadata references; binaries are not stored in PostgreSQL. Candidate APIs expose only boolean trust claims and never evidence values, company email, reviewer notes, or rejection/suspension reasons.

Government identifiers such as Aadhaar and PAN are neither requested nor stored.

## Operational integrations still required

- Email and mobile checks are administrator-recorded states until an existing challenge/OTP provider is integrated. A company domain is never trusted automatically.
- Private object storage and an authenticated upload flow must be added before supporting-document references can be created by the product UI. The current UI accepts only a reference produced by such an approved private-storage workflow.
- Screening remains a manual admin-recorded result; this feature does not provide video infrastructure.

Verification status changes publish minimal events containing only the interviewer ID. Booking consumes approved/rejected/suspended events to maintain its local eligibility projection; existing bookings are retained when eligibility changes.
