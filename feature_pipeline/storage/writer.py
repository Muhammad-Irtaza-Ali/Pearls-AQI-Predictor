from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.csv_writer import write_csv_records


def write_records(path: str | Path, records: list[dict[str, Any]]) -> Path:
    return write_csv_records(path, records)

