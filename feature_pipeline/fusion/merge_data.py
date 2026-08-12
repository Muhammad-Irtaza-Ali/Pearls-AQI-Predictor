from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from validation.schema import AirQualityRecord
from fusion.model_ready import project_model_ready_record


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
        payload = project_model_ready_record(chosen, source="merged", status="merged")
        payload["data_date"] = record_date
        payload["source"] = "merged"
        payload["status"] = "merged"
        merged.append(AirQualityRecord.model_validate(payload))
    return merged
