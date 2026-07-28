from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import API_VERSIONS, PIPELINE_VERSION
from validation.cleaner import clean_record
from validation.schema import AirQualityRecord
from validation.validator import validate_record


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def standardize_record(record: dict[str, Any], run_id: str) -> AirQualityRecord | None:
    cleaned = clean_record(record)
    source = cleaned.get("source")
    response_time_seconds = cleaned.get("response_time_seconds")
    response_time_ms = int(float(response_time_seconds) * 1000) if response_time_seconds is not None else 0
    standardized_payload = {
        **cleaned,
        "run_id": run_id,
        "pipeline_version": PIPELINE_VERSION,
        "api_version": API_VERSIONS.get(source),
        "retrieved_at": _utc_now(),
        "response_time_ms": response_time_ms,
    }
    return validate_record(standardized_payload)


def standardize_records(records: list[dict[str, Any]], run_id: str) -> list[AirQualityRecord]:
    standardized: list[AirQualityRecord] = []
    for record in records:
        standardized_record = standardize_record(record, run_id)
        if standardized_record is not None:
            standardized.append(standardized_record)
    return standardized

