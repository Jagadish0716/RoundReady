import json
from typing import cast
from uuid import UUID, uuid4

import httpx
from conftest import FAKE_PROVIDER, WEBHOOK_SECRET, identity, signature
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


def create_payment(
    client: TestClient, key: str = "idem-key-0001", user_id: UUID | None = None
) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(
            "/v1/payments/orders",
            json={"booking_id": str(uuid4())},
            headers={**identity(user_id=user_id), "Idempotency-Key": key},
        ),
    )


def webhook(
    client: TestClient,
    event_id: str,
    event_type: str,
    order_id: str,
    payment_id: str | None = None,
    *,
    valid: bool = True,
) -> httpx.Response:
    payload = {
        "event": event_type,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id or f"pay_{event_id}",
                    "order_id": order_id,
                    "amount": 20000,
                    "currency": "INR",
                }
            }
        },
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    return cast(
        httpx.Response,
        client.post(
            "/v1/webhooks/razorpay",
            content=body,
            headers={
                "content-type": "application/json",
                "X-Razorpay-Event-Id": event_id,
                "X-Razorpay-Signature": signature(body) if valid else "invalid",
            },
        ),
    )


def test_health_and_fixed_200_rupee_order(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    response = create_payment(client)
    assert response.status_code == 201
    assert response.json()["amount_paise"] == 20000
    assert response.json()["currency"] == "INR"
    assert response.json()["status"] == "pending"
    assert "key_secret" not in json.dumps(response.json())


def test_order_idempotency_and_conflict(client: TestClient) -> None:
    user = uuid4()
    booking = uuid4()
    headers = {**identity(user_id=user), "Idempotency-Key": "same-key-0002"}
    first = client.post("/v1/payments/orders", json={"booking_id": str(booking)}, headers=headers)
    second = client.post("/v1/payments/orders", json={"booking_id": str(booking)}, headers=headers)
    conflict = client.post(
        "/v1/payments/orders", json={"booking_id": str(uuid4())}, headers=headers
    )
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["checkout_data"] is None
    assert conflict.status_code == 409


def test_invalid_signature_is_rejected(client: TestClient) -> None:
    payment = create_payment(client, "invalid-sig-key").json()
    response = webhook(
        client, "evt-invalid", "payment.captured", payment["provider_order_id"], valid=False
    )
    assert response.status_code == 401


def test_capture_and_duplicate_webhook(client: TestClient) -> None:
    payment = create_payment(client, "capture-key-001").json()
    first = webhook(client, "evt-captured", "payment.captured", payment["provider_order_id"])
    second = webhook(client, "evt-captured", "payment.captured", payment["provider_order_id"])
    assert first.status_code == 200 and first.json()["duplicate"] is False
    assert second.status_code == 200 and second.json()["duplicate"] is True
    result = client.get(
        f"/v1/payments/{payment['id']}", headers=identity(user_id=payment.get("candidate_id"))
    )
    # Candidate lookup is separately ownership protected; admin can inspect the resulting state.
    result = client.get(f"/v1/payments/{payment['id']}", headers=identity("admin"))
    assert result.json()["status"] == "captured"


def test_failure_and_unexpected_event(client: TestClient) -> None:
    payment = create_payment(client, "failure-key-001").json()
    assert (
        webhook(client, "evt-failed", "payment.failed", payment["provider_order_id"]).status_code
        == 200
    )
    state = client.get(f"/v1/payments/{payment['id']}", headers=identity("admin"))
    assert state.json()["status"] == "failed"
    ignored = webhook(client, "evt-unknown", "payment.magic", payment["provider_order_id"])
    assert ignored.status_code == 200 and ignored.json()["ignored"] is True


def test_failed_webhook_can_retry(client: TestClient) -> None:
    first = webhook(client, "evt-retry", "payment.captured", "order_retry-key-001")
    assert first.status_code == 503
    payment = create_payment(client, "retry-key-001").json()
    retry = webhook(client, "evt-retry", "payment.captured", payment["provider_order_id"])
    assert retry.status_code == 200
    state = client.get(f"/v1/payments/{payment['id']}", headers=identity("admin"))
    assert state.json()["status"] == "captured"


def test_full_refund_and_audit_event(client: TestClient, postgres_url: str) -> None:
    payment = create_payment(client, "refund-key-001").json()
    assert (
        webhook(
            client, "evt-for-refund", "payment.captured", payment["provider_order_id"]
        ).status_code
        == 200
    )
    response = client.post(
        f"/v1/admin/payments/{payment['id']}/refunds",
        json={"reason": "candidate cancellation"},
        headers=identity("admin"),
    )
    assert response.status_code == 201
    assert response.json()["amount_paise"] == 20000
    assert response.json()["status"] == "processed"
    state = client.get(f"/v1/payments/{payment['id']}", headers=identity("admin"))
    assert state.json()["status"] == "refunded"
    engine = create_engine(postgres_url)
    with engine.connect() as connection:
        event_types = (
            connection.execute(
                text("select event_type from outbox_events where payload->>'payment_id'=:id"),
                {"id": payment["id"]},
            )
            .scalars()
            .all()
        )
        assert event_types == ["payment.captured.v1", "payment.refunded.v1"]
    engine.dispose()


def test_persistence_and_database_constraints(client: TestClient, postgres_url: str) -> None:
    payment = create_payment(client, "persist-key-001").json()
    engine = create_engine(postgres_url)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("select count(*) from payments where id=:id"), {"id": payment["id"]}
            )
            == 1
        )
        assert (
            connection.scalar(
                text("select count(*) from payment_transactions where payment_id=:id"),
                {"id": payment["id"]},
            )
            == 2
        )
    engine.dispose()


def test_ownership_and_roles(client: TestClient) -> None:
    owner = uuid4()
    payment = create_payment(client, "ownership-key", owner).json()
    assert (
        client.get(f"/v1/payments/{payment['id']}", headers=identity(user_id=owner)).status_code
        == 200
    )
    assert client.get(f"/v1/payments/{payment['id']}", headers=identity()).status_code == 404
    assert create_payment(client, "admin-cannot-create", uuid4()).status_code == 201
    forbidden = client.post(
        "/v1/payments/orders",
        json={"booking_id": str(uuid4())},
        headers={**identity("admin"), "Idempotency-Key": "admin-key-001"},
    )
    assert forbidden.status_code == 403


def test_development_completion_is_owned_idempotent_and_authoritative(
    client: TestClient, postgres_url: str
) -> None:
    from app.config import get_settings
    from app.dependencies import get_payment_provider
    from app.infrastructure.development import DevelopmentPaymentProvider

    app = cast(FastAPI, client.app)
    settings = get_settings().model_copy(
        update={"environment": "test", "payment_provider": "development"}
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_payment_provider] = lambda: DevelopmentPaymentProvider(
        WEBHOOK_SECRET
    )
    try:
        owner = uuid4()
        payment = create_payment(client, "development-complete-owner", owner).json()
        endpoint = f"/v1/payments/{payment['id']}/development/complete"
        unrelated = client.post(endpoint, headers=identity())
        first = client.post(endpoint, headers=identity(user_id=owner), json={"amount_paise": 1})
        second = client.post(endpoint, headers=identity(user_id=owner))

        assert unrelated.status_code == 404
        assert first.status_code == 200 and second.status_code == 200
        assert first.json()["status"] == "captured"
        assert first.json()["amount_paise"] == 20000 and first.json()["currency"] == "INR"
        assert first.json()["id"] == second.json()["id"]
        serialized = json.dumps(first.json())
        assert "secret" not in serialized and "signature" not in serialized

        engine = create_engine(postgres_url)
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "select count(*) from outbox_events "
                        "where event_type='payment.captured.v1' and payload->>'payment_id'=:id"
                    ),
                    {"id": payment["id"]},
                )
                == 1
            )
        engine.dispose()
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides[get_payment_provider] = lambda: FAKE_PROVIDER


def test_development_completion_is_hidden_in_production(client: TestClient) -> None:
    from app.config import get_settings
    from app.dependencies import get_payment_provider
    from app.infrastructure.development import DevelopmentPaymentProvider

    app = cast(FastAPI, client.app)
    settings = get_settings().model_copy(
        update={"environment": "production", "payment_provider": "development"}
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_payment_provider] = lambda: DevelopmentPaymentProvider(
        WEBHOOK_SECRET
    )
    try:
        response = client.post(f"/v1/payments/{uuid4()}/development/complete", headers=identity())
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "development_payment_disabled"
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides[get_payment_provider] = lambda: FAKE_PROVIDER
