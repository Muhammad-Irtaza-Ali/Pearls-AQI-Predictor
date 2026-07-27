from __future__ import annotations

import asyncio

import httpx

from cities import get_cities
from openweather_client import OpenWeatherClient


def fetch_pollution(city_name: str | None = None) -> dict:
    city = next((item for item in get_cities() if item.name == city_name), get_cities()[0])

    async def _run() -> dict:
        async with httpx.AsyncClient() as http_client:
            result = await OpenWeatherClient().fetch(http_client, city)
            return result.record or {}

    return asyncio.run(_run())


if __name__ == "__main__":
    print(fetch_pollution())
