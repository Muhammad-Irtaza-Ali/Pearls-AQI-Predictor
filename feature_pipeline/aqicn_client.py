from __future__ import annotations

from typing import Any

from base_client import BaseClient
from cities import City
from config import settings


class AQICNClient(BaseClient):
    source_name = "aqicn"

    def request_specs(self, city: City) -> list[tuple[str, str, dict[str, Any]]]:
        params: dict[str, Any] = {}
        if settings.aqicn_api_key:
            params["token"] = settings.aqicn_api_key
        url = f"https://api.waqi.info/feed/geo:{city.latitude};{city.longitude}/"
        return [("air_quality", url, params)]

    def normalize(self, city: City, payloads: dict[str, Any], response_time_seconds: float) -> dict[str, Any]:
        response = payloads.get("air_quality") or {}
        if not isinstance(response, dict) or response.get("status") not in {None, "ok"}:
            response = {}
        data = response.get("data", {}) if isinstance(response, dict) else {}
        iaqi = data.get("iaqi", {}) if isinstance(data, dict) else {}
        city_info = data.get("city", {}) if isinstance(data, dict) else {}
        return {
            "timestamp": data.get("time", {}).get("s") or self.utc_now(),
            "city": city_info.get("name") or city.name,
            "country": city.country,
            "latitude": city.latitude,
            "longitude": city.longitude,
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "wind_speed": None,
            "wind_direction": None,
            "cloud_cover": None,
            "rain": None,
            "aqi": data.get("aqi"),
            "pm25": iaqi.get("pm25", {}).get("v"),
            "pm10": iaqi.get("pm10", {}).get("v"),
            "co": iaqi.get("co", {}).get("v"),
            "no": iaqi.get("no", {}).get("v"),
            "no2": iaqi.get("no2", {}).get("v"),
            "so2": iaqi.get("so2", {}).get("v"),
            "o3": iaqi.get("o3", {}).get("v"),
            "nh3": iaqi.get("nh3", {}).get("v"),
            "source": self.source_name,
            "status": "success",
            "response_time_seconds": response_time_seconds,
            "raw_payload": self.json_dumps(payloads),
        }
