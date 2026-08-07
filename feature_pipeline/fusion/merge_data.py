from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from validation.schema import AirQualityRecord


def _record_date(record: AirQualityRecord) -> date:
    if record.data_date is not None:
        return record.data_date
    return record.timestamp.date()


def merge_records(records: list[AirQualityRecord]) -> list[AirQualityRecord]:
    grouped: dict[tuple[str, date], list[AirQualityRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.city, _record_date(record))].append(record)

    merged: list[AirQualityRecord] = []
    for (city, record_date), group in grouped.items():
        chosen = group[0]
        payload = chosen.model_dump()
        payload["source"] = "merged"
        payload["endpoint"] = "merged"
        payload["status"] = "merged"
        payload["data_date"] = record_date
        payload["lineage"] = {
            "source_api": "merged",
            "city": city,
            "data_date": record_date.isoformat(),
            "source_apis": [item.source for item in group],
            "source_endpoints": [item.endpoint for item in group],
            "source_records": [item.model_dump(mode="json") for item in group],
        }
        merged.append(AirQualityRecord.model_validate(payload))
    return merged

