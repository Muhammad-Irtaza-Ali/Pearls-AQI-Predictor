from __future__ import annotations

from datetime import date
from typing import Any

from base_client import BaseClient
from cities import City
from config import settings


class AQICNClient(BaseClient):
    source_name = "aqicn"
    supports_historical = False

    def request_specs(
        self,
        city: City,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        if not settings.aqicn_api_key:
            return []
        return [("aqi", f"https://api.waqi.info/feed/{city.name}/", {"token": settings.aqicn_api_key})]

    def normalize(
        self,
        city: City,
        payloads: dict[str, Any],
        response_time_seconds: float,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        payload = payloads.get("aqi") or {}
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        iaqi = data.get("iaqi", {}) if isinstance(data, dict) else {}
        return {
            "timestamp": self.utc_now(),
            "data_date": None,
            "city": city.name,
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
            "pm25": iaqi.get("pm25", {}).get("v") if isinstance(iaqi.get("pm25"), dict) else None,
            "pm10": None,
            "co": iaqi.get("co", {}).get("v") if isinstance(iaqi.get("co"), dict) else None,
            "no": iaqi.get("no", {}).get("v") if isinstance(iaqi.get("no"), dict) else None,
            "no2": iaqi.get("no2", {}).get("v") if isinstance(iaqi.get("no2"), dict) else None,
            "so2": iaqi.get("so2", {}).get("v") if isinstance(iaqi.get("so2"), dict) else None,
            "o3": iaqi.get("o3", {}).get("v") if isinstance(iaqi.get("o3"), dict) else None,
            "nh3": iaqi.get("nh3", {}).get("v") if isinstance(iaqi.get("nh3"), dict) else None,
            "source": self.source_name,
            "status": "success" if payload else "failed",
            "response_time_seconds": response_time_seconds,
            "raw_payload": self.json_dumps(payloads),
        }

