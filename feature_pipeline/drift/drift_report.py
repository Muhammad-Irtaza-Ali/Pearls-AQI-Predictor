from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from typing import Any

from config import settings


def build_drift_report(
    *,
    run_id: str,
    comparison_run_id: str | None,
    execution_time: float,
    drift_detected: bool,
    current_row_count: int,
    previous_row_count: int | None,
    thresholds: dict[str, float],
    features: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "comparison": comparison_run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_time": execution_time,
        "drift_detected": drift_detected,
        "current_row_count": current_row_count,
        "previous_row_count": previous_row_count,
        "thresholds": thresholds,
        "warnings": warnings,
        "features": features,
    }


def write_drift_report(report: dict[str, Any]) -> str:
    os.makedirs(settings.drift_reports_dir, exist_ok=True)
    output_path = os.path.join(settings.drift_reports_dir, f"{report['run_id']}.json")
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str, ensure_ascii=False)
    return output_path
