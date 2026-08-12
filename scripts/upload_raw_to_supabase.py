from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
FEATURE_PIPELINE_DIR = ROOT_DIR / "feature_pipeline"
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))

from storage.supabase_writer import write_raw_records  # noqa: E402


def main() -> int:
    raw_path = ROOT_DIR / "data" / "bronze" / "raw_records.csv"
    report_path = ROOT_DIR / "reports" / "raw_supabase_upload_report.json"

    if not raw_path.exists():
        print(f"Raw dataset not found: {raw_path}")
        return 2

    dataframe = pd.read_csv(raw_path, low_memory=False)
    records = dataframe.to_dict(orient="records")
    if not records:
        print("No raw records found to upload.")
        return 0

    result = write_raw_records(records)
    report = {
        "raw_dataset_path": str(raw_path),
        "rows": len(records),
        "supabase": {
            "inserted_rows": result.inserted_rows,
            "skipped": result.skipped,
            "message": result.message,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Uploaded raw dataset from {raw_path} to Supabase")
    print(f"Rows: {len(records)}")
    print(f"Supabase: inserted={result.inserted_rows}, skipped={result.skipped}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
