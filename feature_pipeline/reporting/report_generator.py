from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_pipeline_report(summary: Any, drift_result: Any | None = None) -> dict[str, Any]:
    payload = {
        "run_id": summary.run_id,
        "cities_processed": summary.cities_processed,
        "total_api_calls": summary.total_api_calls,
        "successful_calls": summary.successful_calls,
        "failed_calls": summary.failed_calls,
        "rows_processed": summary.rows_processed,
        "rows_skipped": summary.rows_skipped,
        "invalid_records": summary.invalid_records,
        "duplicates_removed": summary.duplicates_removed,
        "silver_rows": summary.silver_rows,
        "gold_rows": summary.gold_rows,
        "execution_time_seconds": summary.execution_time_seconds,
        "failed_requests": summary.failed_requests,
        "api_summary": summary.api_summary,
        "missing_values": summary.missing_values,
    }
    if drift_result is not None:
        payload["drift"] = drift_result
    return payload


def write_pipeline_report(path: str | Path, summary: Any, drift_result: Any | None = None) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_pipeline_report(summary, drift_result), indent=2, default=str), encoding="utf-8")
    return output_path

