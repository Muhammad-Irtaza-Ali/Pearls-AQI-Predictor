from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
FEATURE_PIPELINE_DIR = ROOT_DIR / "feature_pipeline"
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))

from storage.run_merger import merge_run_snapshots  # noqa: E402
from fusion.model_ready import project_model_ready_record  # noqa: E402


def main() -> int:
    bronze_path = merge_run_snapshots(ROOT_DIR / "data" / "bronze" / "raw_records.csv")
    silver_path = merge_run_snapshots(ROOT_DIR / "data" / "silver" / "validated_records.csv")
    gold_path = merge_run_snapshots(ROOT_DIR / "data" / "gold" / "merged_records.csv", row_transform=project_model_ready_record)
    print(f"Merged bronze -> {bronze_path}")
    print(f"Merged silver -> {silver_path}")
    print(f"Merged gold -> {gold_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
