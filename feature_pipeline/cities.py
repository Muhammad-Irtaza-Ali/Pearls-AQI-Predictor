from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class City:
    name: str
    latitude: float
    longitude: float
    country: str
    openweather_location_id: str | None = None


def _city_key(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.upper()).strip("_")


def _openweather_location_id(city_name: str) -> str | None:
    return settings.openweather_location_ids.get(city_name) or settings.openweather_location_ids.get(_city_key(city_name))


CITIES: tuple[City, ...] = (
    City("Karachi", 24.8607, 67.0011, "PK", _openweather_location_id("Karachi")),
    City("Hyderabad", 25.3960, 68.3578, "PK", _openweather_location_id("Hyderabad")),
    City("Sukkur", 27.7052, 68.8484, "PK", _openweather_location_id("Sukkur")),
    City("Khairpur Mir's", 27.5295, 68.7592, "PK", _openweather_location_id("Khairpur Mir's")),
    City("Larkana", 27.5598, 68.2120, "PK", _openweather_location_id("Larkana")),
    City("Gambat", 27.3517, 68.5247, "PK", _openweather_location_id("Gambat")),
    City("Lahore", 31.5204, 74.3587, "PK", _openweather_location_id("Lahore")),
)


def get_cities() -> list[City]:
    return list(CITIES)
