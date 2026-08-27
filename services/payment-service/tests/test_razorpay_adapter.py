import hashlib
import hmac

import pytest
from app.infrastructure.razorpay import RazorpayTestAdapter


def test_webhook_signature_verification() -> None:
    adapter = RazorpayTestAdapter(
        "rzp_test_key", "key-secret", "webhook-secret", "https://api.razorpay.com/v1", True
    )
    body = b'{"event":"payment.captured"}'
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    assert adapter.verify_webhook(body, signature)
    assert not adapter.verify_webhook(body, "bad-signature")


def test_live_credentials_are_refused() -> None:
    with pytest.raises(ValueError, match="test-mode"):
        RazorpayTestAdapter(
            "rzp_live_key", "key-secret", "webhook-secret", "https://api.razorpay.com/v1", False
        )
