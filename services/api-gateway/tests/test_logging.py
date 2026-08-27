from roundready_common.logging import add_correlation_id


def test_explicit_event_correlation_id_is_not_overwritten() -> None:
    event: dict[str, object] = {"event": "consumed", "correlation_id": "event-correlation"}
    assert add_correlation_id(object(), "info", event)["correlation_id"] == "event-correlation"
