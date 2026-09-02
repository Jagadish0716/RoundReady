from dataclasses import dataclass


class TemplateError(ValueError):
    pass


class StrictContext(dict[str, object]):
    def __missing__(self, key: str) -> object:
        raise TemplateError(f"missing template field: {key}")


@dataclass(frozen=True)
class Template:
    name: str
    version: int
    subject: str | None
    body: str

    def render(self, context: dict[str, object]) -> tuple[str | None, str]:
        safe = StrictContext(context)
        try:
            return (
                self.subject.format_map(safe) if self.subject else None,
                self.body.format_map(safe),
            )
        except (KeyError, ValueError) as exc:
            raise TemplateError("template rendering failed") from exc


TEMPLATES: dict[str, Template] = {
    "BookingConfirmed": Template(
        "booking_confirmed",
        1,
        "RoundReady interview confirmed",
        "Hi {recipient_name}, your interview is confirmed for {scheduled_start}.",
    ),
    "PaymentCaptured": Template(
        "payment_confirmed",
        1,
        "RoundReady payment confirmed",
        "Payment of ₹{amount_rupees} for booking {booking_id} was confirmed.",
    ),
    "InterviewReminder": Template(
        "interview_reminder",
        1,
        "Your RoundReady interview reminder",
        "Your interview starts at {scheduled_start}. Please join on time.",
    ),
    "InterviewStartingSoon": Template(
        "interview_starting_soon",
        1,
        "Your interview starts soon",
        "Your RoundReady interview starts in {minutes_until_start} minutes.",
    ),
    "BookingCancelled": Template(
        "booking_cancelled",
        1,
        "RoundReady interview cancelled",
        "Your interview scheduled for {scheduled_start} has been cancelled.",
    ),
    "BookingRescheduled": Template(
        "booking_rescheduled",
        1,
        "RoundReady interview rescheduled",
        "Your interview has moved to {scheduled_start}.",
    ),
    "InterviewerNoShow": Template(
        "interviewer_no_show",
        1,
        "Interviewer attendance update",
        "The interviewer did not attend. Our team will help with the next step.",
    ),
    "CandidateNoShow": Template(
        "candidate_no_show",
        1,
        "Candidate attendance update",
        "The candidate did not attend interview {session_id}.",
    ),
    "FeedbackSubmitted": Template(
        "feedback_available",
        1,
        "Your interview feedback is available",
        "Feedback for interview {session_id} is now available in RoundReady.",
    ),
    "PaymentRefunded": Template(
        "refund_status",
        1,
        "RoundReady refund update",
        "A refund of ₹{amount_rupees} for booking {booking_id} was processed.",
    ),
}

EVENT_ALIASES = {
    "booking.confirmed.v1": "BookingConfirmed",
    "booking.cancelled.v1": "BookingCancelled",
    "booking.rescheduled.v1": "BookingRescheduled",
    "payment.captured.v1": "PaymentCaptured",
    "payment.refunded.v1": "PaymentRefunded",
    "interview.interviewer_no_show.v1": "InterviewerNoShow",
    "interview.candidate_no_show.v1": "CandidateNoShow",
    "feedback.submitted.v1": "FeedbackSubmitted",
}


def template_for_event(event_type: str) -> Template | None:
    return TEMPLATES.get(EVENT_ALIASES.get(event_type, event_type))


def supported_event_types() -> set[str]:
    return set(TEMPLATES) | set(EVENT_ALIASES)
