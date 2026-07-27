from __future__ import annotations

import asyncio
import logging
import time

from merge_data import save_records
from pipeline import AsyncIngestionPipeline


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    started_at = time.perf_counter()
    records, summary = asyncio.run(AsyncIngestionPipeline().run())
    save_records(records)
    elapsed_seconds = time.perf_counter() - started_at

    print("Data Saved Successfully")
    print(f"Cities Processed: {summary.cities_processed}")
    print(f"APIs Successful: {summary.api_successful}")
    print(f"APIs Failed: {summary.api_failed}")
    print(f"Rows Inserted: {summary.rows_inserted}")
    print(f"Execution Time: {elapsed_seconds:.2f}s")
    if summary.failed_requests:
        print("Failed Requests:")
        for item in summary.failed_requests:
            print(f"- {item['source']} | {item['city']} | {item['error']}")


if __name__ == "__main__":
    main()
