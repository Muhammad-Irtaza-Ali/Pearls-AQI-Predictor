from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    name: str
    latitude: float
    longitude: float
    country: str


CITIES: tuple[City, ...] = (
    City("Karachi", 24.8607, 67.0011, "PK"),
    City("Hyderabad", 25.3960, 68.3578, "PK"),
    City("Sukkur", 27.7052, 68.8484, "PK"),
    City("Khairpur Mir's", 27.5295, 68.7592, "PK"),
    City("Larkana", 27.5598, 68.2120, "PK"),
    City("Gambat", 27.3517, 68.5247, "PK"),
    City("Lahore", 31.5204, 74.3587, "PK"),
)


def get_cities() -> list[City]:
    return list(CITIES)
