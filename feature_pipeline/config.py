from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


def _city_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _load_openweather_location_ids() -> dict[str, str]:
    mapping: dict[str, str] = {}
    raw_value = os.getenv("OPENWEATHER_LOCATION_IDS")
    if raw_value:
        try:
            parsed_value = json.loads(raw_value)
        except json.JSONDecodeError:
            parsed_value = {}
        if isinstance(parsed_value, dict):
            for key, value in parsed_value.items():
                if value is None:
                    continue
                city_key = str(key).strip()
                location_id = str(value).strip()
                if city_key and location_id:
                    mapping[city_key] = location_id
                    mapping[_city_key(city_key)] = location_id

    prefix = "OPENWEATHER_LOCATION_ID_"
    for environment_key, environment_value in os.environ.items():
        if not environment_key.startswith(prefix) or not environment_value.strip():
            continue
        suffix = environment_key[len(prefix) :].strip()
        location_id = environment_value.strip()
        mapping[suffix] = location_id
        mapping[_city_key(suffix)] = location_id
    return mapping


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str | None
    openweather_location_ids: dict[str, str]
    backfill_openweather_history_weather: bool
    supabase_enabled: bool
    supabase_url: str | None
    supabase_service_role_key: str | None
    supabase_raw_table: str
    hopsworks_enabled: bool
    hopsworks_project: str | None
    hopsworks_api_key: str | None
    hopsworks_host: str | None
    hopsworks_python_exe: str | None
    hopsworks_feature_group: str
    hopsworks_feature_group_version: int
    openmeteo_api_key: str | None
    aqicn_api_key: str | None
    timeout_seconds: float
    retry_count: int
    retry_backoff_seconds: float
    provider_concurrency: int
    output_path: str
    bronze_output_path: str
    silver_output_path: str
    gold_output_path: str
    gold_runs_dir: str
    reports_dir: str
    drift_reports_dir: str


settings = Settings(
    openweather_api_key=os.getenv("OPENWEATHER_API_KEY"),
    openweather_location_ids=_load_openweather_location_ids(),
    backfill_openweather_history_weather=os.getenv("BACKFILL_OPENWEATHER_HISTORY_WEATHER", "false").strip().lower()
    in {"1", "true", "yes", "on"},
    supabase_enabled=os.getenv("SUPABASE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    supabase_raw_table=os.getenv("SUPABASE_RAW_TABLE", "raw_records"),
    hopsworks_enabled=os.getenv("HOPSWORKS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
    hopsworks_project=os.getenv("HOPSWORKS_PROJECT"),
    hopsworks_api_key=os.getenv("HOPSWORKS_API_KEY"),
    hopsworks_host=os.getenv("HOPSWORKS_HOST"),
    hopsworks_python_exe=os.getenv("HOPSWORKS_PYTHON_EXE"),
    hopsworks_feature_group=os.getenv("HOPSWORKS_FEATURE_GROUP", "daily_aqi_features"),
    hopsworks_feature_group_version=_get_int("HOPSWORKS_FEATURE_GROUP_VERSION", 1),
    openmeteo_api_key=os.getenv("OPENMETEO_API_KEY"),
    aqicn_api_key=os.getenv("AQICN_API_KEY"),
    timeout_seconds=_get_float("REQUEST_TIMEOUT", 20.0),
    retry_count=_get_int("RETRY_COUNT", 3),
    retry_backoff_seconds=_get_float("RETRY_BACKOFF_SECONDS", 1.5),
    provider_concurrency=_get_int("PROVIDER_CONCURRENCY", 4),
    output_path=os.getenv("RAW_OUTPUT_PATH", "data/raw/raw_data.csv"),
    bronze_output_path=os.getenv("BRONZE_OUTPUT_PATH", "data/bronze/raw_records.csv"),
    silver_output_path=os.getenv("SILVER_OUTPUT_PATH", "data/silver/validated_records.csv"),
    gold_output_path=os.getenv("GOLD_OUTPUT_PATH", "data/gold/merged_records.csv"),
    gold_runs_dir=os.getenv("GOLD_RUNS_DIR", "data/gold/runs"),
    reports_dir=os.getenv("REPORTS_DIR", "reports"),
    drift_reports_dir=os.getenv("DRIFT_REPORTS_DIR", "reports/drift"),
)


PIPELINE_VERSION = "2.2.0"

API_VERSIONS = {
    "openweather": "2.5",
    "openweather_history": "3.0",
    "openmeteo": "v1",
    "aqicn": "v1",
}


STANDARD_COLUMNS = [
    "timestamp",
    "data_date",
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
    "run_id",
    "pipeline_version",
    "api_version",
    "retrieved_at",
    "response_time_ms",
    "response_time_seconds",
    "raw_payload",
]
