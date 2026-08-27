from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from feature_pipeline.modeling.trainer import train_three_models, write_training_summary  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train three AQI regression models.")
    parser.add_argument(
        "--source",
        choices=["auto", "hopsworks", "local"],
        default="auto",
        help="Data source to train from. Auto prefers Hopsworks when available.",
    )
    parser.add_argument(
        "--local-path",
        default=str(ROOT_DIR / "data" / "gold" / "ml_ready_records.csv"),
        help="Fallback local ML-ready CSV path.",
    )
    parser.add_argument(
        "--feature-group",
        default=None,
        help="Hopsworks feature group name. Defaults to HOPSWORKS_ML_FEATURE_GROUP.",
    )
    parser.add_argument(
        "--feature-group-version",
        type=int,
        default=None,
        help="Hopsworks feature group version. Defaults to HOPSWORKS_ML_FEATURE_GROUP_VERSION.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to store model artifacts. Defaults to models/<run_id>.",
    )
    parser.add_argument(
        "--report-path",
        default=str(ROOT_DIR / "reports" / "model_training_report.json"),
        help="Path for the training summary JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    report, results = train_three_models(
        source=args.source,
        local_path=args.local_path,
        feature_group=args.feature_group,
        feature_group_version=args.feature_group_version,
        output_dir=args.output_dir,
    )
    report_path = write_training_summary(report, args.report_path)

    print(f"Training source: {report.source}")
    print(f"Rows total: {report.rows_total}")
    print(f"Best model: {report.best_model} ({report.best_metric}={report.best_metric_value:.4f})")
    print(f"Report: {report_path}")
    for result in results:
        print(
            f"- {result.name}: rmse={result.rmse:.4f}, mae={result.mae:.4f}, r2={result.r2:.4f}, artifact={result.artifact_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
