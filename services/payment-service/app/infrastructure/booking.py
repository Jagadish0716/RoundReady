from uuid import UUID

import httpx
from app.config import Settings
from roundready_common.errors import ServiceError


class BookingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def validate(self, booking_id: UUID, candidate_id: UUID) -> None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.settings.booking_service_url}/v1/internal/bookings/{booking_id}/payable",
                    headers={
                        "X-User-ID": str(candidate_id),
                        "X-User-Role": "candidate",
                        "X-Internal-Identity-Secret": (
                            self.settings.internal_identity_secret.get_secret_value()
                        ),
                    },
                )
            if response.status_code in {404, 409}:
                raise ServiceError(
                    code="booking_not_payable",
                    message="Payment cannot be created for this booking.",
                    status_code=409,
                )
            response.raise_for_status()
            data = response.json()
            if (
                data["id"] != str(booking_id)
                or data["candidate_id"] != str(candidate_id)
                or data["status"] != "payment_pending"
                or data["amount_paise"] != 20000
                or data["currency"] != "INR"
            ):
                raise ValueError("Invalid payable booking contract")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ServiceError(
                code="booking_validation_unavailable",
                message="Booking validation is unavailable. Try again shortly.",
                status_code=503,
            ) from exc
