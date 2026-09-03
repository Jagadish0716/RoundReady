import structlog
from roundready_common.correlation import valid_correlation_id
from roundready_common.logging import (
    add_correlation_id,
    add_trace_context,
    configure_logging,
    redact_sensitive_data,
)


def test_explicit_event_correlation_id_is_not_overwritten() -> None:
    event: dict[str, object] = {"event": "consumed", "correlation_id": "event-correlation"}
    assert add_correlation_id(object(), "info", event)["correlation_id"] == "event-correlation"


def test_correlation_ids_are_bounded_and_invalid_values_are_replaced() -> None:
    assert valid_correlation_id("request-123") == "request-123"
    assert valid_correlation_id("x" * 129) != "x" * 129
    assert valid_correlation_id("bad value") != "bad value"


def test_sensitive_log_fields_are_redacted() -> None:
    event = redact_sensitive_data(
        {
            "password": "secret",
            "nested": {"access_token": "jwt", "user_id": "user-123"},
            "correlation_id": "corr-123",
        }
    )
    assert event == {
        "password": "[REDACTED]",
        "nested": {"access_token": "[REDACTED]", "user_id": "user-123"},
        "correlation_id": "corr-123",
    }


def test_trace_context_is_optional_when_telemetry_is_disabled() -> None:
    event: dict[str, object] = {"message": "ok"}
    assert add_trace_context(object(), "info", event) == event


def test_production_logs_are_json_and_redact_sensitive_fields(capsys) -> None:
    configure_logging("INFO", "gateway", "production")
    structlog.get_logger().info(
        "request_finished", correlation_id="corr-1", status_code=200, password="secret"
    )
    output = capsys.readouterr().out
    assert '"service": "gateway"' in output
    assert '"environment": "production"' in output
    assert '"correlation_id": "corr-1"' in output
    assert "secret" not in output
