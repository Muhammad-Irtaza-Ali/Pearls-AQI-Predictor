from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from feature_pipeline.api import main as api_main
from feature_pipeline.modeling.predictor import PredictionResult


client = TestClient(api_main.app)


def test_health_endpoint_reflects_model_manifest_state(tmp_path, monkeypatch) -> None:
    model_dir = tmp_path / "models" / "latest"
    model_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_main, "MODEL_DIR", model_dir)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_ready"] is False


def test_predict_endpoint_returns_prediction(monkeypatch) -> None:
    monkeypatch.setattr(
        api_main,
        "predict_single",
        lambda payload, model_dir=None: PredictionResult(
            model_name="random_forest",
            prediction=88.0,
            input_row=payload,
        ),
    )

    response = client.post(
        "/predict",
        json={
            "latitude": 24.8607,
            "longitude": 67.0011,
            "city": "Karachi",
            "temperature": 30.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "random_forest"
    assert payload["predicted_aqi"] == 88.0
    assert payload["input"]["city"] == "Karachi"


def test_batch_predict_endpoint_returns_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        api_main,
        "predict_dataframe",
        lambda dataframe, model_dir=None: dataframe.assign(
            predicted_aqi=[50.0] * len(dataframe),
            best_model="gradient_boosting",
        ),
    )

    response = client.post(
        "/batch-predict",
        json={
            "records": [
                {
                    "latitude": 24.8607,
                    "longitude": 67.0011,
                    "city": "Karachi",
                    "temperature": 30.0,
                },
                {
                    "latitude": 31.5204,
                    "longitude": 74.3587,
                    "city": "Lahore",
                    "temperature": 28.0,
                },
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "gradient_boosting"
    assert len(payload["predictions"]) == 2
