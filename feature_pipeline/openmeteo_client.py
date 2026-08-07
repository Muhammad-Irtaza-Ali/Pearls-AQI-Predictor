from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Any

from base_client import BaseClient
from cities import City


class OpenMeteoClient(BaseClient):
    source_name = "openmeteo"
    supports_historical = True

    def request_specs(
        self,
        city: City,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        base_params = {"latitude": city.latitude, "longitude": city.longitude, "timezone": "UTC"}
        if start_date and end_date:
            return [
                (
                    "weather",
                    "https://archive-api.open-meteo.com/v1/archive",
                    {
                        **base_params,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "hourly": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,cloud_cover,rain",
                    },
                ),
                (
                    "air_quality",
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    {
                        **base_params,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,sulphur_dioxide,ammonia,us_aqi",
                    },
                ),
            ]
        return [
            (
                "weather",
                "https://api.open-meteo.com/v1/forecast",
                {
                    **base_params,
                    "current": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m,cloud_cover,rain",
                },
            ),
            (
                "air_quality",
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                {**base_params, "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,sulphur_dioxide,ammonia,us_aqi"},
            ),
        ]

    @staticmethod
    def _hourly_value(payload: dict[str, Any], field: str) -> Any:
        hourly = payload.get("hourly", {}) if isinstance(payload, dict) else {}
        values = hourly.get(field, []) if isinstance(hourly, dict) else []
        return values[0] if values else None

    @staticmethod
    def _mean_hourly_value(payload: dict[str, Any], field: str) -> float | None:
        hourly = payload.get("hourly", {}) if isinstance(payload, dict) else {}
        values = hourly.get(field, []) if isinstance(hourly, dict) else []
        filtered = [float(value) for value in values if value is not None]
        return round(mean(filtered), 4) if filtered else None

    def normalize(
        self,
        city: City,
        payloads: dict[str, Any],
        response_time_seconds: float,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        weather_data = payloads.get("weather") or {}
        air_quality_data = payloads.get("air_quality") or {}
        historical_mode = bool(start_date and end_date)
        if historical_mode:
            historical_aqi = self._mean_hourly_value(air_quality_data, "us_aqi")
            return {
                "timestamp": start_date.isoformat() if start_date else self.utc_now(),
                "data_date": start_date.isoformat() if start_date else None,
                "city": city.name,
                "country": city.country,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "temperature": self._mean_hourly_value(weather_data, "temperature_2m"),
                "humidity": self._mean_hourly_value(weather_data, "relative_humidity_2m"),
                "pressure": self._mean_hourly_value(weather_data, "pressure_msl"),
                "wind_speed": self._mean_hourly_value(weather_data, "wind_speed_10m"),
                "wind_direction": self._mean_hourly_value(weather_data, "wind_direction_10m"),
                "cloud_cover": self._mean_hourly_value(weather_data, "cloud_cover"),
                "rain": self._mean_hourly_value(weather_data, "rain"),
                "aqi": int(round(historical_aqi)) if historical_aqi is not None else None,
                "pm25": self._mean_hourly_value(air_quality_data, "pm2_5"),
                "pm10": self._mean_hourly_value(air_quality_data, "pm10"),
                "co": self._mean_hourly_value(air_quality_data, "carbon_monoxide"),
                "no": None,
                "no2": self._mean_hourly_value(air_quality_data, "nitrogen_dioxide"),
                "so2": self._mean_hourly_value(air_quality_data, "sulphur_dioxide"),
                "o3": self._mean_hourly_value(air_quality_data, "ozone"),
                "nh3": self._mean_hourly_value(air_quality_data, "ammonia"),
                "source": self.source_name,
                "status": "success",
                "response_time_seconds": response_time_seconds,
                "raw_payload": self.json_dumps(payloads),
            }
        weather_current = weather_data.get("current", {}) if isinstance(weather_data, dict) else {}
        return {
            "timestamp": weather_current.get("time") or self._hourly_value(air_quality_data, "time") or self.utc_now(),
            "data_date": None,
            "city": city.name,
            "country": city.country,
            "latitude": city.latitude,
            "longitude": city.longitude,
            "temperature": weather_current.get("temperature_2m"),
            "humidity": weather_current.get("relative_humidity_2m"),
            "pressure": weather_current.get("pressure_msl"),
            "wind_speed": weather_current.get("wind_speed_10m"),
            "wind_direction": weather_current.get("wind_direction_10m"),
            "cloud_cover": weather_current.get("cloud_cover"),
            "rain": weather_current.get("rain"),
            "aqi": self._hourly_value(air_quality_data, "us_aqi"),
            "pm25": self._hourly_value(air_quality_data, "pm2_5"),
            "pm10": self._hourly_value(air_quality_data, "pm10"),
            "co": self._hourly_value(air_quality_data, "carbon_monoxide"),
            "no": None,
            "no2": self._hourly_value(air_quality_data, "nitrogen_dioxide"),
            "so2": self._hourly_value(air_quality_data, "sulphur_dioxide"),
            "o3": self._hourly_value(air_quality_data, "ozone"),
            "nh3": self._hourly_value(air_quality_data, "ammonia"),
            "source": self.source_name,
            "status": "success",
            "response_time_seconds": response_time_seconds,
            "raw_payload": self.json_dumps(payloads),
        }

