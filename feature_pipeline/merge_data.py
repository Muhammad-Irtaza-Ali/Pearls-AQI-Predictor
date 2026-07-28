from __future__ import annotations

from typing import Any

from config import settings
from storage.csv_writer import CSVWriter


def save_records(records: list[dict[str, Any]]) -> None:
    CSVWriter(settings.silver_output_path).write(records)


def save_record(record: dict[str, Any]) -> None:
    save_records([record])

