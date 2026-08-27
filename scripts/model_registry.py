from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from feature_pipeline.modeling.registry import CURRENT_MODEL_PATH, REGISTRY_PATH, list_models, get_current_model  # noqa: E402


def main() -> int:
    current_model = get_current_model()
    print(f"Registry file: {REGISTRY_PATH}")
    print(f"Current model file: {CURRENT_MODEL_PATH}")
    if not current_model:
        print("No registered model found.")
        return 0

    print(
        "Current approved model: "
        f"{current_model.get('model_name')} | version={current_model.get('version')} | "
        f"rmse={current_model.get('metrics', {}).get('rmse')} | "
        f"artifact={current_model.get('artifact_path')}"
    )
    print("\nRegistered models:")
    for entry in list_models():
        status = "approved" if entry.get("approved") else "candidate"
        metrics = entry.get("metrics", {})
        print(
            f"- {entry.get('model_name')} v{entry.get('version')} | {status} | "
            f"rmse={metrics.get('rmse')} | mae={metrics.get('mae')} | r2={metrics.get('r2')} | "
            f"run={entry.get('run_id')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
