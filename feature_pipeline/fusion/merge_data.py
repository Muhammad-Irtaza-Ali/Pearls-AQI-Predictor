from __future__ import annotations

from collections import defaultdict
from typing import Any

from validation.schema import AirQualityRecord


def merge_records(records: list[AirQualityRecord]) -> list[AirQualityRecord]:
    grouped: dict[str, list[AirQualityRecord]] = defaultdict(list)
    for record in records:
        grouped[record.city].append(record)

    merged_records: list[AirQualityRecord] = []
    for city_records in grouped.values():
        city_records = sorted(city_records, key=lambda item: item.retrieved_at)
        latest = city_records[-1]
        merged_payload = latest.model_dump()

        for field_name in AirQualityRecord.model_fields:
            if field_name in {"source", "status", "raw_payload", "retrieved_at"}:
                continue
            if merged_payload.get(field_name) is not None:
                continue
            for candidate in reversed(city_records):
                candidate_value = candidate.model_dump().get(field_name)
                if candidate_value is not None:
                    merged_payload[field_name] = candidate_value
                    break

        merged_payload["source"] = "merged"
        merged_payload["status"] = "merged"
        merged_payload["raw_payload"] = {
            "sources": [record.source for record in city_records],
            "source_records": [record.model_dump(mode="json") for record in city_records],
        }
        merged_records.append(AirQualityRecord.model_validate(merged_payload))

    return merged_records
