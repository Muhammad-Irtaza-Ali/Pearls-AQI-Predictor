from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any

import httpx

from aqicn_client import AQICNClient
from base_client import FetchResult
from cities import City, get_cities
from config import settings
from fusion.merge_data import merge_records
from monitoring.logger import log_api_event
from standardization.standardizer import standardize_records
from validation.cleaner import deduplicate_records
from openmeteo_client import OpenMeteoClient
from openweather_client import OpenWeatherClient


@dataclass(slots=True)
class PipelineSummary:
    run_id: str
    cities_processed: int
    api_successful: int
    api_failed: int
    silver_rows: int
    gold_rows: int
    execution_time_seconds: float
    failed_requests: list[dict[str, str]]
    api_summary: dict[str, dict[str, int]]
    missing_values: dict[str, int]


@dataclass(slots=True)
class PipelineArtifacts:
    bronze_records: list[dict[str, Any]]
    silver_records: list[dict[str, Any]]
    gold_records: list[dict[str, Any]]
    summary: PipelineSummary


class AsyncIngestionPipeline:
    def __init__(self, cities: list[City] | None = None) -> None:
        self.cities = cities or get_cities()
        self.clients = [
            OpenWeatherClient(),
            OpenMeteoClient(),
            AQICNClient(),
        ]

    async def run(self) -> PipelineArtifacts:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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

        bronze_records = [
            {
                "run_id": run_id,
                "source": result.source,
                "city": result.city,
                "status": result.status,
                "response_time_ms": int(result.response_time_seconds * 1000),
                "error": result.error,
                "raw_payload": result.raw_payload,
            }
            for result in normalized_results
        ]

        source_records = [
            record
            for record in (result.record for result in normalized_results if result.record is not None)
            if record is not None
        ]
        deduplicated_records = deduplicate_records(source_records)
        standardized_records = standardize_records(deduplicated_records, run_id)
        silver_records = [record.model_dump(mode="json") for record in standardized_records]
        gold_models = merge_records(standardized_records)
        gold_records = [record.model_dump(mode="json") for record in gold_models]

        failed_requests = [
            {
                "source": result.source,
                "city": result.city,
                "error": result.error or "Unknown error",
            }
            for result in normalized_results
            if result.status == "failed"
        ]
        api_summary: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failed": 0})
        for result in normalized_results:
            api_summary[result.source][result.status if result.status == "failed" else "success"] += 1

        monitored_fields = [
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "cloud_cover",
            "rain",
            "aqi",
            "pm25",
            "pm10",
            "co",
            "no",
            "no2",
            "so2",
            "o3",
            "nh3",
        ]
        missing_values = Counter()
        for record in gold_models:
            record_dump = record.model_dump()
            for field_name in monitored_fields:
                if record_dump.get(field_name) is None:
                    missing_values[field_name] += 1

        summary = PipelineSummary(
            run_id=run_id,
            cities_processed=len(self.cities),
            api_successful=sum(1 for result in normalized_results if result.status != "failed"),
            api_failed=sum(1 for result in normalized_results if result.status == "failed"),
            silver_rows=len(silver_records),
            gold_rows=len(gold_records),
            execution_time_seconds=time.perf_counter() - started_at,
            failed_requests=failed_requests,
            api_summary=dict(api_summary),
            missing_values=dict(missing_values),
        )

        for result in normalized_results:
            log_api_event(
                city=result.city,
                api=result.source,
                status=result.status.upper(),
                response_time_ms=int(result.response_time_seconds * 1000),
                reason=result.error,
            )

        return PipelineArtifacts(
            bronze_records=bronze_records,
            silver_records=silver_records,
            gold_records=gold_records,
            summary=summary,
        )
