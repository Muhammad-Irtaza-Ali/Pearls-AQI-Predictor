from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_metrics_report(summary: Any) -> dict[str, Any]:
    return {
        "run_id": summary.run_id,
        "total_api_calls": summary.total_api_calls,
        "successful_calls": summary.successful_calls,
        "failed_calls": summary.failed_calls,
        "rows_processed": summary.rows_processed,
        "rows_skipped": summary.rows_skipped,
        "invalid_records": summary.invalid_records,
        "duplicates_removed": summary.duplicates_removed,
        "execution_time_seconds": summary.execution_time_seconds,
    }


def write_metrics_report(path: str | Path, summary: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_metrics_report(summary), indent=2, default=str), encoding="utf-8")
    return output_path

