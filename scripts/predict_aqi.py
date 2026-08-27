from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from feature_pipeline.modeling.predictor import predict_dataframe, predict_single  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict AQI using the best trained model.")
    parser.add_argument("--model-dir", default=str(ROOT_DIR / "models" / "latest"), help="Directory with model artifacts.")
    parser.add_argument("--input-csv", default=None, help="CSV file with prediction rows.")
    parser.add_argument("--input-json", default=None, help="JSON file with one prediction record.")
    parser.add_argument("--output-csv", default=None, help="Optional output CSV path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if bool(args.input_csv) == bool(args.input_json):
        raise SystemExit("Provide exactly one of --input-csv or --input-json")

    if args.input_csv:
        dataframe = pd.read_csv(args.input_csv)
        predictions = predict_dataframe(dataframe, model_dir=args.model_dir)
        if args.output_csv:
            output_path = Path(args.output_csv)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            predictions.to_csv(output_path, index=False)
            print(f"Predictions written to {output_path}")
        else:
            print(predictions.to_json(orient="records", indent=2, date_format="iso"))
        return 0

    record = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    result = predict_single(record, model_dir=args.model_dir)
    print(json.dumps(asdict(result), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
