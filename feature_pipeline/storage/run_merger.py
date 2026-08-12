from __future__ import annotations

import csv
from pathlib import Path
import sys
from collections.abc import Callable
from typing import Any


csv.field_size_limit(min(sys.maxsize, 2_147_483_647))


def _read_csv_rows(
    path: Path,
    row_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists() or path.stat().st_size == 0:
        return [], []

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [row_transform(dict(row)) if row_transform is not None else dict(row) for row in reader]
        if row_transform is not None:
            fieldnames = list(rows[0].keys()) if rows else []
        else:
            fieldnames = list(reader.fieldnames or [])
    return rows, fieldnames


def merge_run_snapshots(
    main_output_path: str | Path,
    *,
    row_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    include_existing_main: bool = False,
) -> Path:
    """
    Merge every run snapshot into the canonical CSV for a data layer.

    The layer layout is expected to be:
    - `data/bronze/raw_records.csv` + `data/bronze/runs/*.csv`
    - `data/silver/validated_records.csv` + `data/silver/runs/*.csv`
    - `data/gold/merged_records.csv` + `data/gold/runs/*.csv`
    """

    output_path = Path(main_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_dir = output_path.parent / "runs"
    row_buffer: list[dict[str, Any]] = []
    fieldnames: list[str] = []

    if include_existing_main and output_path.exists():
        main_rows, main_fields = _read_csv_rows(output_path, row_transform=row_transform)
        row_buffer.extend(main_rows)
        fieldnames.extend(main_fields)

    if run_dir.exists():
        for run_file in sorted(run_dir.glob("*.csv")):
            rows, run_fields = _read_csv_rows(run_file, row_transform=row_transform)
            row_buffer.extend(rows)
            fieldnames.extend(run_fields)

    unique_fieldnames = list(dict.fromkeys(fieldnames))
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=unique_fieldnames)
        writer.writeheader()
        for row in row_buffer:
            writer.writerow({field: row.get(field) for field in unique_fieldnames})
    return output_path
