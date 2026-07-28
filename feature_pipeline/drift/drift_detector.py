from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging
import time

import pandas as pd

from config import settings
from drift.drift_report import build_drift_report, write_drift_report
from drift.statistics import compare_statistics, compute_statistics
from drift.thresholds import DriftThresholds, load_thresholds, threshold_for_feature

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DriftDetectionResult:
    run_id: str
    comparison_run_id: str | None
    execution_time: float
    drift_detected: bool
    report_path: str
    current_snapshot_path: str
    previous_snapshot_path: str | None
    warnings: list[str]
    features: dict[str, Any]


class DriftDetector:
    def __init__(
        self,
        gold_runs_dir: str | None = None,
        thresholds: DriftThresholds | None = None,
    ) -> None:
        self.gold_runs_dir = Path(gold_runs_dir or settings.gold_runs_dir)
        self.thresholds = thresholds or load_thresholds()

    def _load_frame(self, path: Path | None) -> pd.DataFrame:
        if path is None or not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def _find_previous_snapshot(self, current_run_id: str) -> Path | None:
        if not self.gold_runs_dir.exists():
            return None
        candidates = sorted(
            path for path in self.gold_runs_dir.glob("*.csv") if path.stem < current_run_id
        )
        return candidates[-1] if candidates else None

    def _snapshot_path(self, run_id: str) -> Path:
        return self.gold_runs_dir / f"{run_id}.csv"

    def _save_snapshot(self, current_gold: pd.DataFrame, run_id: str) -> str:
        self.gold_runs_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self._snapshot_path(run_id)
        current_gold.to_csv(snapshot_path, index=False)
        return str(snapshot_path)

    def _feature_threshold(self, feature_name: str) -> float:
        return threshold_for_feature(self.thresholds, feature_name)

    def _is_feature_drifted(self, comparison: dict[str, Any], threshold: float) -> bool:
        percentage_metrics = ("mean", "median", "minimum", "maximum", "standard_deviation")
        for metric_name in percentage_metrics:
            metric_value = comparison["percentage"].get(metric_name)
            if metric_value is not None and abs(metric_value) >= threshold:
                return True

        missing_percentage = comparison["difference"].get("missing_percentage")
        if missing_percentage is not None and abs(missing_percentage) >= self.thresholds.missing_percentage:
            return True

        record_count_percentage = comparison["percentage"].get("record_count")
        if record_count_percentage is not None and abs(record_count_percentage) >= self.thresholds.record_count:
            return True

        return False

    def detect(
        self,
        current_gold: pd.DataFrame,
        run_id: str,
        comparison_snapshot_path: str | None = None,
    ) -> DriftDetectionResult:
        started_at = time.perf_counter()
        logger.info("Drift Started | run_id=%s", run_id)

        previous_snapshot = (
            Path(comparison_snapshot_path)
            if comparison_snapshot_path
            else self._find_previous_snapshot(run_id)
        )
        comparison_run_id = previous_snapshot.stem if previous_snapshot else None
        previous_gold = self._load_frame(previous_snapshot)

        current_statistics = compute_statistics(current_gold)
        previous_statistics = compute_statistics(previous_gold) if not previous_gold.empty else {}

        warnings: list[str] = []
        if previous_snapshot is None:
            warnings.append("No previous gold dataset found for comparison.")
            logger.warning("No previous gold dataset found | run_id=%s", run_id)
        else:
            logger.info("Comparison Run ID=%s", comparison_run_id)

        features: dict[str, Any] = {}
        drift_detected = False
        for feature_name, current_stats in current_statistics.items():
            threshold = self._feature_threshold(feature_name)
            previous_stats = previous_statistics.get(feature_name)
            if previous_stats is None:
                features[feature_name] = {
                    "current": current_stats.as_dict(),
                    "previous": None,
                    "difference": None,
                    "percentage": None,
                    "threshold": threshold,
                    "drift_detected": False,
                }
                continue

            comparison = compare_statistics(current_stats, previous_stats)
            feature_drift = self._is_feature_drifted(comparison, threshold)
            comparison["threshold"] = threshold
            comparison["drift_detected"] = feature_drift
            features[feature_name] = comparison

            if feature_drift:
                drift_detected = True
                warning_message = (
                    f"{feature_name} drift exceeded threshold {threshold}% "
                    f"(current mean={current_stats.mean}, previous mean={previous_stats.mean})"
                )
                warnings.append(warning_message)
                logger.warning(warning_message)

        execution_time = time.perf_counter() - started_at
        current_row_count = int(len(current_gold))
        previous_row_count = int(len(previous_gold)) if not previous_gold.empty else None
        report = build_drift_report(
            run_id=run_id,
            comparison_run_id=comparison_run_id,
            execution_time=execution_time,
            drift_detected=drift_detected,
            current_row_count=current_row_count,
            previous_row_count=previous_row_count,
            thresholds=self.thresholds.as_dict(),
            features=features,
            warnings=warnings,
        )
        report_path = write_drift_report(report)
        current_snapshot_path = self._save_snapshot(current_gold, run_id)

        logger.info(
            "Drift Finished | run_id=%s | comparison=%s | execution_time=%.3fs | drift=%s",
            run_id,
            comparison_run_id,
            execution_time,
            drift_detected,
        )

        return DriftDetectionResult(
            run_id=run_id,
            comparison_run_id=comparison_run_id,
            execution_time=execution_time,
            drift_detected=drift_detected,
            report_path=report_path,
            current_snapshot_path=current_snapshot_path,
            previous_snapshot_path=str(previous_snapshot) if previous_snapshot else None,
            warnings=warnings,
            features=features,
        )
