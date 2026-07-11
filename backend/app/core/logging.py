"""Structured (JSON) logging configuration.

Every log line is a single JSON object so it can be piped into any log
aggregator. Request-scoped fields (request_id, stage) are injected via
`extra=` at call sites, e.g. logger.info("chunking done", extra={"request_id": rid, "stage": "chunk"}).
"""
import json
import logging
import sys
import time
from typing import Any

RESERVED = set(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include any extra= fields passed at the call site
        for key, value in record.__dict__.items():
            if key not in RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
