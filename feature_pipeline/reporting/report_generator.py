from __future__ import annotations

import json
import os
from typing import Any

from config import settings


def build_report(
    *,
    run_id: str,
    execution_time_seconds: float,
    cities_processed: int,
    pipeline_version: str | None,
    api_summary: dict[str, dict[str, int]],
    missing_values: dict[str, int],
    silver_rows: int,
    gold_rows: int,
    failed_requests: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "pipeline_version": pipeline_version,
        "execution_time_seconds": execution_time_seconds,
        "cities_processed": cities_processed,
        "api_summary": api_summary,
        "rows_saved": gold_rows,
        "silver_rows": silver_rows,
        "missing_values": missing_values,
        "validation": {
            "passed": len(failed_requests) == 0,
            "failed_requests": failed_requests,
        },
    }


def write_report(report: dict[str, Any]) -> str:
    os.makedirs(settings.reports_dir, exist_ok=True)
    output_path = os.path.join(settings.reports_dir, f"{report['run_id']}.json")
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str, ensure_ascii=False)
    return output_path
