import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from app.infrastructure.holds import RedisHoldStore
from conftest import headers
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from roundready_common.errors import ServiceError


def generate(
    client: TestClient, admin: dict[str, str], interviewer: UUID, start: datetime
) -> dict[str, object]:
    response = client.post(
        "/v1/internal/slots/generate",
        headers=admin,
        json={
            "interviewer_id": str(interviewer),
            "windows": [
                {
                    "starts_at": start.isoformat(),
                    "ends_at": (start + timedelta(minutes=20)).isoformat(),
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    return cast(list[dict[str, object]], response.json())[0]


def book(
    client: TestClient, candidate: dict[str, str], slot_id: str, key: str
) -> tuple[int, dict[str, object]]:
    held = client.post(f"/v1/slots/{slot_id}/hold", headers=candidate)
    assert held.status_code == 200, held.text
    response = client.post(
        "/v1/bookings",
        headers={**candidate, "Idempotency-Key": key},
        json={"slot_id": slot_id, "hold_token": held.json()["hold_token"]},
    )
    return response.status_code, response.json()


def test_simultaneous_holds_allow_one_winner(client: TestClient) -> None:
    slot = generate(client, headers("admin"), uuid4(), datetime(2030, 1, 1, 10, tzinfo=UTC))
    slot_id = str(slot["id"])
    candidates = [headers(), headers()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda h: client.post(f"/v1/slots/{slot_id}/hold", headers=h).status_code,
                candidates,
            )
        )
    assert sorted(results) == [200, 409]


def test_two_candidates_cannot_concurrently_book_same_slot(client: TestClient) -> None:
    slot = generate(client, headers("admin"), uuid4(), datetime(2030, 1, 1, 11, tzinfo=UTC))
    slot_id = str(slot["id"])

    def attempt(candidate: dict[str, str], key: str) -> int:
        held = client.post(f"/v1/slots/{slot_id}/hold", headers=candidate)
        if held.status_code != 200:
            return held.status_code
        return client.post(
            "/v1/bookings",
            headers={**candidate, "Idempotency-Key": key},
            json={"slot_id": slot_id, "hold_token": held.json()["hold_token"]},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(attempt, headers(), "concurrent-candidate-one"),
            pool.submit(attempt, headers(), "concurrent-candidate-two"),
        ]
        results = [future.result() for future in futures]

    assert results.count(201) == 1
    assert results.count(409) == 1


def test_idempotent_booking_creation(client: TestClient) -> None:
    candidate = headers()
    slot = generate(client, headers("admin"), uuid4(), datetime(2030, 1, 2, 10, tzinfo=UTC))
    held = client.post(f"/v1/slots/{slot['id']}/hold", headers=candidate).json()
    request = {"slot_id": slot["id"], "hold_token": held["hold_token"]}
    request_headers = {**candidate, "Idempotency-Key": "same-request-key"}
    first = client.post("/v1/bookings", headers=request_headers, json=request)
    second = client.post("/v1/bookings", headers=request_headers, json=request)
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["id"] == second.json()["id"] and first.json()["amount_paise"] == 20000


def test_candidate_overlap_rejected_by_database(client: TestClient) -> None:
    candidate = headers()
    admin = headers("admin")
    start = datetime(2030, 1, 3, 10, tzinfo=UTC)
    first = generate(client, admin, uuid4(), start)
    second = generate(client, admin, uuid4(), start + timedelta(minutes=10))
    assert book(client, candidate, str(first["id"]), "overlap-first")[0] == 201
    status, body = book(client, candidate, str(second["id"]), "overlap-second")
    error = cast(dict[str, Any], body["error"])
    assert status == 409 and error["code"] == "booking_overlap"


def test_interviewer_overlap_rejected_by_database(client: TestClient) -> None:
    interviewer = uuid4()
    admin = headers("admin")
    start = datetime(2030, 1, 4, 10, tzinfo=UTC)
    first = generate(client, admin, interviewer, start)
    second = generate(client, admin, interviewer, start + timedelta(minutes=10))
    assert book(client, headers(), str(first["id"]), "interviewer-first")[0] == 201
    assert book(client, headers(), str(second["id"]), "interviewer-second")[0] == 409


def test_payment_event_and_invalid_transition(client: TestClient) -> None:
    admin = headers("admin")
    slot = generate(client, admin, uuid4(), datetime(2030, 1, 5, 10, tzinfo=UTC))
    status, booking = book(client, headers(), str(slot["id"]), "payment-booking")
    assert status == 201
    payment = client.post(
        "/v1/internal/payment-events",
        headers=admin,
        json={
            "event_id": str(uuid4()),
            "payment_id": str(uuid4()),
            "booking_id": booking["id"],
            "event_type": "payment.captured.v1",
        },
    )
    assert payment.json()["status"] == "booked"
    invalid = client.post(
        f"/v1/admin/bookings/{booking['id']}/transition",
        headers=admin,
        json={"status": "completed"},
    )
    assert invalid.status_code == 409
    confirmed = client.post(
        f"/v1/admin/bookings/{booking['id']}/transition",
        headers=admin,
        json={"status": "confirmed"},
    )
    assert confirmed.json()["status"] == "confirmed"


def test_redis_lock_expires(infrastructure: tuple[str, str]) -> None:
    async def scenario() -> None:
        redis = Redis.from_url(infrastructure[1], decode_responses=True)
        store = RedisHoldStore(redis, 1)
        assert await store.acquire("expiry-test", "token-one")
        await asyncio.sleep(1.1)
        assert await store.acquire("expiry-test", "token-two")
        await redis.aclose()

    asyncio.run(scenario())


def test_redis_failure_maps_to_service_unavailable() -> None:
    class UnavailableRedis:
        async def set(self, *_args: object, **_kwargs: object) -> None:
            raise RedisConnectionError("unavailable")

    async def scenario() -> None:
        store = RedisHoldStore(cast(Any, UnavailableRedis()), 300)
        try:
            await store.acquire("slot", "token")
        except ServiceError as exc:
            assert exc.status_code == 503
            assert exc.code == "hold_store_unavailable"
        else:
            raise AssertionError("Redis failure was not mapped")

    asyncio.run(scenario())


def test_hold_expiry_releases_slot(client: TestClient) -> None:
    import time

    slot = generate(client, headers("admin"), uuid4(), datetime(2030, 1, 6, 10, tzinfo=UTC))
    first = headers()
    second = headers()
    assert client.post(f"/v1/slots/{slot['id']}/hold", headers=first).status_code == 200
    time.sleep(2.1)
    assert client.post(f"/v1/slots/{slot['id']}/hold", headers=second).status_code == 200


def test_persistence_after_restart(client: TestClient) -> None:
    slot = generate(client, headers("admin"), uuid4(), datetime(2030, 1, 7, 10, tzinfo=UTC))
    status, booking = book(client, headers(), str(slot["id"]), "persistent-booking")
    assert status == 201
    from app.main import create_app

    with TestClient(create_app()) as restarted:
        duplicate_headers = headers(user_id=UUID(str(booking["candidate_id"])))
        # The unique idempotency record remains after the process-level restart.
        response = restarted.post(
            "/v1/bookings",
            headers={**duplicate_headers, "Idempotency-Key": "persistent-booking"},
            json={"slot_id": slot["id"], "hold_token": "x" * 32},
        )
    assert response.status_code == 201 and response.json()["id"] == booking["id"]
