from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import settings
from .data_loader import TrainingDataSource, load_training_dataframe
from .hopsworks_model import publish_model
from .registry import register_training_run

logger = logging.getLogger("model_trainer")


FEATURE_COLUMNS = [
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

NUMERIC_FEATURES = [column for column in FEATURE_COLUMNS if column != "city"]
CATEGORICAL_FEATURES = ["city"]
TARGET_COLUMN = "aqi"


@dataclass(slots=True)
class TrainedModelResult:
    name: str
    artifact_path: str
    mae: float
    rmse: float
    r2: float
    fit_seconds: float


@dataclass(slots=True)
class TrainingReport:
    run_id: str
    started_at: str
    finished_at: str
    source: str
    feature_group: str | None
    feature_group_version: int | None
    rows_total: int
    rows_train: int
    rows_test: int
    target_column: str
    feature_columns: list[str]
    dropped_columns: list[str]
    models: list[TrainedModelResult]
    best_model: str
    best_metric: str
    best_metric_value: float
    dataset_path: str | None = None


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def _make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _prepare_training_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()

    if "timestamp" not in frame.columns or TARGET_COLUMN not in frame.columns:
        raise ValueError("Training data must include 'timestamp' and 'aqi'")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame["data_date"] = pd.to_datetime(frame["data_date"], errors="coerce")
    frame[TARGET_COLUMN] = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")

    frame = frame.dropna(subset=["timestamp", TARGET_COLUMN, "city"]).copy()
    frame = frame[frame[TARGET_COLUMN].between(0, 500, inclusive="both")].copy()

    frame["month"] = frame["timestamp"].dt.month
    frame["day_of_week"] = frame["timestamp"].dt.dayofweek
    frame["hour"] = frame["timestamp"].dt.hour
    frame["day_of_year"] = frame["timestamp"].dt.dayofyear

    for column in NUMERIC_FEATURES:
        if column not in frame.columns:
            frame[column] = np.nan

    frame = frame.sort_values("timestamp").reset_index(drop=True)
    return frame


def _build_model_pipeline(model: Any) -> Pipeline:
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return Pipeline(steps=[("preprocess", preprocessing), ("model", model)])


def _time_split(frame: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(frame) < 5:
        raise ValueError("Not enough rows to train models")
    split_index = max(int(len(frame) * (1.0 - test_fraction)), 1)
    split_index = min(split_index, len(frame) - 1)
    train_frame = frame.iloc[:split_index].copy()
    test_frame = frame.iloc[split_index:].copy()
    return train_frame, test_frame


def _evaluate_predictions(y_true: pd.Series, predictions: np.ndarray) -> dict[str, float]:
    mse = float(mean_squared_error(y_true, predictions))
    return {
        "mae": float(mean_absolute_error(y_true, predictions)),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true, predictions)),
    }


def train_three_models(
    *,
    source: str = "auto",
    local_path: str | Path | None = None,
    feature_group: str | None = None,
    feature_group_version: int | None = None,
    output_dir: str | Path | None = None,
) -> tuple[TrainingReport, list[TrainedModelResult]]:
    started_at = datetime.now(timezone.utc)
    run_id = _make_run_id()
    destination_dir = Path(output_dir or Path("models") / run_id)
    destination_dir.mkdir(parents=True, exist_ok=True)

    data_source: TrainingDataSource = load_training_dataframe(
        source=source,
        local_path=local_path,
        feature_group=feature_group,
        feature_group_version=feature_group_version,
    )

    frame = _prepare_training_frame(data_source.dataframe)
    train_frame, test_frame = _time_split(frame)

    feature_columns = [column for column in FEATURE_COLUMNS if column in frame.columns]
    dropped_columns = [column for column in frame.columns if column not in feature_columns and column != TARGET_COLUMN]

    X_train = train_frame[feature_columns]
    y_train = train_frame[TARGET_COLUMN]
    X_test = test_frame[feature_columns]
    y_test = test_frame[TARGET_COLUMN]

    model_specs: list[tuple[str, Any]] = [
        ("ridge", Ridge(alpha=1.0)),
        ("random_forest", RandomForestRegressor(n_estimators=250, random_state=42, n_jobs=-1)),
        ("gradient_boosting", GradientBoostingRegressor(random_state=42)),
    ]

    results: list[TrainedModelResult] = []
    best_model_name = ""
    best_metric_value = float("inf")

    for model_name, model in model_specs:
        pipeline = _build_model_pipeline(model)
        logger.info("Training %s on %s rows", model_name, len(train_frame))

        fit_started = datetime.now(timezone.utc)
        pipeline.fit(X_train, y_train)
        fit_seconds = (datetime.now(timezone.utc) - fit_started).total_seconds()

        predictions = pipeline.predict(X_test)
        metrics = _evaluate_predictions(y_test, predictions)

        artifact_path = destination_dir / f"{model_name}.joblib"
        with artifact_path.open("wb") as file_handle:
            pickle.dump(pipeline, file_handle)

        result = TrainedModelResult(
            name=model_name,
            artifact_path=str(artifact_path),
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            r2=metrics["r2"],
            fit_seconds=float(fit_seconds),
        )
        results.append(result)
        logger.info(
            "Finished %s | rmse=%.4f | mae=%.4f | r2=%.4f | fit=%.2fs",
            model_name,
            result.rmse,
            result.mae,
            result.r2,
            result.fit_seconds,
        )

        if result.rmse < best_metric_value:
            best_metric_value = result.rmse
            best_model_name = model_name

    finished_at = datetime.now(timezone.utc)
    report = TrainingReport(
        run_id=run_id,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        source=data_source.source,
        feature_group=data_source.feature_group,
        feature_group_version=data_source.feature_group_version,
        rows_total=int(len(frame)),
        rows_train=int(len(train_frame)),
        rows_test=int(len(test_frame)),
        target_column=TARGET_COLUMN,
        feature_columns=feature_columns,
        dropped_columns=dropped_columns,
        models=results,
        best_model=best_model_name,
        best_metric="rmse",
        best_metric_value=float(best_metric_value),
        dataset_path=str(data_source.local_path) if data_source.local_path else None,
    )

    report_path = destination_dir / "training_report.json"
    report_path.write_text(json.dumps(asdict(report), indent=2, default=str), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "best_model": best_model_name,
        "best_metric": "rmse",
        "best_metric_value": best_metric_value,
        "artifacts": {result.name: result.artifact_path for result in results},
    }
    manifest_path = destination_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    register_training_run(report, results, manifest_path=manifest_path)

    best_result = next(result for result in results if result.name == best_model_name)
    publish_model(
        best_result.artifact_path,
        model_name=settings.hopsworks_model_name,
        metrics={"mae": best_result.mae, "rmse": best_result.rmse, "r2": best_result.r2},
    )

    logger.info("Training complete | best_model=%s | rmse=%.4f", best_model_name, best_metric_value)
    logger.info("Artifacts saved to %s", destination_dir)

    return report, results


def write_training_summary(report: TrainingReport, destination: str | Path | None = None) -> Path:
    output_path = Path(destination or Path("reports") / "model_training_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(report), indent=2, default=str), encoding="utf-8")
    return output_path
