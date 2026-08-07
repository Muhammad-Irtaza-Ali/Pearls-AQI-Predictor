from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import settings
from drift.drift_report import write_drift_report
from drift.statistics import compute_column_statistics
from drift.thresholds import DEFAULT_THRESHOLDS


class DriftDetector:
    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def detect(self, current_gold: list[dict[str, Any]], previous_gold: list[dict[str, Any]] | None = None, *, run_id: str | None = None, comparison_run_id: str | None = None) -> dict[str, Any]:
        current_df = pd.DataFrame(current_gold)
        previous_df = pd.DataFrame(previous_gold or [])
        features = {}
        drift_detected = False
        for feature, threshold in self.thresholds.items():
            if feature not in current_df.columns or feature not in previous_df.columns:
                continue
            stats = compute_column_statistics(current_df[feature], previous_df[feature])
            current_mean = stats["current_mean"]
            previous_mean = stats["previous_mean"]
            difference = None if pd.isna(current_mean) or pd.isna(previous_mean) else current_mean - previous_mean
            percentage = None
            if previous_mean not in (None, 0) and difference is not None:
                percentage = abs(difference) / abs(previous_mean) * 100
                if percentage >= threshold:
                    drift_detected = True
            features[feature] = {**stats, "difference": difference, "percentage": percentage, "threshold": threshold}
        payload = {
            "run_id": run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "comparison": comparison_run_id,
            "execution_time": 0.0,
            "drift_detected": drift_detected,
            "features": features,
        }
        write_drift_report(Path(settings.drift_reports_dir) / f"{payload['run_id']}.json", payload)
        return payload

