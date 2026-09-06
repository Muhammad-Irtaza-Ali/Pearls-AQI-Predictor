from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://pearls-aqi-predictor.onrender.com",
).rstrip("/")


class APIClientError(RuntimeError):
    """Raised when the prediction API cannot return a usable response."""


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", timeout=30, **kwargs)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise APIClientError(f"Backend request failed: {exc}") from exc
    except ValueError as exc:
        raise APIClientError("Backend returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise APIClientError("Backend returned an unexpected response.")
    return payload


def predict(record: dict[str, Any]) -> dict[str, Any]:
    payload = _request("POST", "/predict", json=record)
    if "predicted_aqi" not in payload:
        raise APIClientError("Backend response did not include predicted_aqi.")
    return payload


def batch_predict(dataframe: pd.DataFrame) -> pd.DataFrame:
    payload = _request("POST", "/batch-predict", json={"records": dataframe.to_dict(orient="records")})
    predictions = payload.get("predictions")
    if not isinstance(predictions, list):
        raise APIClientError("Backend response did not include predictions.")
    return pd.DataFrame(predictions)


def fetch_ml_ready_data() -> pd.DataFrame:
    payload = _request("GET", "/data/ml-ready")
    records = payload.get("records")
    if not isinstance(records, list):
        raise APIClientError("Backend response did not include dashboard records.")
    return pd.DataFrame(records)