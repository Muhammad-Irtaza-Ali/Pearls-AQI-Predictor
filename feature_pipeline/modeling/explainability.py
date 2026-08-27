from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from modeling.predictor import TRAINING_FEATURE_COLUMNS, _coerce_frame, load_model

logger = logging.getLogger("model_explainability")

try:
    import shap  # type: ignore

    SHAP_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    shap = None  # type: ignore[assignment]
    SHAP_AVAILABLE = False

GROUP_FEATURES = {"city": "city"}

BOUNDED_RANGES = {
    "humidity": (0.0, 100.0),
    "cloud_cover": (0.0, 100.0),
    "wind_direction": (0.0, 360.0),
    "month": (1.0, 12.0),
    "day_of_week": (0.0, 6.0),
    "hour": (0.0, 23.0),
    "day_of_year": (1.0, 366.0),
    "rain": (0.0, None),
    "pm25": (0.0, None),
    "pm10": (0.0, None),
    "co": (0.0, None),
    "no": (0.0, None),
    "no2": (0.0, None),
    "so2": (0.0, None),
    "o3": (0.0, None),
    "nh3": (0.0, None),
}


@dataclass(slots=True)
class LocalContribution:
    feature: str
    transformed_feature: str
    value: float
    baseline: float
    contribution: float


@dataclass(slots=True)
class GlobalImportance:
    feature: str
    importance: float


@dataclass(slots=True)
class ExplanationResult:
    model_name: str
    method: str
    prediction: float
    baseline_prediction: float
    local_contributions: list[LocalContribution]
    global_importance: list[GlobalImportance]
    notes: list[str]


def _group_name(feature_name: str) -> str:
    if feature_name.startswith("city_"):
        return "city"
    return GROUP_FEATURES.get(feature_name, feature_name)


def _reference_frame(reference_frame: pd.DataFrame | None) -> pd.DataFrame:
    if reference_frame is None or reference_frame.empty:
        return pd.DataFrame()
    frame = reference_frame.copy()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    return frame


def _numeric_reference_stats(frame: pd.DataFrame) -> dict[str, float]:
    stats: dict[str, float] = {}
    if frame.empty:
        return stats
    for column in TRAINING_FEATURE_COLUMNS:
        if column == "city":
            continue
        if column in frame.columns:
            series = pd.to_numeric(frame[column], errors="coerce")
            stats[column] = float(series.median()) if series.notna().any() else 0.0
    return stats


def _city_reference_options(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "city" not in frame.columns:
        return []
    cities = [str(value) for value in frame["city"].dropna().astype(str).unique().tolist()]
    return sorted(cities)


def _city_reference_value(frame: pd.DataFrame, fallback_city: str) -> str:
    if frame.empty or "city" not in frame.columns:
        return fallback_city
    mode_series = frame["city"].dropna()
    if mode_series.empty:
        return fallback_city
    return str(mode_series.mode().iloc[0])


def _clip_value(feature: str, value: float) -> float:
    bounds = BOUNDED_RANGES.get(feature)
    if bounds is None:
        return value
    lower, upper = bounds
    clipped = max(value, lower)
    if upper is not None:
        clipped = min(clipped, upper)
    return clipped


def _build_perturbation_samples(
    base_row: pd.Series,
    frame: pd.DataFrame,
    *,
    sample_count: int,
    random_state: int,
) -> pd.DataFrame:
    generator = np.random.default_rng(random_state)
    stats = _numeric_reference_stats(frame)
    city_options = _city_reference_options(frame) or [str(base_row.get("city", "Karachi"))]
    city_mode = _city_reference_value(frame, str(base_row.get("city", "Karachi")))

    rows: list[dict[str, Any]] = []
    for _ in range(sample_count):
        row = base_row.to_dict()
        for feature in TRAINING_FEATURE_COLUMNS:
            if feature == "city":
                row["city"] = str(generator.choice(city_options)) if generator.random() < 0.45 else city_mode
                continue

            current_value = float(pd.to_numeric(pd.Series([row.get(feature)]), errors="coerce").iloc[0])
            reference_value = stats.get(feature, current_value)
            spread = max(abs(reference_value) * 0.15, 0.5)
            sampled_value = float(generator.normal(loc=current_value, scale=spread))
            row[feature] = _clip_value(feature, sampled_value)
        rows.append(row)

    return pd.DataFrame(rows, columns=TRAINING_FEATURE_COLUMNS)


def _transformed_feature_names(pipeline: Any) -> list[str]:
    preprocessor = pipeline.named_steps["preprocess"]
    try:
        return [str(name) for name in preprocessor.get_feature_names_out()]
    except Exception:
        numeric_features = list(getattr(preprocessor, "feature_names_in_", TRAINING_FEATURE_COLUMNS))
        return [str(name) for name in numeric_features]


def _to_dense(frame_or_matrix: Any) -> np.ndarray:
    if hasattr(frame_or_matrix, "toarray"):
        return frame_or_matrix.toarray()
    return np.asarray(frame_or_matrix)


def _aggregate(values: dict[str, float]) -> list[GlobalImportance]:
    grouped: dict[str, float] = {}
    for feature_name, value in values.items():
        grouped[_group_name(feature_name)] = grouped.get(_group_name(feature_name), 0.0) + float(abs(value))
    return sorted(
        (GlobalImportance(feature=name, importance=importance) for name, importance in grouped.items()),
        key=lambda item: item.importance,
        reverse=True,
    )


def _model_importances(pipeline: Any) -> list[GlobalImportance]:
    estimator = pipeline.named_steps["model"]
    transformed_names = _transformed_feature_names(pipeline)

    if hasattr(estimator, "feature_importances_"):
        raw_importances = dict(zip(transformed_names, [float(value) for value in estimator.feature_importances_]))
        return _aggregate(raw_importances)

    if hasattr(estimator, "coef_"):
        coefficients = np.asarray(estimator.coef_).ravel()
        raw_importances = dict(zip(transformed_names, [float(value) for value in coefficients]))
        return _aggregate(raw_importances)

    return []


def _build_local_result(
    *,
    model_name: str,
    prediction: float,
    baseline_prediction: float,
    transformed_names: list[str],
    transformed_values: np.ndarray,
    local_values: np.ndarray,
    method: str,
    notes: list[str],
    top_n: int,
) -> ExplanationResult:
    local_contributions: list[LocalContribution] = []
    for name, transformed_value, contribution in zip(transformed_names, transformed_values, local_values):
        local_contributions.append(
            LocalContribution(
                feature=_group_name(name),
                transformed_feature=name,
                value=float(transformed_value),
                baseline=0.0,
                contribution=float(contribution),
            )
        )

    grouped_local: dict[str, LocalContribution] = {}
    for item in local_contributions:
        if item.feature not in grouped_local:
            grouped_local[item.feature] = LocalContribution(
                feature=item.feature,
                transformed_feature=item.transformed_feature,
                value=item.value,
                baseline=item.baseline,
                contribution=item.contribution,
            )
        else:
            existing = grouped_local[item.feature]
            grouped_local[item.feature] = LocalContribution(
                feature=item.feature,
                transformed_feature=existing.transformed_feature,
                value=existing.value,
                baseline=existing.baseline,
                contribution=existing.contribution + item.contribution,
            )

    ranked_local = sorted(grouped_local.values(), key=lambda item: abs(item.contribution), reverse=True)[:top_n]

    return ExplanationResult(
        model_name=model_name,
        method=method,
        prediction=prediction,
        baseline_prediction=baseline_prediction,
        local_contributions=ranked_local,
        global_importance=[],
        notes=notes,
    )


def _shap_explanation(
    *,
    model_name: str,
    pipeline: Any,
    input_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    sample_count: int,
    random_state: int,
    top_n: int,
) -> ExplanationResult | None:
    if not SHAP_AVAILABLE:
        return None

    estimator = pipeline.named_steps["model"]
    transformed_names = _transformed_feature_names(pipeline)

    background_frame = reference_frame if not reference_frame.empty else input_frame
    if len(background_frame) > sample_count:
        background_frame = background_frame.sample(n=sample_count, random_state=random_state)

    background_transformed = _to_dense(pipeline.named_steps["preprocess"].transform(background_frame))
    input_transformed = _to_dense(pipeline.named_steps["preprocess"].transform(input_frame))

    try:
        explainer = shap.Explainer(estimator, background_transformed, feature_names=transformed_names)
        shap_values = explainer(input_transformed)
        values = np.asarray(shap_values.values)
        if values.ndim == 3:
            values = values[0]
        if values.ndim == 2:
            values = values[0]

        base_value = getattr(shap_values, "base_values", getattr(explainer, "expected_value", 0.0))
        baseline_prediction = float(np.asarray(base_value).mean())
        prediction = float(np.asarray(pipeline.predict(input_frame))[0])

        local_result = _build_local_result(
            model_name=model_name,
            prediction=prediction,
            baseline_prediction=baseline_prediction,
            transformed_names=transformed_names,
            transformed_values=input_transformed[0],
            local_values=np.asarray(values).ravel(),
            method="SHAP",
            notes=[
                "SHAP is used when the package is available in the environment.",
                "The model is explained in transformed feature space and grouped back to business features.",
            ],
            top_n=top_n,
        )

        background_sample = background_transformed
        if len(background_sample) > min(sample_count, 80):
            background_sample = background_sample[: min(sample_count, 80)]
        background_values = explainer(background_sample)
        global_values = np.asarray(background_values.values)
        if global_values.ndim == 3:
            global_values = global_values[0]
        if global_values.ndim == 1:
            global_values = global_values.reshape(1, -1)

        global_importance = {
            name: float(np.mean(np.abs(global_values[:, index])))
            for index, name in enumerate(transformed_names)
        }
        local_result.global_importance = _aggregate(global_importance)[:top_n]
        return local_result
    except Exception as exc:
        logger.warning("SHAP explanation failed, falling back to local surrogate: %s", exc)
        return None


def _local_surrogate_explanation(
    *,
    model_name: str,
    pipeline: Any,
    input_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    sample_count: int,
    random_state: int,
    top_n: int,
) -> ExplanationResult:
    base_row = input_frame.iloc[0]
    perturbed_frame = _build_perturbation_samples(
        base_row,
        reference_frame if not reference_frame.empty else input_frame,
        sample_count=sample_count,
        random_state=random_state,
    )
    perturbation_predictions = pipeline.predict(perturbed_frame)
    transformed = _to_dense(pipeline.named_steps["preprocess"].transform(perturbed_frame))
    transformed_names = _transformed_feature_names(pipeline)
    transformed_frame = pd.DataFrame(transformed, columns=transformed_names)

    weights = np.exp(-np.linalg.norm(transformed_frame - transformed_frame.iloc[0], axis=1))
    surrogate = Ridge(alpha=1.0, random_state=random_state)
    surrogate.fit(transformed_frame, perturbation_predictions, sample_weight=weights)

    baseline_transformed = _to_dense(pipeline.named_steps["preprocess"].transform(input_frame))
    baseline_series = pd.Series(np.asarray(baseline_transformed).ravel(), index=transformed_names)
    surrogate_coefficients = pd.Series(np.asarray(surrogate.coef_).ravel(), index=transformed_names)

    local_values = surrogate_coefficients * baseline_series
    result = _build_local_result(
        model_name=model_name,
        prediction=float(pipeline.predict(input_frame)[0]),
        baseline_prediction=float(surrogate.intercept_),
        transformed_names=transformed_names,
        transformed_values=np.asarray(baseline_series.values, dtype=float),
        local_values=np.asarray(local_values.values, dtype=float),
        method="LIME-style local surrogate",
        notes=[
            "SHAP is not installed, so the app used a local surrogate explanation.",
            "Install `shap` to enable true SHAP explanations in this project.",
        ],
        top_n=top_n,
    )
    result.global_importance = _model_importances(pipeline)[:top_n]
    return result


def explain_prediction(
    record: dict[str, Any],
    *,
    model_name: str | None = None,
    reference_frame: pd.DataFrame | None = None,
    sample_count: int = 160,
    random_state: int = 42,
    top_n: int = 10,
    model_dir: str | None = None,
) -> ExplanationResult:
    loaded_model_name, pipeline = load_model(model_name=model_name, model_dir=model_dir or (Path("models") / "latest"))
    reference = _reference_frame(reference_frame)
    input_frame = _coerce_frame(pd.DataFrame([record]))

    shap_result = _shap_explanation(
        pipeline=pipeline,
        model_name=loaded_model_name,
        input_frame=input_frame,
        reference_frame=reference,
        sample_count=sample_count,
        random_state=random_state,
        top_n=top_n,
    )
    if shap_result is not None:
        shap_result.model_name = loaded_model_name
        shap_result.notes.insert(0, "SHAP-based explanation generated successfully.")
        return shap_result

    return _local_surrogate_explanation(
        model_name=loaded_model_name,
        pipeline=pipeline,
        input_frame=input_frame,
        reference_frame=reference,
        sample_count=sample_count,
        random_state=random_state,
        top_n=top_n,
    )
