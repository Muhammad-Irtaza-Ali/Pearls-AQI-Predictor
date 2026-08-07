from __future__ import annotations

HOPSWORKS_FEATURE_GROUP_NAME = "daily_aqi_features"
HOPSWORKS_FEATURE_GROUP_VERSION = 1
HOPSWORKS_PRIMARY_KEYS = ["city", "data_date"]
HOPSWORKS_EVENT_TIME = "timestamp"

HOPSWORKS_FEATURE_COLUMNS = [
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
    "lineage",
    "raw_payload",
]

