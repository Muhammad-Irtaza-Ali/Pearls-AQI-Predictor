from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from statistics import mean
from typing import Any

from base_client import BaseClient
from cities import City
from config import settings

logger = logging.getLogger(__name__)


class OpenWeatherClient(BaseClient):
    source_name = "openweather"
    supports_historical = True

    def request_specs(
        self,
        city: City,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        weather_params: dict[str, Any] = {"lat": city.latitude, "lon": city.longitude, "units": "metric"}
        pollution_params: dict[str, Any] = {"lat": city.latitude, "lon": city.longitude}
        if settings.openweather_api_key:
            weather_params["appid"] = settings.openweather_api_key
            pollution_params["appid"] = settings.openweather_api_key

        if start_date and end_date:
            start_timestamp = int(datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            end_timestamp = int(datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc).timestamp())
            request_specs: list[tuple[str, str, dict[str, Any]]] = []
            if settings.backfill_openweather_history_weather:
                weather_location_id = getattr(city, "openweather_location_id", None)
                if weather_location_id:
                    weather_params = {"id": weather_location_id, "start": start_timestamp, "end": end_timestamp}
                    if settings.openweather_api_key:
                        weather_params["appid"] = settings.openweather_api_key
                    request_specs.append(
                        ("weather", "https://history.openweathermap.org/data/3.0/history/result", weather_params)
                    )
                else:
                    logger.warning("Skipping OpenWeather historical weather for %s because no location ID is configured", city.name)
            else:
                logger.info("Skipping OpenWeather historical weather for %s because backfill weather history is disabled", city.name)
            pollution_params.update({"start": start_timestamp, "end": end_timestamp})
            request_specs.append(("air_quality", "https://api.openweathermap.org/data/2.5/air_pollution/history", pollution_params))
            return request_specs

        return [
            ("weather", "https://api.openweathermap.org/data/2.5/weather", weather_params),
            ("air_quality", "https://api.openweathermap.org/data/2.5/air_pollution", pollution_params),
        ]

    @staticmethod
    def _aggregate_numeric(values: list[float | int | None]) -> float | None:
        filtered = [float(value) for value in values if value is not None]
        return round(mean(filtered), 4) if filtered else None

    @staticmethod
    def _first_timestamp_from_history(payload: dict[str, Any], fallback: str | None = None) -> str:
        weather_list = payload.get("list") if isinstance(payload, dict) else None
        if isinstance(weather_list, list) and weather_list:
            first_item = weather_list[0]
            if isinstance(first_item, dict) and first_item.get("dt") is not None:
                return datetime.fromtimestamp(int(first_item["dt"]), tz=timezone.utc).isoformat()
        return fallback or datetime.now(timezone.utc).isoformat()

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
            weather_items = weather_data.get("list") if isinstance(weather_data, dict) else []
            weather_items = weather_items if isinstance(weather_items, list) else []
            pollution_items = air_quality_data.get("list") if isinstance(air_quality_data, dict) else []
            weather_main_values = [item.get("main", {}).get("temp") for item in weather_items if isinstance(item, dict)]
            humidity_values = [item.get("main", {}).get("humidity") for item in weather_items if isinstance(item, dict)]
            pressure_values = [item.get("main", {}).get("pressure") for item in weather_items if isinstance(item, dict)]
            wind_speed_values = [item.get("wind", {}).get("speed") for item in weather_items if isinstance(item, dict)]
            wind_direction_values = [item.get("wind", {}).get("deg") for item in weather_items if isinstance(item, dict)]
            cloud_cover_values = [item.get("clouds", {}).get("all") for item in weather_items if isinstance(item, dict)]
            rain_values = [item.get("rain", {}).get("1h") or item.get("rain", {}).get("3h") for item in weather_items if isinstance(item, dict)]
            aqi_values = [(item.get("main", {}) or {}).get("aqi") for item in pollution_items if isinstance(item, dict)]
            components = [item.get("components", {}) for item in pollution_items if isinstance(item, dict)]
            return {
                "timestamp": self._first_timestamp_from_history(weather_data, fallback=start_date.isoformat() if start_date else None),
                "data_date": start_date.isoformat() if start_date else None,
                "city": city.name,
                "country": city.country,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "temperature": self._aggregate_numeric(weather_main_values),
                "humidity": self._aggregate_numeric(humidity_values),
                "pressure": self._aggregate_numeric(pressure_values),
                "wind_speed": self._aggregate_numeric(wind_speed_values),
                "wind_direction": self._aggregate_numeric(wind_direction_values),
                "cloud_cover": self._aggregate_numeric(cloud_cover_values),
                "rain": self._aggregate_numeric(rain_values),
                "aqi": self._aggregate_numeric(aqi_values),
                "pm25": self._aggregate_numeric([component.get("pm2_5") for component in components]),
                "pm10": self._aggregate_numeric([component.get("pm10") for component in components]),
                "co": self._aggregate_numeric([component.get("co") for component in components]),
                "no": self._aggregate_numeric([component.get("no") for component in components]),
                "no2": self._aggregate_numeric([component.get("no2") for component in components]),
                "so2": self._aggregate_numeric([component.get("so2") for component in components]),
                "o3": self._aggregate_numeric([component.get("o3") for component in components]),
                "nh3": self._aggregate_numeric([component.get("nh3") for component in components]),
                "source": self.source_name,
                "status": "success",
                "response_time_seconds": response_time_seconds,
                "raw_payload": self.json_dumps(payloads),
            }

        weather_main = weather_data.get("main", {}) if isinstance(weather_data, dict) else {}
        weather_wind = weather_data.get("wind", {}) if isinstance(weather_data, dict) else {}
        weather_clouds = weather_data.get("clouds", {}) if isinstance(weather_data, dict) else {}
        weather_rain = weather_data.get("rain", {}) if isinstance(weather_data, dict) else {}
        pollution_item = {}
        if isinstance(air_quality_data, dict):
            pollution_list = air_quality_data.get("list") or []
            if pollution_list:
                pollution_item = pollution_list[0]
        pollution_components = pollution_item.get("components", {}) if isinstance(pollution_item, dict) else {}
        return {
            "timestamp": self.utc_now(),
            "data_date": None,
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

