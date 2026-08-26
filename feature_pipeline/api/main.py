from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from feature_pipeline.modeling.predictor import predict_dataframe, predict_single


MODEL_DIR = Path("models") / "latest"

app = FastAPI(title="Pearls AQI Predictor", version="1.0.0")


class AQIPredictionRequest(BaseModel):
    latitude: float
    longitude: float
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    cloud_cover: float | None = None
    rain: float | None = None
    pm25: float | None = None
    pm10: float | None = None
    co: float | None = None
    no: float | None = None
    no2: float | None = None
    so2: float | None = None
    o3: float | None = None
    nh3: float | None = None
    city: str
    timestamp: str | None = Field(default=None, description="ISO timestamp used to derive date features")


class BatchAQIPredictionRequest(BaseModel):
    records: list[AQIPredictionRequest]


@app.get("/health")
def health() -> dict[str, Any]:
    manifest_path = MODEL_DIR / "manifest.json"
    return {
        "status": "ok",
        "model_dir": str(MODEL_DIR),
        "model_ready": manifest_path.exists(),
    }


@app.post("/predict")
def predict(record: AQIPredictionRequest) -> dict[str, Any]:
    try:
        result = predict_single(record.model_dump(), model_dir=MODEL_DIR)
    except Exception as exc:  # pragma: no cover - API safety
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "model_name": result.model_name,
        "predicted_aqi": result.prediction,
        "input": result.input_row,
    }


@app.post("/batch-predict")
def batch_predict(request: BatchAQIPredictionRequest) -> dict[str, Any]:
    try:
        dataframe = pd.DataFrame([record.model_dump() for record in request.records])
        predictions = predict_dataframe(dataframe, model_dir=MODEL_DIR)
    except Exception as exc:  # pragma: no cover - API safety
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "model_name": predictions["best_model"].iloc[0] if not predictions.empty else None,
        "predictions": predictions.to_dict(orient="records"),
    }

