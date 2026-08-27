"""Cross-cutting contracts and observability utilities for RoundReady."""

from roundready_common.errors import ApiError, ErrorDetail
from roundready_common.events import EventEnvelope

__all__ = ["ApiError", "ErrorDetail", "EventEnvelope"]
