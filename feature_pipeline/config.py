from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str | None
    openmeteo_api_key: str | None
    aqicn_api_key: str | None
    timeout_seconds: float
    retry_count: int
    retry_backoff_seconds: float
    provider_concurrency: int
    output_path: str


settings = Settings(
    openweather_api_key=os.getenv("OPENWEATHER_API_KEY"),
    openmeteo_api_key=os.getenv("OPENMETEO_API_KEY"),
    aqicn_api_key=os.getenv("AQICN_API_KEY"),
    timeout_seconds=_get_float("REQUEST_TIMEOUT", 20.0),
    retry_count=_get_int("RETRY_COUNT", 3),
    retry_backoff_seconds=_get_float("RETRY_BACKOFF_SECONDS", 1.5),
    provider_concurrency=_get_int("PROVIDER_CONCURRENCY", 4),
    output_path=os.getenv("RAW_OUTPUT_PATH", "data/raw/raw_data.csv"),
)


STANDARD_COLUMNS = [
    "timestamp",
    "city",
    "country",
    "latitude",
    "longitude",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "rain",
    "aqi",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
    "source",
    "status",
    "response_time_seconds",
    "raw_payload",
]
