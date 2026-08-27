from app.domain.models import BookingStatus
from app.domain.state_machine import can_transition, occupies_time


def test_valid_and_invalid_transitions() -> None:
    assert can_transition(BookingStatus.PAYMENT_PENDING, BookingStatus.BOOKED)
    assert not can_transition(BookingStatus.PAYMENT_PENDING, BookingStatus.COMPLETED)
    assert not occupies_time(BookingStatus.CANCELLED)
    assert occupies_time(BookingStatus.CONFIRMED)


def test_all_states_are_defined() -> None:
    assert len(BookingStatus) == 16
