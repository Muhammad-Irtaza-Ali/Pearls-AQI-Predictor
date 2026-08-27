from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from feature_pipeline.modeling import predictor


class ConstantModel:
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        return np.full(len(features), 123.0)


def test_predict_dataframe_uses_manifest_when_registry_is_empty(tmp_path: Path, monkeypatch) -> None:
    model_dir = tmp_path / "models" / "latest"
    model_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = model_dir / "constant_model.joblib"
    joblib.dump(ConstantModel(), artifact_path)
    (model_dir / "manifest.json").write_text(
        """
        {
          "best_model": "constant_model",
          "artifacts": {
            "constant_model": "constant_model.joblib"
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(predictor, "resolve_registered_model", lambda model_name=None: None)

    frame = pd.DataFrame(
        [
            {
                "timestamp": "2026-08-01T00:00:00Z",
                "city": "Karachi",
                "latitude": 24.8607,
                "longitude": 67.0011,
                "temperature": 30.0,
                "humidity": 60.0,
                "pressure": 1000.0,
                "wind_speed": 5.0,
                "wind_direction": 180.0,
                "cloud_cover": 10.0,
                "rain": 0.0,
                "pm25": 14.0,
                "pm10": 25.0,
                "co": 100.0,
                "no": 1.0,
                "no2": 2.0,
                "so2": 3.0,
                "o3": 4.0,
                "nh3": 5.0,
            }
        ]
    )

    result = predictor.predict_dataframe(frame, model_dir=model_dir)

    assert result["predicted_aqi"].tolist() == [123.0]
    assert result["best_model"].tolist() == ["constant_model"]


def test_predict_single_returns_model_name_and_prediction(tmp_path: Path, monkeypatch) -> None:
    model_dir = tmp_path / "models" / "latest"
    model_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = model_dir / "constant_model.joblib"
    joblib.dump(ConstantModel(), artifact_path)
    (model_dir / "manifest.json").write_text(
        """
        {
          "best_model": "constant_model",
          "artifacts": {
            "constant_model": "constant_model.joblib"
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(predictor, "resolve_registered_model", lambda model_name=None: None)

    result = predictor.predict_single(
        {
            "timestamp": "2026-08-01T00:00:00Z",
            "city": "Karachi",
            "latitude": 24.8607,
            "longitude": 67.0011,
            "temperature": 30.0,
            "humidity": 60.0,
            "pressure": 1000.0,
            "wind_speed": 5.0,
            "wind_direction": 180.0,
            "cloud_cover": 10.0,
            "rain": 0.0,
            "pm25": 14.0,
            "pm10": 25.0,
            "co": 100.0,
            "no": 1.0,
            "no2": 2.0,
            "so2": 3.0,
            "o3": 4.0,
            "nh3": 5.0,
        },
        model_dir=model_dir,
    )

    assert result.model_name == "constant_model"
    assert result.prediction == 123.0
