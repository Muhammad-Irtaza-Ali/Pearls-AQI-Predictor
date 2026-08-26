from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class ModelSummary:
    name: str
    mae: float
    rmse: float
    r2: float
    fit_seconds: float


def _load_training_report(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Training report not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_summary(training_report: dict) -> dict:
    models = [
        ModelSummary(
            name=str(model["name"]),
            mae=float(model["mae"]),
            rmse=float(model["rmse"]),
            r2=float(model["r2"]),
            fit_seconds=float(model["fit_seconds"]),
        )
        for model in training_report.get("models", [])
    ]

    if not models:
        raise ValueError("No model metrics found in training report")

    best_model_name = str(training_report.get("best_model", models[0].name))
    best_model = next((model for model in models if model.name == best_model_name), models[0])
    ranked_models = sorted(models, key=lambda model: model.rmse)

    baseline = ranked_models[0]
    comparison = []
    for model in ranked_models:
        rmse_gap = model.rmse - baseline.rmse
        mae_gap = model.mae - baseline.mae
        r2_gap = baseline.r2 - model.r2
        comparison.append(
            {
                "name": model.name,
                "rmse": model.rmse,
                "mae": model.mae,
                "r2": model.r2,
                "fit_seconds": model.fit_seconds,
                "rmse_gap_vs_best": rmse_gap,
                "mae_gap_vs_best": mae_gap,
                "r2_gap_vs_best": r2_gap,
            }
        )

    return {
        "run_id": training_report.get("run_id"),
        "source": training_report.get("source"),
        "rows_total": training_report.get("rows_total"),
        "rows_train": training_report.get("rows_train"),
        "rows_test": training_report.get("rows_test"),
        "best_model": best_model.name,
        "best_rmse": best_model.rmse,
        "best_mae": best_model.mae,
        "best_r2": best_model.r2,
        "models_ranked_by_rmse": comparison,
        "dataset_path": training_report.get("dataset_path"),
    }


def _write_markdown(summary: dict, destination: Path) -> None:
    lines = [
        "# Model Evaluation Summary",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Data source: `{summary['source']}`",
        f"- Rows total: `{summary['rows_total']}`",
        f"- Rows train: `{summary['rows_train']}`",
        f"- Rows test: `{summary['rows_test']}`",
        f"- Best model: `{summary['best_model']}`",
        f"- Best RMSE: `{summary['best_rmse']:.4f}`",
        f"- Best MAE: `{summary['best_mae']:.4f}`",
        f"- Best R2: `{summary['best_r2']:.4f}`",
        "",
        "## Model Ranking",
        "",
    ]

    for item in summary["models_ranked_by_rmse"]:
        lines.extend(
            [
                f"- `{item['name']}` | rmse={item['rmse']:.4f} | mae={item['mae']:.4f} | r2={item['r2']:.4f} | fit={item['fit_seconds']:.2f}s",
            ]
        )

    destination.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a model evaluation summary from the latest training report.")
    parser.add_argument(
        "--training-report",
        default=str(Path("reports") / "model_training_report.json"),
        help="Path to the training report JSON.",
    )
    parser.add_argument(
        "--output-json",
        default=str(Path("reports") / "model_evaluation_summary.json"),
        help="Path for the evaluation summary JSON.",
    )
    parser.add_argument(
        "--output-md",
        default=str(Path("reports") / "model_evaluation_summary.md"),
        help="Path for the evaluation summary markdown.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    training_report = _load_training_report(Path(args.training_report))
    summary = _build_summary(training_report)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    _write_markdown(summary, output_md)

    print(f"Evaluation summary written to {output_json}")
    print(f"Markdown summary written to {output_md}")
    print(f"Best model: {summary['best_model']} (rmse={summary['best_rmse']:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
