from __future__ import annotations

from typing import Any

from base_client import BaseClient
from cities import City
from config import settings


class OpenWeatherClient(BaseClient):
    source_name = "openweather"

    def request_specs(self, city: City) -> list[tuple[str, str, dict[str, Any]]]:
        weather_params: dict[str, Any] = {
            "lat": city.latitude,
            "lon": city.longitude,
            "units": "metric",
        }
        pollution_params: dict[str, Any] = {
            "lat": city.latitude,
            "lon": city.longitude,
        }
        if settings.openweather_api_key:
            weather_params["appid"] = settings.openweather_api_key
            pollution_params["appid"] = settings.openweather_api_key
        return [
            ("weather", "https://api.openweathermap.org/data/2.5/weather", weather_params),
            ("air_quality", "https://api.openweathermap.org/data/2.5/air_pollution", pollution_params),
        ]

    def normalize(self, city: City, payloads: dict[str, Any], response_time_seconds: float) -> dict[str, Any]:
        weather_data = payloads.get("weather") or {}
        air_quality_data = payloads.get("air_quality") or {}
        weather_main = weather_data.get("main", {})
        weather_wind = weather_data.get("wind", {})
        weather_clouds = weather_data.get("clouds", {})
        weather_rain = weather_data.get("rain", {})
        pollution_item = {}
        if isinstance(air_quality_data, dict):
            pollution_list = air_quality_data.get("list") or []
            if pollution_list:
                pollution_item = pollution_list[0]
        pollution_components = pollution_item.get("components", {}) if isinstance(pollution_item, dict) else {}
        return {
            "timestamp": self.utc_now(),
            "city": city.name,
            "country": city.country,
            "latitude": city.latitude,
            "longitude": city.longitude,
            "temperature": weather_main.get("temp"),
            "humidity": weather_main.get("humidity"),
            "pressure": weather_main.get("pressure"),
            "wind_speed": weather_wind.get("speed"),
            "wind_direction": weather_wind.get("deg"),
            "cloud_cover": weather_clouds.get("all"),
            "rain": weather_rain.get("1h") or weather_rain.get("3h"),
            "aqi": (pollution_item.get("main") or {}).get("aqi") if isinstance(pollution_item, dict) else None,
            "pm25": pollution_components.get("pm2_5"),
            "pm10": pollution_components.get("pm10"),
            "co": pollution_components.get("co"),
            "no": pollution_components.get("no"),
            "no2": pollution_components.get("no2"),
            "so2": pollution_components.get("so2"),
            "o3": pollution_components.get("o3"),
            "nh3": pollution_components.get("nh3"),
            "source": self.source_name,
            "status": "success",
            "response_time_seconds": response_time_seconds,
            "raw_payload": self.json_dumps(payloads),
        }
