import logging
import sys

import structlog

from roundready_common.correlation import get_correlation_id


def configure_logging(log_level: str) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level.upper())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            lambda _logger, _method, event: {**event, "correlation_id": get_correlation_id()},
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
