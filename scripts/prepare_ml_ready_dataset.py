from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
FEATURE_PIPELINE_DIR = ROOT_DIR / "feature_pipeline"
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))

from preparation.ml_ready_dataset import build_ml_ready_dataset, quality_report  # noqa: E402


def main() -> int:
    silver_path = ROOT_DIR / "data" / "silver" / "validated_records.csv"
    bronze_path = ROOT_DIR / "data" / "bronze" / "raw_records.csv"
    output_path = ROOT_DIR / "data" / "gold" / "ml_ready_records.csv"
    report_path = ROOT_DIR / "reports" / "data_quality_report.json"

    dataset, summary = build_ml_ready_dataset(silver_path, bronze_path=bronze_path, output_path=output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(quality_report(summary), indent=2, default=str), encoding="utf-8")

    print(f"ML-ready dataset written to {output_path}")
    print(f"Rows: {len(dataset)}")
    print(f"Quality report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
