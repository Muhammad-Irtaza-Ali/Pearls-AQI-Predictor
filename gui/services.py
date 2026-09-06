from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from gui.api_client import APIClientError, fetch_ml_ready_data


ROOT_DIR = Path(__file__).resolve().parents[1]
GOLD_DATA_PATH = ROOT_DIR / "data" / "gold" / "ml_ready_records.csv"
TRAINING_REPORT_PATH = ROOT_DIR / "models" / "latest" / "training_report.json"
EVALUATION_SUMMARY_PATH = ROOT_DIR / "reports" / "model_evaluation_summary.json"
QUALITY_REPORT_PATH = ROOT_DIR / "reports" / "data_quality_report.json"
PROJECT_STATUS_PATH = ROOT_DIR / "reports" / "project_status_report.md"
RAW_UPLOAD_REPORT_PATH = ROOT_DIR / "reports" / "raw_supabase_upload_report.json"
ML_READY_UPLOAD_REPORT_PATH = ROOT_DIR / "reports" / "ml_ready_upload_report.json"
MODEL_EVALUATION_SOURCE = EVALUATION_SUMMARY_PATH

AQI_BANDS = [
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for Sensitive Groups"),
    (200, "Unhealthy"),
    (300, "Very Unhealthy"),
    (float("inf"), "Hazardous"),
]


@dataclass(slots=True)
class CitySummary:
    city: str
    rows: int
    latest_timestamp: str | None
    latest_aqi: float | None
    average_aqi: float | None
    temperature: float | None
    humidity: float | None
    pressure: float | None
    wind_speed: float | None


@st.cache_data(ttl="30m")
def load_dataset() -> pd.DataFrame:
    try:
        frame = fetch_ml_ready_data()
    except APIClientError:
        frame = None

    if frame is not None and not frame.empty:
        if "timestamp" in frame.columns:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        if "data_date" in frame.columns:
            frame["data_date"] = pd.to_datetime(frame["data_date"], errors="coerce")
        return frame

    if not GOLD_DATA_PATH.exists():
        return pd.DataFrame()
    frame = pd.read_csv(GOLD_DATA_PATH, low_memory=False)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    if "data_date" in frame.columns:
        frame["data_date"] = pd.to_datetime(frame["data_date"], errors="coerce")
    return frame


@st.cache_data(ttl="30m")
def load_json_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(ttl="30m")
def load_text_report(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


@st.cache_data(ttl="30m")
def load_model_comparison() -> dict[str, Any]:
    return load_json_report(MODEL_EVALUATION_SOURCE)


def available_models() -> list[dict[str, Any]]:
    report = load_model_comparison()
    models = report.get("models_ranked_by_rmse", [])
    return [model for model in models if isinstance(model, dict)]


def best_model_name() -> str | None:
    report = load_model_comparison()
    best_model = report.get("best_model")
    return str(best_model) if best_model else None


def clear_cached_data() -> None:
    st.cache_data.clear()


def city_options(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "city" not in frame.columns:
        return []
    return sorted(str(value) for value in frame["city"].dropna().unique().tolist())


def aqi_category(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 150:
        return "Unhealthy for Sensitive Groups"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _latest_row(group: pd.DataFrame) -> pd.Series:
    if "timestamp" in group.columns and group["timestamp"].notna().any():
        ordered = group.sort_values("timestamp")
    elif "data_date" in group.columns and group["data_date"].notna().any():
        ordered = group.sort_values("data_date")
    else:
        ordered = group
    return ordered.iloc[-1]


def build_city_summaries(frame: pd.DataFrame) -> list[CitySummary]:
    if frame.empty or "city" not in frame.columns:
        return []

    summaries: list[CitySummary] = []
    for city, group in frame.groupby("city"):
        latest = _latest_row(group)
        summaries.append(
            CitySummary(
                city=str(city),
                rows=int(len(group)),
                latest_timestamp=str(latest.get("timestamp")) if pd.notna(latest.get("timestamp")) else None,
                latest_aqi=float(latest.get("aqi")) if pd.notna(latest.get("aqi")) else None,
                average_aqi=float(pd.to_numeric(group["aqi"], errors="coerce").mean()) if "aqi" in group.columns else None,
                temperature=float(latest.get("temperature")) if pd.notna(latest.get("temperature")) else None,
                humidity=float(latest.get("humidity")) if pd.notna(latest.get("humidity")) else None,
                pressure=float(latest.get("pressure")) if pd.notna(latest.get("pressure")) else None,
                wind_speed=float(latest.get("wind_speed")) if pd.notna(latest.get("wind_speed")) else None,
            )
        )
    return sorted(summaries, key=lambda item: item.city)


def latest_snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "city" not in frame.columns:
        return pd.DataFrame()
    rows = []
    for _, group in frame.groupby("city"):
        rows.append(_latest_row(group))
    return pd.DataFrame(rows)


def current_overview(frame: pd.DataFrame) -> dict[str, Any]:
    snapshot = latest_snapshot(frame)
    if snapshot.empty:
        return {}

    aqi_series = pd.to_numeric(snapshot["aqi"], errors="coerce")
    valid = snapshot[aqi_series.notna()].copy()
    latest_idx = pd.to_datetime(snapshot["timestamp"], errors="coerce", utc=True).idxmax() if "timestamp" in snapshot.columns and snapshot["timestamp"].notna().any() else snapshot.index[-1]
    latest_row = snapshot.loc[latest_idx]
    highest_row = valid.loc[pd.to_numeric(valid["aqi"], errors="coerce").idxmax()] if not valid.empty else latest_row
    lowest_row = valid.loc[pd.to_numeric(valid["aqi"], errors="coerce").idxmin()] if not valid.empty else latest_row

    return {
        "current_aqi": float(latest_row.get("aqi")) if pd.notna(latest_row.get("aqi")) else None,
        "aqi_category": aqi_category(float(latest_row.get("aqi"))) if pd.notna(latest_row.get("aqi")) else "Not available",
        "highest_city": str(highest_row.get("city")) if pd.notna(highest_row.get("city")) else "Not available",
        "lowest_city": str(lowest_row.get("city")) if pd.notna(lowest_row.get("city")) else "Not available",
        "average_aqi": float(aqi_series.mean()) if not aqi_series.dropna().empty else None,
        "active_cities": int(snapshot["city"].nunique()),
        "last_update": str(pd.to_datetime(latest_row.get("timestamp"), errors="coerce", utc=True)) if pd.notna(latest_row.get("timestamp")) else None,
        "model_status": "Ready" if (ROOT_DIR / "models" / "latest" / "manifest.json").exists() else "Not available",
    }


def filter_frame(frame: pd.DataFrame, cities: list[str] | None = None, start_date: Any | None = None, end_date: Any | None = None) -> pd.DataFrame:
    filtered = frame.copy()
    if cities:
        filtered = filtered[filtered["city"].isin(cities)]
    if start_date is not None and end_date is not None and "timestamp" in filtered.columns:
        filtered = filtered[(filtered["timestamp"].dt.date >= start_date) & (filtered["timestamp"].dt.date <= end_date)]
    return filtered
