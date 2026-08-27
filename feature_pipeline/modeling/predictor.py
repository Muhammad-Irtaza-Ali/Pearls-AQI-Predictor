from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .registry import resolve_registered_model


TRAINING_FEATURE_COLUMNS = [
    "latitude",
    "longitude",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "rain",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
    "month",
    "day_of_week",
    "hour",
    "day_of_year",
    "city",
]


@dataclass(slots=True)
class PredictionResult:
    model_name: str
    prediction: float
    input_row: dict[str, Any]


def load_best_model(model_dir: str | Path = Path("models") / "latest") -> tuple[str, Any]:
    return load_model(model_dir=model_dir)


def _load_from_manifest(
    *,
    model_name: str | None,
    model_dir: str | Path,
) -> tuple[str, Any]:
    base_dir = Path(model_dir)
    manifest_path = base_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Model manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_model_name = str(model_name or manifest["best_model"])
    artifacts = manifest.get("artifacts", {})
    if selected_model_name not in artifacts:
        available_models = ", ".join(sorted(map(str, artifacts.keys()))) or "none"
        raise KeyError(
            f"Model '{selected_model_name}' is not available in the manifest. "
            f"Available models: {available_models}"
        )

    artifact_path = Path(artifacts[selected_model_name])
    if not artifact_path.is_absolute():
        artifact_path = (base_dir / artifact_path.name).resolve()
    if not artifact_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

    model = joblib.load(artifact_path)
    return selected_model_name, model


def load_model(
    model_name: str | None = None,
    *,
    model_dir: str | Path = Path("models") / "latest",
) -> tuple[str, Any]:
    registered_model = resolve_registered_model(model_name)
    if registered_model:
        artifact_path = Path(str(registered_model.get("artifact_path", "")))
        if artifact_path.exists():
            return str(registered_model.get("model_name")), joblib.load(artifact_path)

    return _load_from_manifest(model_name=model_name, model_dir=model_dir)


def _coerce_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        frame["month"] = frame["timestamp"].dt.month
        frame["day_of_week"] = frame["timestamp"].dt.dayofweek
        frame["hour"] = frame["timestamp"].dt.hour
        frame["day_of_year"] = frame["timestamp"].dt.dayofyear

    for column in TRAINING_FEATURE_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA

    frame["city"] = frame["city"].astype("string")
    numeric_columns = [column for column in TRAINING_FEATURE_COLUMNS if column != "city"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame[TRAINING_FEATURE_COLUMNS]


def predict_dataframe(
    dataframe: pd.DataFrame,
    *,
    model_name: str | None = None,
    model_dir: str | Path = Path("models") / "latest",
) -> pd.DataFrame:
    model_name, model = load_model(model_name=model_name, model_dir=model_dir)
    features = _coerce_frame(dataframe)
    predictions = model.predict(features)
    result = dataframe.copy()
    result["predicted_aqi"] = predictions
    result["best_model"] = model_name
    return result


def predict_single(
    record: dict[str, Any],
    *,
    model_name: str | None = None,
    model_dir: str | Path = Path("models") / "latest",
) -> PredictionResult:
    dataframe = pd.DataFrame([record])
    result = predict_dataframe(dataframe, model_name=model_name, model_dir=model_dir).iloc[0]
    model_name = str(result["best_model"])
    return PredictionResult(
        model_name=model_name,
        prediction=float(result["predicted_aqi"]),
        input_row=record,
    )
