from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    root.setLevel(level)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)


def log_api_event(*, city: str, api: str, status: str, response_time_ms: int, reason: str | None = None) -> None:
    logger = logging.getLogger("ingestion")
    message = f"City={city} | API={api} | Status={status} | ResponseTime={response_time_ms}ms"
    if reason:
        message += f" | Reason={reason}"
    logger.info(message)

