from app.domain.models import BookingStatus

TERMINAL = frozenset(
    {
        BookingStatus.CANCELLED,
        BookingStatus.PAYMENT_FAILED,
        BookingStatus.SETTLED,
        BookingStatus.CANDIDATE_NO_SHOW,
        BookingStatus.INTERVIEWER_NO_SHOW,
        BookingStatus.TECHNICAL_FAILURE,
        BookingStatus.REFUNDED,
        BookingStatus.RESCHEDULED,
    }
)
ALLOWED: dict[BookingStatus, frozenset[BookingStatus]] = {
    BookingStatus.PAYMENT_PENDING: frozenset(
        {BookingStatus.BOOKED, BookingStatus.PAYMENT_FAILED, BookingStatus.CANCELLED}
    ),
    BookingStatus.BOOKED: frozenset(
        {BookingStatus.CONFIRMED, BookingStatus.CANCELLED, BookingStatus.REFUNDED}
    ),
    BookingStatus.CONFIRMED: frozenset(
        {
            BookingStatus.READY,
            BookingStatus.CANCELLED,
            BookingStatus.RESCHEDULED,
            BookingStatus.REFUNDED,
        }
    ),
    BookingStatus.READY: frozenset(
        {
            BookingStatus.IN_PROGRESS,
            BookingStatus.CANDIDATE_NO_SHOW,
            BookingStatus.INTERVIEWER_NO_SHOW,
            BookingStatus.TECHNICAL_FAILURE,
        }
    ),
    BookingStatus.IN_PROGRESS: frozenset(
        {BookingStatus.COMPLETED, BookingStatus.TECHNICAL_FAILURE}
    ),
    BookingStatus.COMPLETED: frozenset({BookingStatus.FEEDBACK_PENDING}),
    BookingStatus.FEEDBACK_PENDING: frozenset({BookingStatus.FEEDBACK_SUBMITTED}),
    BookingStatus.FEEDBACK_SUBMITTED: frozenset({BookingStatus.SETTLED}),
    **{status: frozenset() for status in TERMINAL},
}


def can_transition(current: BookingStatus, target: BookingStatus) -> bool:
    return target in ALLOWED[current]


def occupies_time(status: BookingStatus) -> bool:
    return status not in TERMINAL
