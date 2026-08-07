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
    endpoint = cleaned.get("endpoint")
    response_time_seconds = cleaned.get("response_time_seconds")
    response_time_ms = int(float(response_time_seconds) * 1000) if response_time_seconds is not None else 0
    retrieved_at = _utc_now()
    api_version = API_VERSIONS.get(source)
    if source == "openweather":
        endpoints = endpoint if isinstance(endpoint, list) else [endpoint]
        if any(isinstance(value, str) and "history.openweathermap.org/data/3.0/history/result" in value for value in endpoints):
            api_version = API_VERSIONS.get("openweather_history")
    lineage = {
        "source_api": source,
        "endpoint": endpoint,
        "city": cleaned.get("city"),
        "run_id": run_id,
        "retrieved_at": retrieved_at.isoformat(),
        "response_time_ms": response_time_ms,
        "response_time_seconds": response_time_seconds,
        "pipeline_version": PIPELINE_VERSION,
        "api_version": api_version,
    }
    standardized_payload = {
        **cleaned,
        "run_id": run_id,
        "pipeline_version": PIPELINE_VERSION,
        "api_version": api_version,
        "retrieved_at": retrieved_at,
        "response_time_ms": response_time_ms,
        "lineage": lineage,
    }
    return validate_record(standardized_payload)


def standardize_records(records: list[dict[str, Any]], run_id: str) -> list[AirQualityRecord]:
    standardized: list[AirQualityRecord] = []
    for record in records:
        standardized_record = standardize_record(record, run_id)
        if standardized_record is not None:
            standardized.append(standardized_record)
    return standardized

