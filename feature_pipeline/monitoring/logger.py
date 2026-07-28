from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def log_api_event(
    *,
    city: str,
    api: str,
    status: str,
    response_time_ms: int | None = None,
    reason: str | None = None,
) -> None:
    message_parts = [f"City={city}", f"API={api}", f"Status={status}"]
    if response_time_ms is not None:
        message_parts.append(f"ResponseTime={response_time_ms}ms")
    if reason:
        message_parts.append(f"Reason={reason}")
    logging.getLogger("ingestion").info(" | ".join(message_parts))

