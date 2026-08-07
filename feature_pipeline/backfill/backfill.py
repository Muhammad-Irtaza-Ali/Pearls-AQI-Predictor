from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date
from pathlib import Path
import sys
import time

CURRENT_DIR = Path(__file__).resolve().parent
FEATURE_PIPELINE_DIR = CURRENT_DIR.parent
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))

from monitoring.logger import configure_logging  # noqa: E402
from pipeline import AsyncIngestionPipeline  # noqa: E402
from reporting.output_writer import publish_outputs  # noqa: E402


def _parse_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed < date(2023, 1, 1):
        raise argparse.ArgumentTypeError("Backfill dates must be on or after 2023-01-01.")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AQI historical backfill from 2023 onwards.")
    parser.add_argument("--start-date", type=_parse_date, required=True, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", type=_parse_date, default=date.today(), help="End date in YYYY-MM-DD format. Defaults to today.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(logging.INFO)
    logger = logging.getLogger("backfill")
    logger.info("Backfill Started | start_date=%s | end_date=%s", args.start_date, args.end_date)

    started_at = time.perf_counter()
    artifacts = asyncio.run(AsyncIngestionPipeline().run(start_date=args.start_date, end_date=args.end_date))
    outputs = publish_outputs(
        run_id=artifacts.summary.run_id,
        bronze_records=artifacts.bronze_records,
        silver_records=artifacts.silver_records,
        gold_records=artifacts.gold_records,
        summary=artifacts.summary,
        drift_result=None,
    )
    elapsed_seconds = time.perf_counter() - started_at

    logger.info("Backfill Finished | run_id=%s | execution_time=%.2fs | calls=%s | failed=%s", artifacts.summary.run_id, elapsed_seconds, artifacts.summary.total_api_calls, artifacts.summary.failed_calls)
    print("Historical Backfill Completed")
    print(f"Run ID: {artifacts.summary.run_id}")
    print(f"Execution Time: {elapsed_seconds:.2f}s")
    print(f"Report Saved: {outputs.report_path}")
    print(f"Metrics Saved: {outputs.metrics_path}")
    print(f"Quality Saved: {outputs.quality_path}")
    print(f"Bronze Snapshot: {outputs.bronze_snapshot_path}")
    print(f"Silver Snapshot: {outputs.silver_snapshot_path}")
    print(f"Gold Snapshot: {outputs.gold_snapshot_path}")
    print(f"APIs Successful: {artifacts.summary.successful_calls}")
    print(f"APIs Failed: {artifacts.summary.failed_calls}")
    return 0 if artifacts.summary.failed_calls == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

