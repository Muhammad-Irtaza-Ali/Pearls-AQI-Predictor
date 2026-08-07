from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from typing import Any, Iterable


POLLUTANT_FIELDS = {"aqi", "pm25", "pm10", "co", "no", "no2", "so2", "o3", "nh3"}
SENTINEL_NUMBERS = {-9999, -9999.0, -999, -999.0, 9999, 9999.0}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if not text or text.upper() == "N/A":
            return None
        return text
    return value


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in record.items():
        normalized_value = _normalize_value(value)
        if key in POLLUTANT_FIELDS:
            if normalized_value in SENTINEL_NUMBERS:
                cleaned[key] = None
                continue
            if key == "aqi" and isinstance(normalized_value, float):
                cleaned[key] = int(round(normalized_value))
                continue
            if isinstance(normalized_value, (int, float)) and normalized_value < 0:
                cleaned[key] = None
                continue
        cleaned[key] = normalized_value
    return cleaned


def deduplicate_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: "OrderedDict[tuple[Any, ...], dict[str, Any]]" = OrderedDict()
    for record in records:
        key = (
            record.get("city"),
            record.get("data_date"),
            record.get("timestamp"),
            record.get("source"),
        )
        if key not in seen:
            seen[key] = record
    return list(seen.values())
