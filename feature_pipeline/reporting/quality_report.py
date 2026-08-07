from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_quality_report(summary: Any) -> dict[str, Any]:
    return {
        "run_id": summary.run_id,
        "missing_values": summary.missing_values,
        "api_summary": summary.api_summary,
        "failed_requests": summary.failed_requests,
    }


def write_quality_report(path: str | Path, summary: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_quality_report(summary), indent=2, default=str), encoding="utf-8")
    return output_path

