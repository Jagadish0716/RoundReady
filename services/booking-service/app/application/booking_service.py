import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from app.api.schemas import GenerateSlotsRequest
from app.config import Settings
from app.domain.models import (
    Booking,
    BookingStatus,
    BookingStatusHistory,
    OutboxEvent,
    ProcessedEvent,
    Slot,
    SlotStatus,
    utc_now,
)
from app.domain.state_machine import can_transition, occupies_time
from app.infrastructure.holds import RedisHoldStore
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import Range, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class BookingService:
    def __init__(self, session: AsyncSession, holds: RedisHoldStore, settings: Settings) -> None:
        self.session = session
        self.holds = holds
        self.settings = settings

    async def generate_slots(self, request: GenerateSlotsRequest) -> list[Slot]:
        duration = timedelta(minutes=self.settings.session_duration_minutes)
        if any(window.ends_at - window.starts_at != duration for window in request.windows):
            raise ServiceError(
                code="invalid_slot_duration",
                message="Slot duration does not match configured session duration",
                status_code=422,
            )
        rows = [
            {
                "id": uuid4(),
                "interviewer_id": request.interviewer_id,
                "starts_at": w.starts_at,
                "ends_at": w.ends_at,
                "status": SlotStatus.AVAILABLE,
            }
            for w in request.windows
        ]
        statement = (
            insert(Slot)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_interviewer_slot")
            .returning(Slot)
        )
        result = list((await self.session.scalars(statement)).all())
        await self.session.commit()
        return result

    async def available_slots(self, starts_after: datetime, ends_before: datetime) -> list[Slot]:
        now = datetime.now(UTC)
        return list(
            (
                await self.session.scalars(
                    select(Slot)
                    .where(
                        Slot.starts_at >= starts_after,
                        Slot.ends_at <= ends_before,
                        or_(
                            Slot.status == SlotStatus.AVAILABLE,
                            (Slot.status == SlotStatus.HELD) & (Slot.hold_expires_at <= now),
                        ),
                    )
                    .order_by(Slot.starts_at)
                )
            ).all()
        )

    async def hold(self, slot_id: UUID, candidate_id: UUID) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(48)
        if not await self.holds.acquire(str(slot_id), token):
            raise ServiceError(
                code="slot_unavailable", message="Slot is not available", status_code=409
            )
        try:
            slot = await self.session.scalar(
                select(Slot).where(Slot.id == slot_id).with_for_update()
            )
            now = datetime.now(UTC)
            if (
                slot is None
                or slot.status in {SlotStatus.BOOKED, SlotStatus.BLOCKED}
                or (
                    slot.status == SlotStatus.HELD
                    and slot.hold_expires_at
                    and slot.hold_expires_at > now
                )
            ):
                raise ServiceError(
                    code="slot_unavailable", message="Slot is not available", status_code=409
                )
            expires = now + timedelta(seconds=self.settings.hold_ttl_seconds)
            slot.status = SlotStatus.HELD
            slot.held_by_candidate_id = candidate_id
            slot.hold_token_hash = self._hash(token)
            slot.hold_expires_at = expires
            await self.session.commit()
            return token, expires
        except Exception:
            await self.session.rollback()
            await self.holds.release(str(slot_id), token)
            raise

    async def create_booking(
        self, slot_id: UUID, candidate_id: UUID, token: str, idempotency_key: str
    ) -> Booking:
        existing = await self.session.scalar(
            select(Booking).where(
                Booking.candidate_id == candidate_id, Booking.idempotency_key == idempotency_key
            )
        )
        if existing:
            return existing
        if not await self.holds.matches(str(slot_id), token):
            raise ServiceError(
                code="invalid_or_expired_hold",
                message="Slot hold is invalid or expired",
                status_code=409,
            )
        slot = await self.session.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
        now = datetime.now(UTC)
        if (
            slot is None
            or slot.status != SlotStatus.HELD
            or slot.held_by_candidate_id != candidate_id
            or slot.hold_token_hash != self._hash(token)
            or slot.hold_expires_at is None
            or slot.hold_expires_at <= now
        ):
            raise ServiceError(
                code="invalid_or_expired_hold",
                message="Slot hold is invalid or expired",
                status_code=409,
            )
        booking = Booking(
            id=uuid4(),
            slot_id=slot.id,
            candidate_id=candidate_id,
            interviewer_id=slot.interviewer_id,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            time_range=Range(slot.starts_at, slot.ends_at, bounds="[)"),
            status=BookingStatus.PAYMENT_PENDING,
            occupies_time=True,
            amount_paise=self.settings.session_price_paise,
            currency="INR",
            idempotency_key=idempotency_key,
        )
        self.session.add_all(
            [
                booking,
                BookingStatusHistory(
                    booking_id=booking.id,
                    from_status=None,
                    to_status=booking.status,
                    changed_by=candidate_id,
                ),
            ]
        )
        slot.status = SlotStatus.BOOKED
        slot.hold_token_hash = None
        slot.hold_expires_at = None
        self._event("booking.BookingCreated.v1", booking)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            existing = await self.session.scalar(
                select(Booking).where(
                    Booking.candidate_id == candidate_id, Booking.idempotency_key == idempotency_key
                )
            )
            if existing:
                return cast(Booking, existing)
            raise ServiceError(
                code="booking_overlap",
                message="Candidate or interviewer already has an overlapping booking",
                status_code=409,
            ) from exc
        await self.holds.release(str(slot_id), token)
        return booking

    async def transition(
        self, booking_id: UUID, target: BookingStatus, actor: UUID | None, reason: str | None = None
    ) -> Booking:
        booking = await self.session.scalar(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
        if booking is None:
            raise ServiceError(
                code="booking_not_found", message="Booking was not found", status_code=404
            )
        if not can_transition(booking.status, target):
            raise ServiceError(
                code="invalid_booking_transition",
                message=f"Cannot transition booking from {booking.status.value} to {target.value}",
                status_code=409,
            )
        previous = booking.status
        booking.status = target
        booking.occupies_time = occupies_time(target)
        booking.updated_at = utc_now()
        self.session.add(
            BookingStatusHistory(
                booking_id=booking.id,
                from_status=previous,
                to_status=target,
                reason=reason,
                changed_by=actor,
            )
        )
        event = {
            BookingStatus.CONFIRMED: "BookingConfirmed",
            BookingStatus.CANCELLED: "BookingCancelled",
            BookingStatus.COMPLETED: "BookingCompleted",
            BookingStatus.CANDIDATE_NO_SHOW: "CandidateNoShow",
            BookingStatus.INTERVIEWER_NO_SHOW: "InterviewerNoShow",
            BookingStatus.RESCHEDULED: "BookingRescheduled",
        }.get(target)
        if event:
            self._event(f"booking.{event}.v1", booking)
        if not booking.occupies_time:
            await self.session.execute(
                update(Slot).where(Slot.id == booking.slot_id).values(status=SlotStatus.AVAILABLE)
            )
        await self.session.commit()
        return booking

    async def cancel_by_candidate(
        self, booking_id: UUID, candidate_id: UUID, reason: str | None
    ) -> Booking:
        booking = await self.session.scalar(
            select(Booking).where(Booking.id == booking_id, Booking.candidate_id == candidate_id)
        )
        if booking is None:
            raise ServiceError(
                code="booking_not_found", message="Booking was not found", status_code=404
            )
        return await self.transition(booking_id, BookingStatus.CANCELLED, candidate_id, reason)

    async def handle_payment(
        self, event_id: UUID, event_type: str, payment_id: UUID, booking_id: UUID
    ) -> Booking:
        if await self.session.get(ProcessedEvent, event_id):
            booking = await self.session.get(Booking, booking_id)
            assert booking is not None
            return booking
        booking = await self.session.scalar(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
        if booking is None:
            raise ServiceError(
                code="booking_not_found", message="Booking was not found", status_code=404
            )
        self.session.add(ProcessedEvent(event_id=event_id, event_type=event_type))
        booking.payment_id = payment_id
        target = (
            BookingStatus.BOOKED
            if event_type == "payment.captured.v1"
            else BookingStatus.PAYMENT_FAILED
        )
        previous = booking.status
        if not can_transition(previous, target):
            raise ServiceError(
                code="invalid_booking_transition",
                message="Payment event is invalid for booking state",
                status_code=409,
            )
        booking.status = target
        booking.occupies_time = occupies_time(target)
        self.session.add(
            BookingStatusHistory(booking_id=booking.id, from_status=previous, to_status=target)
        )
        self._event("booking.BookingPaymentRecorded.v1", booking)
        await self.session.commit()
        return cast(Booking, booking)

    async def expire_holds(self) -> int:
        now = datetime.now(UTC)
        ids = list(
            (
                await self.session.scalars(
                    update(Slot)
                    .where(Slot.status == SlotStatus.HELD, Slot.hold_expires_at <= now)
                    .values(
                        status=SlotStatus.AVAILABLE,
                        held_by_candidate_id=None,
                        hold_token_hash=None,
                        hold_expires_at=None,
                    )
                    .returning(Slot.id)
                )
            ).all()
        )
        await self.session.commit()
        return len(ids)

    def _event(self, name: str, booking: Booking) -> None:
        self.session.add(
            OutboxEvent(
                event_type=name,
                event_version=1,
                correlation_id=get_correlation_id(),
                payload={
                    "booking_id": str(booking.id),
                    "candidate_id": str(booking.candidate_id),
                    "interviewer_id": str(booking.interviewer_id),
                    "status": booking.status.value,
                },
            )
        )

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
