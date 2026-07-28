from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from drift.thresholds import NUMERIC_DRIFT_FIELDS


@dataclass(frozen=True, slots=True)
class FeatureStatistics:
    mean: float | None
    median: float | None
    minimum: float | None
    maximum: float | None
    standard_deviation: float | None
    missing_count: int
    missing_percentage: float
    unique_values: int
    record_count: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def compute_feature_statistics(frame: pd.DataFrame, column: str) -> FeatureStatistics:
    numeric_series = _to_numeric_series(frame, column)
    total_rows = int(len(frame))
    non_null_series = numeric_series.dropna()
    missing_count = int(numeric_series.isna().sum())
    missing_percentage = (missing_count / total_rows * 100.0) if total_rows else 0.0
    return FeatureStatistics(
        mean=float(non_null_series.mean()) if not non_null_series.empty else None,
        median=float(non_null_series.median()) if not non_null_series.empty else None,
        minimum=float(non_null_series.min()) if not non_null_series.empty else None,
        maximum=float(non_null_series.max()) if not non_null_series.empty else None,
        standard_deviation=float(non_null_series.std(ddof=0)) if len(non_null_series) > 0 else None,
        missing_count=missing_count,
        missing_percentage=missing_percentage,
        unique_values=int(non_null_series.nunique(dropna=True)),
        record_count=total_rows,
    )


def compute_statistics(frame: pd.DataFrame) -> dict[str, FeatureStatistics]:
    return {field_name: compute_feature_statistics(frame, field_name) for field_name in NUMERIC_DRIFT_FIELDS}


def _safe_difference(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def _safe_percentage_difference(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0


def compare_statistics(
    current: FeatureStatistics,
    previous: FeatureStatistics,
) -> dict[str, Any]:
    return {
        "current": current.as_dict(),
        "previous": previous.as_dict(),
        "difference": {
            "mean": _safe_difference(current.mean, previous.mean),
            "median": _safe_difference(current.median, previous.median),
            "minimum": _safe_difference(current.minimum, previous.minimum),
            "maximum": _safe_difference(current.maximum, previous.maximum),
            "standard_deviation": _safe_difference(current.standard_deviation, previous.standard_deviation),
            "missing_count": current.missing_count - previous.missing_count,
            "missing_percentage": current.missing_percentage - previous.missing_percentage,
            "record_count": current.record_count - previous.record_count,
            "unique_values": current.unique_values - previous.unique_values,
        },
        "percentage": {
            "mean": _safe_percentage_difference(current.mean, previous.mean),
            "median": _safe_percentage_difference(current.median, previous.median),
            "minimum": _safe_percentage_difference(current.minimum, previous.minimum),
            "maximum": _safe_percentage_difference(current.maximum, previous.maximum),
            "standard_deviation": _safe_percentage_difference(current.standard_deviation, previous.standard_deviation),
            "missing_count": _safe_percentage_difference(float(current.missing_count), float(previous.missing_count)),
            "missing_percentage": _safe_percentage_difference(current.missing_percentage, previous.missing_percentage),
            "record_count": _safe_percentage_difference(float(current.record_count), float(previous.record_count)),
            "unique_values": _safe_percentage_difference(float(current.unique_values), float(previous.unique_values)),
        },
    }
