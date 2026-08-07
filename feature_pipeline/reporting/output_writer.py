from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import settings
from reporting.metrics_report import write_metrics_report
from reporting.quality_report import write_quality_report
from reporting.report_generator import write_pipeline_report
from storage.hopsworks_writer import write_feature_group
from storage.supabase_writer import write_raw_records
from storage.snapshots import write_run_snapshot
from storage.writer import write_records


@dataclass(slots=True)
class OutputPaths:
    report_path: Path
    metrics_path: Path
    quality_path: Path
    bronze_snapshot_path: Path
    silver_snapshot_path: Path
    gold_snapshot_path: Path


def publish_outputs(
    *,
    run_id: str,
    bronze_records: list[dict[str, Any]],
    silver_records: list[dict[str, Any]],
    gold_records: list[dict[str, Any]],
    summary: Any,
    drift_result: Any | None = None,
) -> OutputPaths:
    report_path = write_pipeline_report(Path(settings.reports_dir) / f"{run_id}.json", summary, drift_result)
    metrics_path = write_metrics_report(Path(settings.reports_dir) / f"{run_id}_metrics.json", summary)
    quality_path = write_quality_report(Path(settings.reports_dir) / f"{run_id}_quality.json", summary)
    bronze_snapshot_path = write_run_snapshot(settings.bronze_output_path, run_id, bronze_records)
    silver_snapshot_path = write_run_snapshot(settings.silver_output_path, run_id, silver_records)
    gold_snapshot_path = write_run_snapshot(settings.gold_output_path, run_id, gold_records)
    write_records(settings.output_path, bronze_records)
    write_raw_records(bronze_records, run_id)
    write_feature_group(gold_records, run_id)
    return OutputPaths(
        report_path=report_path,
        metrics_path=metrics_path,
        quality_path=quality_path,
        bronze_snapshot_path=bronze_snapshot_path,
        silver_snapshot_path=silver_snapshot_path,
        gold_snapshot_path=gold_snapshot_path,
    )
