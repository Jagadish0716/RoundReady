from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from app.config import Settings
from app.infrastructure.booking import BookingClient
from roundready_common.errors import ServiceError


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 409, 500])
async def test_booking_contract_fails_closed(status: int) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json={}))
    real_client = httpx.AsyncClient(transport=transport)
    with patch("app.infrastructure.booking.httpx.AsyncClient", return_value=real_client):
        with pytest.raises(ServiceError) as caught:
            await BookingClient(Settings()).validate(uuid4(), uuid4())
    assert caught.value.status_code == (503 if status == 500 else 409)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_id", str(uuid4())),
        ("amount_paise", 1),
        ("currency", "USD"),
        ("status", "confirmed"),
    ],
)
async def test_booking_contract_rejects_inconsistent_response(field: str, value: object) -> None:
    booking, candidate = uuid4(), uuid4()
    data = {
        "id": str(booking),
        "candidate_id": str(candidate),
        "amount_paise": 20000,
        "currency": "INR",
        "status": "payment_pending",
        field: value,
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=data))
    real_client = httpx.AsyncClient(transport=transport)
    with patch("app.infrastructure.booking.httpx.AsyncClient", return_value=real_client):
        with pytest.raises(ServiceError):
            await BookingClient(Settings()).validate(booking, candidate)
