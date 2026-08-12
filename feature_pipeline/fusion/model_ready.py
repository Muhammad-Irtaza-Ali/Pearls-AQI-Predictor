from __future__ import annotations

from datetime import date, datetime
from typing import Any

from validation.schema import AirQualityRecord


MODEL_READY_GOLD_COLUMNS = [
    "timestamp",
    "data_date",
    "city",
    "country",
    "latitude",
    "longitude",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "rain",
    "aqi",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
    "source",
    "status",
    "run_id",
    "pipeline_version",
    "api_version",
    "retrieved_at",
    "response_time_ms",
    "response_time_seconds",
]


def _record_data_date(record: AirQualityRecord) -> date:
    return record.data_date or record.timestamp.date()


def _coerce_datetime(value: Any) -> Any:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


def _coerce_date(value: Any) -> Any:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


def project_model_ready_record(
    record: AirQualityRecord | dict[str, Any],
    *,
    source: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """
    Convert a validated record into a compact model-ready payload.

    The gold layer keeps only the fields that are useful for training,
    scoring, and reproducible lineage at the row level.
    """

    if isinstance(record, dict):
        payload = dict(record)
        timestamp = _coerce_datetime(payload.get("timestamp"))
        data_date = _coerce_date(payload.get("data_date"))
        if data_date is None and isinstance(timestamp, datetime):
            data_date = timestamp.date()
        return {
            "timestamp": timestamp,
            "data_date": data_date,
            "city": payload.get("city"),
            "country": payload.get("country"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "temperature": payload.get("temperature"),
            "humidity": payload.get("humidity"),
            "pressure": payload.get("pressure"),
            "wind_speed": payload.get("wind_speed"),
            "wind_direction": payload.get("wind_direction"),
            "cloud_cover": payload.get("cloud_cover"),
            "rain": payload.get("rain"),
            "aqi": payload.get("aqi"),
            "pm25": payload.get("pm25"),
            "pm10": payload.get("pm10"),
            "co": payload.get("co"),
            "no": payload.get("no"),
            "no2": payload.get("no2"),
            "so2": payload.get("so2"),
            "o3": payload.get("o3"),
            "nh3": payload.get("nh3"),
            "source": source or payload.get("source"),
            "status": status or payload.get("status"),
            "run_id": payload.get("run_id"),
            "pipeline_version": payload.get("pipeline_version"),
            "api_version": payload.get("api_version"),
            "retrieved_at": _coerce_datetime(payload.get("retrieved_at")),
            "response_time_ms": payload.get("response_time_ms"),
            "response_time_seconds": payload.get("response_time_seconds"),
        }

    return {
        "timestamp": record.timestamp,
        "data_date": _record_data_date(record),
        "city": record.city,
        "country": record.country,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "pressure": record.pressure,
        "wind_speed": record.wind_speed,
        "wind_direction": record.wind_direction,
        "cloud_cover": record.cloud_cover,
        "rain": record.rain,
        "aqi": record.aqi,
        "pm25": record.pm25,
        "pm10": record.pm10,
        "co": record.co,
        "no": record.no,
        "no2": record.no2,
        "so2": record.so2,
        "o3": record.o3,
        "nh3": record.nh3,
        "source": source or record.source,
        "status": status or record.status,
        "run_id": record.run_id,
        "pipeline_version": record.pipeline_version,
        "api_version": record.api_version,
        "retrieved_at": record.retrieved_at,
        "response_time_ms": record.response_time_ms,
        "response_time_seconds": record.response_time_seconds,
    }
