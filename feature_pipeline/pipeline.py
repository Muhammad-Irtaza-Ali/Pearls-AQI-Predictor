from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Any

import httpx

from aqicn_client import AQICNClient
from base_client import FetchResult
from cities import City, get_cities
from config import settings
from openmeteo_client import OpenMeteoClient
from openweather_client import OpenWeatherClient


@dataclass(slots=True)
class PipelineSummary:
    cities_processed: int
    api_successful: int
    api_failed: int
    rows_inserted: int
    execution_time_seconds: float
    failed_requests: list[dict[str, str]]


class AsyncIngestionPipeline:
    def __init__(self, cities: list[City] | None = None) -> None:
        self.cities = cities or get_cities()
        self.clients = [
            OpenWeatherClient(),
            OpenMeteoClient(),
            AQICNClient(),
        ]

    async def run(self) -> tuple[list[dict[str, Any]], PipelineSummary]:
        started_at = time.perf_counter()
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        timeout = httpx.Timeout(settings.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http_client:
            tasks = [
                client.fetch(http_client, city)
                for city in self.cities
                for client in self.clients
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        normalized_results: list[FetchResult] = []
        for result in results:
            if isinstance(result, FetchResult):
                normalized_results.append(result)
            else:
                normalized_results.append(
                    FetchResult(
                        source="unknown",
                        city="unknown",
                        record=None,
                        raw_payload={},
                        status="failed",
                        response_time_seconds=0.0,
                        error=str(result),
                    )
                )

        records = [result.record for result in normalized_results if result.record]
        failed_requests = [
            {
                "source": result.source,
                "city": result.city,
                "error": result.error or "Unknown error",
            }
            for result in normalized_results
            if result.status == "failed"
        ]
        summary = PipelineSummary(
            cities_processed=len(self.cities),
            api_successful=sum(1 for result in normalized_results if result.status != "failed"),
            api_failed=sum(1 for result in normalized_results if result.status == "failed"),
            rows_inserted=len(records),
            execution_time_seconds=time.perf_counter() - started_at,
            failed_requests=failed_requests,
        )
        return records, summary
