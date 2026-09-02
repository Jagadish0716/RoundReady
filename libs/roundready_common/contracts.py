"""Canonical cross-service event names.

Payloads remain service-owned; these constants prevent routing-key drift without
sharing domain models or persistence entities.
"""

PAYMENT_CAPTURED = "payment.captured.v1"
PAYMENT_FAILED = "payment.failed.v1"
PAYMENT_REFUNDED = "payment.refunded.v1"

BOOKING_CREATED = "booking.created.v1"
BOOKING_CONFIRMED = "booking.confirmed.v1"
BOOKING_CANCELLED = "booking.cancelled.v1"
BOOKING_RESCHEDULED = "booking.rescheduled.v1"

INTERVIEW_STARTED = "interview.started.v1"
INTERVIEW_COMPLETED = "interview.completed.v1"
FEEDBACK_SUBMITTED = "feedback.submitted.v1"
CANDIDATE_NO_SHOW = "interview.candidate_no_show.v1"
INTERVIEWER_NO_SHOW = "interview.interviewer_no_show.v1"
TECHNICAL_FAILURE = "interview.technical_failure.v1"
