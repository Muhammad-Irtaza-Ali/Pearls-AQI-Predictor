from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AirQualityRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: datetime = Field(...)
    city: str = Field(min_length=1)
    country: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    temperature: float | None = Field(default=None, ge=-80, le=70)
    humidity: float | None = Field(default=None, ge=0, le=100)
    pressure: float | None = Field(default=None, ge=0)
    wind_speed: float | None = Field(default=None, ge=0)
    wind_direction: float | None = Field(default=None, ge=0, le=360)
    cloud_cover: float | None = Field(default=None, ge=0, le=100)
    rain: float | None = Field(default=None, ge=0)
    aqi: int | None = Field(default=None, ge=0)
    pm25: float | None = Field(default=None, ge=0)
    pm10: float | None = Field(default=None, ge=0)
    co: float | None = Field(default=None, ge=0)
    no: float | None = Field(default=None, ge=0)
    no2: float | None = Field(default=None, ge=0)
    so2: float | None = Field(default=None, ge=0)
    o3: float | None = Field(default=None, ge=0)
    nh3: float | None = Field(default=None, ge=0)
    source: str = Field(min_length=1)
    status: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    pipeline_version: str = Field(min_length=1)
    api_version: str | None = None
    retrieved_at: datetime = Field(...)
    response_time_ms: int = Field(ge=0)
    response_time_seconds: float | None = Field(default=None, ge=0)
    raw_payload: dict[str, Any] | list[Any] | None = None

    @field_validator("city", "country", "source", "status", "run_id", "pipeline_version", "api_version", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value.upper() == "N/A":
                return None
            return value
        return value

    @field_validator("raw_payload", mode="before")
    @classmethod
    def normalize_raw_payload(cls, value: Any) -> Any:
        if isinstance(value, str):
            text = value.strip()
            if not text or text.upper() == "N/A":
                return None
            return value
        return value

