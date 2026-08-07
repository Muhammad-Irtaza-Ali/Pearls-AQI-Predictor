from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.csv_writer import write_csv_records


def write_run_snapshot(base_dir: str | Path, run_id: str, records: list[dict[str, Any]]) -> Path:
    base_path = Path(base_dir)
    if base_path.suffix:
        base_path = base_path.parent
    output_path = base_path / "runs" / f"{run_id}.csv"
    return write_csv_records(output_path, records)
