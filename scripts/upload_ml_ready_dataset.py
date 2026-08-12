from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
FEATURE_PIPELINE_DIR = ROOT_DIR / "feature_pipeline"
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))

from storage.hopsworks_writer import write_ml_ready_feature_group  # noqa: E402
from storage.supabase_writer import write_raw_records  # noqa: E402


def main() -> int:
    raw_path = ROOT_DIR / "data" / "bronze" / "raw_records.csv"
    dataset_path = ROOT_DIR / "data" / "gold" / "ml_ready_records.csv"
    report_path = ROOT_DIR / "reports" / "ml_ready_upload_report.json"

    if not raw_path.exists():
        print(f"Raw dataset not found: {raw_path}")
        return 2

    if not dataset_path.exists():
        print(f"ML-ready dataset not found: {dataset_path}")
        return 2

    raw_dataframe = pd.read_csv(raw_path, low_memory=False)
    raw_records = raw_dataframe.to_dict(orient="records")
    if not raw_records:
        print("No raw records found to upload.")
        return 0

    ml_dataframe = pd.read_csv(dataset_path, low_memory=False)
    ml_records = ml_dataframe.to_dict(orient="records")
    if not ml_records:
        print("No ML-ready records found to upload.")
        return 0

    supabase_result = write_raw_records(raw_records)
    hopsworks_result = write_ml_ready_feature_group(ml_records)

    report = {
        "raw_dataset_path": str(raw_path),
        "ml_ready_dataset_path": str(dataset_path),
        "raw_rows": len(raw_records),
        "ml_ready_rows": len(ml_records),
        "supabase": {
            "inserted_rows": supabase_result.inserted_rows,
            "skipped": supabase_result.skipped,
            "message": supabase_result.message,
        },
        "hopsworks": {
            "uploaded": hopsworks_result,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Uploaded raw dataset from {raw_path} to Supabase")
    print(f"Uploaded ML-ready dataset from {dataset_path} to Hopsworks")
    print(f"Raw rows: {len(raw_records)}")
    print(f"ML-ready rows: {len(ml_records)}")
    print(f"Supabase: inserted={supabase_result.inserted_rows}, skipped={supabase_result.skipped}")
    print(f"Hopsworks: uploaded={hopsworks_result}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
