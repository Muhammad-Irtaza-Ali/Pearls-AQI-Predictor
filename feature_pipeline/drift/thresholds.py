from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from typing import Any


NUMERIC_DRIFT_FIELDS: tuple[str, ...] = (
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "aqi",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
)


DEFAULT_THRESHOLD_VALUES: dict[str, float] = {
    "temperature": 5.0,
    "humidity": 10.0,
    "pressure": 10.0,
    "wind_speed": 10.0,
    "aqi": 10.0,
    "pm25": 10.0,
    "pm10": 10.0,
    "co": 10.0,
    "no": 10.0,
    "no2": 10.0,
    "so2": 10.0,
    "o3": 10.0,
    "nh3": 10.0,
    "record_count": 10.0,
    "missing_percentage": 10.0,
}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None and value != "" else default


@dataclass(frozen=True, slots=True)
class DriftThresholds:
    temperature: float = 5.0
    humidity: float = 10.0
    pressure: float = 10.0
    wind_speed: float = 10.0
    aqi: float = 10.0
    pm25: float = 10.0
    pm10: float = 10.0
    co: float = 10.0
    no: float = 10.0
    no2: float = 10.0
    so2: float = 10.0
    o3: float = 10.0
    nh3: float = 10.0
    record_count: float = 10.0
    missing_percentage: float = 10.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def load_thresholds(overrides: dict[str, Any] | None = None) -> DriftThresholds:
    """Load drift thresholds from the environment with optional overrides."""

    override_values = overrides or {}
    return DriftThresholds(
        temperature=float(override_values.get("temperature", _get_float("DRIFT_THRESHOLD_TEMPERATURE", DEFAULT_THRESHOLD_VALUES["temperature"]))),
        humidity=float(override_values.get("humidity", _get_float("DRIFT_THRESHOLD_HUMIDITY", DEFAULT_THRESHOLD_VALUES["humidity"]))),
        pressure=float(override_values.get("pressure", _get_float("DRIFT_THRESHOLD_PRESSURE", DEFAULT_THRESHOLD_VALUES["pressure"]))),
        wind_speed=float(override_values.get("wind_speed", _get_float("DRIFT_THRESHOLD_WIND_SPEED", DEFAULT_THRESHOLD_VALUES["wind_speed"]))),
        aqi=float(override_values.get("aqi", _get_float("DRIFT_THRESHOLD_AQI", DEFAULT_THRESHOLD_VALUES["aqi"]))),
        pm25=float(override_values.get("pm25", _get_float("DRIFT_THRESHOLD_PM25", DEFAULT_THRESHOLD_VALUES["pm25"]))),
        pm10=float(override_values.get("pm10", _get_float("DRIFT_THRESHOLD_PM10", DEFAULT_THRESHOLD_VALUES["pm10"]))),
        co=float(override_values.get("co", _get_float("DRIFT_THRESHOLD_CO", DEFAULT_THRESHOLD_VALUES["co"]))),
        no=float(override_values.get("no", _get_float("DRIFT_THRESHOLD_NO", DEFAULT_THRESHOLD_VALUES["no"]))),
        no2=float(override_values.get("no2", _get_float("DRIFT_THRESHOLD_NO2", DEFAULT_THRESHOLD_VALUES["no2"]))),
        so2=float(override_values.get("so2", _get_float("DRIFT_THRESHOLD_SO2", DEFAULT_THRESHOLD_VALUES["so2"]))),
        o3=float(override_values.get("o3", _get_float("DRIFT_THRESHOLD_O3", DEFAULT_THRESHOLD_VALUES["o3"]))),
        nh3=float(override_values.get("nh3", _get_float("DRIFT_THRESHOLD_NH3", DEFAULT_THRESHOLD_VALUES["nh3"]))),
        record_count=float(override_values.get("record_count", _get_float("DRIFT_THRESHOLD_RECORD_COUNT", DEFAULT_THRESHOLD_VALUES["record_count"]))),
        missing_percentage=float(
            override_values.get(
                "missing_percentage",
                _get_float("DRIFT_THRESHOLD_MISSING_PERCENTAGE", DEFAULT_THRESHOLD_VALUES["missing_percentage"]),
            )
        ),
    )


def threshold_for_feature(thresholds: DriftThresholds, feature_name: str) -> float:
    """Return the configured threshold for a specific feature."""

    return getattr(thresholds, feature_name, thresholds.record_count)
