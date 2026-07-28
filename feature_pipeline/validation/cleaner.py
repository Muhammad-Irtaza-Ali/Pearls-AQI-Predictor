from __future__ import annotations

import json
from typing import Any


def _clean_string(value: str) -> str | None:
    text = value.strip()
    if not text or text.upper() == "N/A":
        return None
    return text


def _maybe_json(value: str) -> Any:
    text = value.strip()
    if not text:
        return None
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def clean_value(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = _clean_string(value)
        if cleaned is None:
            return None
        return _maybe_json(cleaned)
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    return value


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: clean_value(value) for key, value in record.items()}


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduplicated: list[dict[str, Any]] = []
    for record in records:
        signature = (
            record.get("source"),
            record.get("city"),
            record.get("timestamp"),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduplicated.append(record)
    return deduplicated

