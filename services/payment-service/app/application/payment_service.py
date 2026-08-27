from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    OutboxEvent,
    Payment,
    PaymentStatus,
    PaymentTransaction,
    Refund,
    RefundStatus,
    WebhookEvent,
    WebhookProcessingStatus,
)
from app.domain.providers import PaymentProvider


class PaymentService:
    def __init__(self, session: AsyncSession, provider: PaymentProvider, price: int) -> None:
        self.session, self.provider, self.price = session, provider, price

    async def create_order(
        self, booking_id: UUID, candidate_id: UUID, key: str
    ) -> tuple[Payment, dict[str, str | int] | None]:
        existing = await self.session.scalar(
            select(Payment).where(
                Payment.candidate_id == candidate_id, Payment.idempotency_key == key
            )
        )
        if existing:
            if existing.booking_id != booking_id:
                raise ServiceError(
                    code="idempotency_conflict",
                    message="Idempotency key was used for another booking",
                    status_code=409,
                )
            return existing, None
        payment = Payment(
            booking_id=booking_id,
            candidate_id=candidate_id,
            amount_paise=self.price,
            currency="INR",
            provider=self.provider.name,
            status=PaymentStatus.CREATED,
            idempotency_key=key,
        )
        self.session.add(payment)
        await self.session.flush()
        self._audit(payment, None, PaymentStatus.CREATED, "payment_created")
        try:
            order = await self.provider.create_order(
                amount_paise=self.price, currency="INR", idempotency_key=key
            )
            if order.amount_paise != self.price or order.currency != "INR":
                raise ValueError("Provider returned an inconsistent order")
        except Exception as exc:
            self._transition(payment, PaymentStatus.FAILED, "order_creation_failed")
            self._event("PaymentFailed", payment, {"reason": "order_creation_failed"})
            await self.session.commit()
            raise ServiceError(
                code="provider_error",
                message="Payment provider rejected the order",
                status_code=502,
            ) from exc
        payment.provider_order_id = order.order_id
        self._transition(payment, PaymentStatus.PENDING, "provider_order_created", order.order_id)
        await self.session.commit()
        return payment, order.checkout_data

    async def get(self, payment_id: UUID, user_id: UUID, admin: bool) -> Payment:
        payment = await self.session.get(Payment, payment_id)
        if payment is None or (not admin and payment.candidate_id != user_id):
            raise ServiceError(
                code="payment_not_found", message="Payment was not found", status_code=404
            )
        return payment

    async def process_webhook(
        self, event_id: str, event_type: str, payload: dict[str, object]
    ) -> tuple[bool, bool]:
        webhook = await self.session.scalar(
            select(WebhookEvent)
            .where(
                WebhookEvent.provider == self.provider.name,
                WebhookEvent.provider_event_id == event_id,
            )
            .with_for_update()
        )
        if webhook and webhook.processing_status in {
            WebhookProcessingStatus.PROCESSED,
            WebhookProcessingStatus.IGNORED,
        }:
            return True, webhook.processing_status is WebhookProcessingStatus.IGNORED
        if webhook is None:
            webhook = WebhookEvent(
                provider=self.provider.name,
                provider_event_id=event_id,
                event_type=event_type,
                payload=payload,
                processing_status=WebhookProcessingStatus.RECEIVED,
            )
            self.session.add(webhook)
            try:
                await self.session.flush()
            except IntegrityError:
                await self.session.rollback()
                return True, False
        supported = {"payment.authorized", "payment.captured", "payment.failed", "refund.processed"}
        if event_type not in supported:
            webhook.processing_status = WebhookProcessingStatus.IGNORED
            webhook.processed_at = datetime.now(UTC)
            await self.session.commit()
            return False, True
        try:
            await self._apply_webhook(event_type, payload)
        except ServiceError as exc:
            webhook.processing_status = WebhookProcessingStatus.FAILED
            webhook.last_error = exc.code
            await self.session.commit()
            raise
        webhook.processing_status = WebhookProcessingStatus.PROCESSED
        webhook.processed_at = datetime.now(UTC)
        webhook.last_error = None
        await self.session.commit()
        return False, False

    async def _apply_webhook(self, event_type: str, payload: dict[str, object]) -> None:
        root = payload.get("payload")
        if not isinstance(root, dict):
            raise self._bad_webhook()
        key = "refund" if event_type.startswith("refund.") else "payment"
        wrapper = root.get(key)
        entity = wrapper.get("entity") if isinstance(wrapper, dict) else None
        if not isinstance(entity, dict):
            raise self._bad_webhook()
        if key == "refund":
            await self._refund_webhook(entity)
            return
        order_id, provider_payment_id = entity.get("order_id"), entity.get("id")
        payment = await self.session.scalar(
            select(Payment).where(Payment.provider_order_id == order_id).with_for_update()
        )
        if payment is None:
            raise ServiceError(
                code="payment_not_found", message="Webhook payment was not found", status_code=503
            )
        if (
            entity.get("amount") != payment.amount_paise
            or entity.get("currency") != payment.currency
        ):
            raise ServiceError(
                code="webhook_payment_mismatch",
                message="Webhook payment details do not match the order",
                status_code=400,
            )
        payment.provider_payment_id = str(provider_payment_id)
        target = {
            "payment.authorized": PaymentStatus.AUTHORIZED,
            "payment.captured": PaymentStatus.CAPTURED,
            "payment.failed": PaymentStatus.FAILED,
        }[event_type]
        if payment.status == target:
            return
        allowed = {
            PaymentStatus.PENDING: {
                PaymentStatus.AUTHORIZED,
                PaymentStatus.CAPTURED,
                PaymentStatus.FAILED,
            },
            PaymentStatus.AUTHORIZED: {PaymentStatus.CAPTURED, PaymentStatus.FAILED},
        }
        if target not in allowed.get(payment.status, set()):
            raise ServiceError(
                code="invalid_payment_transition",
                message="Payment status transition is invalid",
                status_code=409,
            )
        self._transition(payment, target, event_type, str(provider_payment_id))
        if target is PaymentStatus.CAPTURED:
            self._event("PaymentCaptured", payment)
        elif target is PaymentStatus.FAILED:
            self._event("PaymentFailed", payment)

    async def refund(self, payment_id: UUID, amount: int | None, reason: str) -> Refund:
        payment = await self.session.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        if payment is None:
            raise ServiceError(
                code="payment_not_found", message="Payment was not found", status_code=404
            )
        refund_amount = amount or payment.amount_paise
        already = await self.session.scalar(
            select(func.coalesce(func.sum(Refund.amount_paise), 0)).where(
                Refund.payment_id == payment.id, Refund.status == RefundStatus.PROCESSED
            )
        )
        already_amount = int(already or 0)
        if (
            payment.status
            not in {
                PaymentStatus.CAPTURED,
                PaymentStatus.PARTIALLY_REFUNDED,
            }
            or refund_amount > payment.amount_paise - already_amount
        ):
            raise ServiceError(
                code="invalid_refund",
                message="Refund amount or payment status is invalid",
                status_code=409,
            )
        if not payment.provider_payment_id:
            raise ServiceError(
                code="invalid_refund",
                message="Provider payment reference is missing",
                status_code=409,
            )
        refund = Refund(
            payment_id=payment.id,
            amount_paise=refund_amount,
            reason=reason,
            status=RefundStatus.PENDING,
        )
        self.session.add(refund)
        self._transition(payment, PaymentStatus.REFUND_PENDING, "refund_requested")
        await self.session.flush()
        try:
            result = await self.provider.refund(
                provider_payment_id=payment.provider_payment_id,
                amount_paise=refund_amount,
                idempotency_key=str(refund.id),
            )
        except Exception as exc:
            refund.status = RefundStatus.FAILED
            self._transition(payment, PaymentStatus.CAPTURED, "refund_failed")
            await self.session.commit()
            raise ServiceError(
                code="provider_error",
                message="Payment provider rejected the refund",
                status_code=502,
            ) from exc
        refund.provider_refund_id = result.refund_id
        if result.processed:
            refund.status = RefundStatus.PROCESSED
            total = already_amount + refund_amount
            target = (
                PaymentStatus.REFUNDED
                if total == payment.amount_paise
                else PaymentStatus.PARTIALLY_REFUNDED
            )
            self._transition(payment, target, "refund_processed", result.refund_id)
            self._event(
                "PaymentRefunded",
                payment,
                {"refund_id": str(refund.id), "amount_paise": refund_amount},
            )
        await self.session.commit()
        return refund

    async def _refund_webhook(self, entity: dict[str, Any]) -> None:
        refund = await self.session.scalar(
            select(Refund)
            .where(Refund.provider_refund_id == str(entity.get("id")))
            .with_for_update()
        )
        if refund is None:
            raise ServiceError(
                code="refund_not_found", message="Webhook refund was not found", status_code=503
            )
        if refund.status is RefundStatus.PROCESSED:
            return
        payment = await self.session.get(Payment, refund.payment_id)
        if payment is None:
            raise self._bad_webhook()
        refund.status = RefundStatus.PROCESSED
        total = await self.session.scalar(
            select(func.sum(Refund.amount_paise)).where(
                Refund.payment_id == payment.id, Refund.status == RefundStatus.PROCESSED
            )
        )
        target = (
            PaymentStatus.REFUNDED
            if int(total or 0) == payment.amount_paise
            else PaymentStatus.PARTIALLY_REFUNDED
        )
        self._transition(payment, target, "refund.processed", refund.provider_refund_id)
        self._event(
            "PaymentRefunded",
            payment,
            {"refund_id": str(refund.id), "amount_paise": refund.amount_paise},
        )

    def _transition(
        self, payment: Payment, target: PaymentStatus, action: str, reference: str | None = None
    ) -> None:
        old = payment.status
        payment.status = target
        self._audit(payment, old, target, action, reference)

    def _audit(
        self,
        payment: Payment,
        old: PaymentStatus | None,
        target: PaymentStatus,
        action: str,
        reference: str | None = None,
    ) -> None:
        self.session.add(
            PaymentTransaction(
                payment_id=payment.id,
                action=action,
                from_status=old,
                to_status=target,
                amount_paise=payment.amount_paise,
                provider_reference=reference,
            )
        )

    def _event(
        self, event_type: str, payment: Payment, extra: dict[str, object] | None = None
    ) -> None:
        payload: dict[str, object] = {
            "payment_id": str(payment.id),
            "booking_id": str(payment.booking_id),
            "amount_paise": payment.amount_paise,
            "currency": payment.currency,
        }
        payload.update(extra or {})
        self.session.add(
            OutboxEvent(event_type=event_type, correlation_id=get_correlation_id(), payload=payload)
        )

    @staticmethod
    def _bad_webhook() -> ServiceError:
        return ServiceError(
            code="invalid_webhook_payload", message="Webhook payload is invalid", status_code=400
        )
