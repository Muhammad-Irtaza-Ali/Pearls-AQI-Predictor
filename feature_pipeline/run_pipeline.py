from __future__ import annotations

import asyncio
import logging
import time

import pandas as pd

from config import PIPELINE_VERSION, settings
from drift.drift_detector import DriftDetector
from monitoring.logger import configure_logging
from pipeline import AsyncIngestionPipeline
from reporting.report_generator import build_report, write_report
from storage.csv_writer import CSVWriter


def main() -> None:
    configure_logging(logging.INFO)
    started_at = time.perf_counter()
    artifacts = asyncio.run(AsyncIngestionPipeline().run())

    bronze_writer = CSVWriter(settings.bronze_output_path)
    silver_writer = CSVWriter(settings.silver_output_path)
    gold_writer = CSVWriter(settings.gold_output_path)

    bronze_writer.write(artifacts.bronze_records)
    silver_writer.write(artifacts.silver_records)
    gold_writer.write(artifacts.gold_records)

    gold_frame = pd.DataFrame(artifacts.gold_records)
    drift_result = DriftDetector().detect(gold_frame, artifacts.summary.run_id)

    report = build_report(
        run_id=artifacts.summary.run_id,
        execution_time_seconds=artifacts.summary.execution_time_seconds,
        cities_processed=artifacts.summary.cities_processed,
        pipeline_version=PIPELINE_VERSION,
        api_summary=artifacts.summary.api_summary,
        missing_values=artifacts.summary.missing_values,
        silver_rows=artifacts.summary.silver_rows,
        gold_rows=artifacts.summary.gold_rows,
        failed_requests=artifacts.summary.failed_requests,
    )
    report_path = write_report(report)

    elapsed_seconds = time.perf_counter() - started_at

    print("Data Saved Successfully")
    print(f"Run ID: {artifacts.summary.run_id}")
    print(f"Cities Processed: {artifacts.summary.cities_processed}")
    print(f"APIs Successful: {artifacts.summary.api_successful}")
    print(f"APIs Failed: {artifacts.summary.api_failed}")
    print(f"Silver Rows: {artifacts.summary.silver_rows}")
    print(f"Gold Rows: {artifacts.summary.gold_rows}")
    print(f"Execution Time: {elapsed_seconds:.2f}s")
    print(f"Report Saved: {report_path}")
    print(f"Drift Report Saved: {drift_result.report_path}")
    print(f"Drift Detected: {'YES' if drift_result.drift_detected else 'NO'}")
    print(f"Validation: {'PASS' if not artifacts.summary.failed_requests else 'FAIL'}")
    if artifacts.summary.failed_requests:
        print("Failed Requests:")
        for item in artifacts.summary.failed_requests:
            print(f"- {item['source']} | {item['city']} | {item['error']}")
    if drift_result.warnings:
        print("Drift Warnings:")
        for warning in drift_result.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
