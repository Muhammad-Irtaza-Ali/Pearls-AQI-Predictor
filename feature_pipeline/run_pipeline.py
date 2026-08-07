from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from drift.drift_detector import DriftDetector  # noqa: E402
from monitoring.logger import configure_logging  # noqa: E402
from pipeline import AsyncIngestionPipeline  # noqa: E402
from reporting.output_writer import publish_outputs  # noqa: E402


def main() -> int:
    configure_logging(logging.INFO)
    artifacts = asyncio.run(AsyncIngestionPipeline().run())
    publish_outputs(
        run_id=artifacts.summary.run_id,
        bronze_records=artifacts.bronze_records,
        silver_records=artifacts.silver_records,
        gold_records=artifacts.gold_records,
        summary=artifacts.summary,
        drift_result=DriftDetector().detect(artifacts.gold_records, run_id=artifacts.summary.run_id),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

