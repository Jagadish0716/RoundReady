from datetime import UTC, datetime, timedelta
from uuid import UUID

from roundready_common.events import EventEnvelope
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.domain.models import (
    Channel,
    DeadLetterRecord,
    DeliveryAttempt,
    DeliveryStatus,
    Notification,
    ProcessedEvent,
)
from app.domain.providers import NotificationProvider, ProviderMessage, RecipientResolver
from app.domain.templates import TemplateError, template_for_event


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        providers: dict[Channel, NotificationProvider],
        settings: Settings,
        resolver: RecipientResolver | None = None,
    ) -> None:
        self.db = session
        self.providers = providers
        self.settings = settings
        self.resolver = resolver

    async def consume(self, event: EventEnvelope) -> list[Notification]:
        if await self.db.get(ProcessedEvent, event.event_id):
            return []
        template = template_for_event(event.event_type)
        if template is None:
            self._dead_letter(
                event.event_id, None, event.event_type, event.correlation_id, "unsupported_event"
            )
            self.db.add(ProcessedEvent(event_id=event.event_id, event_type=event.event_type))
            await self.db.commit()
            return []
        recipients: list[tuple[Channel, str]] = []
        email = event.payload.get("recipient_email")
        whatsapp = event.payload.get("recipient_whatsapp")
        if isinstance(email, str) and email:
            recipients.append((Channel.EMAIL, email))
        if isinstance(whatsapp, str) and whatsapp:
            recipients.append((Channel.WHATSAPP, whatsapp))
        candidate_id = event.payload.get("candidate_id")
        if not recipients and isinstance(candidate_id, str) and self.resolver is not None:
            destination = await self.resolver.resolve(candidate_id, event.correlation_id)
            if destination.email:
                recipients.append((Channel.EMAIL, destination.email))
            if destination.phone:
                recipients.append((Channel.WHATSAPP, destination.phone))
        if not recipients:
            self._dead_letter(
                event.event_id, None, event.event_type, event.correlation_id, "recipient_missing"
            )
            self.db.add(ProcessedEvent(event_id=event.event_id, event_type=event.event_type))
            await self.db.commit()
            return []
        context = dict(event.payload)
        if "amount_paise" in context and "amount_rupees" not in context:
            amount = context["amount_paise"]
            if isinstance(amount, int):
                context["amount_rupees"] = amount // 100
        try:
            subject, body = template.render(context)
        except TemplateError:
            self._dead_letter(
                event.event_id,
                None,
                event.event_type,
                event.correlation_id,
                "template_context_invalid",
            )
            self.db.add(ProcessedEvent(event_id=event.event_id, event_type=event.event_type))
            await self.db.commit()
            return []
        records = [
            Notification(
                event_id=event.event_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                recipient=recipient,
                channel=channel,
                template=template.name,
                template_version=template.version,
                rendered_subject=subject,
                rendered_body=body,
                status=DeliveryStatus.PENDING,
            )
            for channel, recipient in recipients
        ]
        self.db.add_all(
            [*records, ProcessedEvent(event_id=event.event_id, event_type=event.event_type)]
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            return []
        for record in records:
            await self.deliver(record.id)
        return records

    async def deliver(self, notification_id: UUID, now: datetime | None = None) -> Notification:
        current = now or datetime.now(UTC)
        record = await self.db.scalar(
            select(Notification).where(Notification.id == notification_id).with_for_update()
        )
        if record is None:
            raise LookupError("notification not found")
        if record.status in {DeliveryStatus.SENT, DeliveryStatus.DEAD_LETTERED}:
            return record
        if record.next_attempt_at and record.next_attempt_at > current:
            return record
        record.attempt_count += 1
        attempt = DeliveryAttempt(
            notification_id=record.id,
            attempt_number=record.attempt_count,
            started_at=current,
            successful=False,
        )
        self.db.add(attempt)
        provider = self.providers[record.channel]
        try:
            reference = await provider.send(
                ProviderMessage(
                    recipient=record.recipient,
                    subject=record.rendered_subject,
                    body=record.rendered_body,
                    idempotency_key=str(record.id),
                )
            )
        except Exception as exc:
            code = type(exc).__name__
            attempt.finished_at = datetime.now(UTC)
            attempt.error_code = code
            record.last_error_code = code
            if record.attempt_count >= self.settings.max_delivery_attempts:
                record.status = DeliveryStatus.DEAD_LETTERED
                record.next_attempt_at = None
                self._dead_letter(
                    record.event_id,
                    record.id,
                    record.event_type,
                    record.correlation_id,
                    "delivery_attempts_exhausted",
                    {"attempt_count": record.attempt_count, "error_code": code},
                )
            else:
                delay = min(
                    self.settings.retry_base_seconds * (2 ** (record.attempt_count - 1)),
                    self.settings.retry_max_seconds,
                )
                record.status = DeliveryStatus.RETRY_SCHEDULED
                record.next_attempt_at = current + timedelta(seconds=delay)
            await self.db.commit()
            return record
        attempt.successful = True
        attempt.finished_at = datetime.now(UTC)
        attempt.provider_reference = reference
        record.status = DeliveryStatus.SENT
        record.provider_reference = reference
        record.sent_at = attempt.finished_at
        record.next_attempt_at = None
        record.last_error_code = None
        await self.db.commit()
        return record

    async def retry_due(self, now: datetime | None = None, batch_size: int = 100) -> int:
        current = now or datetime.now(UTC)
        ids = list(
            (
                await self.db.scalars(
                    select(Notification.id)
                    .where(
                        Notification.status.in_(
                            [DeliveryStatus.PENDING, DeliveryStatus.RETRY_SCHEDULED]
                        ),
                        (Notification.next_attempt_at.is_(None))
                        | (Notification.next_attempt_at <= current),
                    )
                    .order_by(Notification.created_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        delivered = 0
        for notification_id in ids:
            result = await self.deliver(notification_id, current)
            if result.status is DeliveryStatus.SENT:
                delivered += 1
        return delivered

    def _dead_letter(
        self,
        event_id: UUID | None,
        notification_id: UUID | None,
        event_type: str,
        correlation_id: str,
        reason: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            DeadLetterRecord(
                event_id=event_id,
                notification_id=notification_id,
                event_type=event_type,
                correlation_id=correlation_id,
                reason_code=reason,
                metadata_json=metadata or {},
            )
        )
