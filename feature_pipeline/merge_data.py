from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from config import STANDARD_COLUMNS, settings


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {column: record.get(column) for column in STANDARD_COLUMNS}
    if normalized.get("raw_payload") is not None:
        normalized["raw_payload"] = (
            normalized["raw_payload"]
            if isinstance(normalized["raw_payload"], str)
            else json.dumps(normalized["raw_payload"], default=str, ensure_ascii=False)
        )
    return normalized


def save_records(records: list[dict[str, Any]]) -> None:
    if not records:
        return

    os.makedirs(os.path.dirname(settings.output_path), exist_ok=True)
    normalized_records = [_normalize_record(record) for record in records]
    frame = pd.DataFrame(normalized_records, columns=STANDARD_COLUMNS)
    write_header = not os.path.exists(settings.output_path)
    frame.to_csv(settings.output_path, mode="a" if not write_header else "w", header=write_header, index=False)


def save_record(record: dict[str, Any]) -> None:
    save_records([record])
