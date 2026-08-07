from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging
import time
from typing import Any

import httpx

from aqicn_client import AQICNClient
from base_client import BaseClient, FetchResult
from cities import City, get_cities
from config import API_VERSIONS, PIPELINE_VERSION, settings
from fusion.merge_data import merge_records
from monitoring.logger import log_api_event
from standardization.standardizer import standardize_records
from utils.run_id import generate_run_id
from validation.cleaner import deduplicate_records

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineSummary:
    run_id: str
    cities_processed: int
    total_api_calls: int
    successful_calls: int
    failed_calls: int
    rows_processed: int
    rows_skipped: int
    invalid_records: int
    duplicates_removed: int
    silver_rows: int
    gold_rows: int
    execution_time_seconds: float
    failed_requests: list[dict[str, str]]
    api_summary: dict[str, dict[str, int]]
    missing_values: dict[str, int]

    @property
    def api_successful(self) -> int:
        return self.successful_calls

    @property
    def api_failed(self) -> int:
        return self.failed_calls


@dataclass(slots=True)
class PipelineArtifacts:
    bronze_records: list[dict[str, Any]]
    silver_records: list[dict[str, Any]]
    gold_records: list[dict[str, Any]]
    summary: PipelineSummary


class AsyncIngestionPipeline:
    def __init__(self, cities: list[City] | None = None, clients: list[BaseClient] | None = None) -> None:
        self.cities = cities or get_cities()
        if clients is None:
            from openmeteo_client import OpenMeteoClient
            from openweather_client import OpenWeatherClient

            self.clients = [OpenWeatherClient(), OpenMeteoClient(), AQICNClient()]
        else:
            self.clients = clients

    @staticmethod
    def _date_range(start_date: date, end_date: date) -> list[date]:
        current_date = start_date
        dates: list[date] = []
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        return dates

    @staticmethod
    def _result_to_bronze_record(result: FetchResult, run_id: str, data_date: date | None) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "source": result.source,
            "endpoint": result.endpoint,
            "city": result.city,
            "status": result.status,
            "pipeline_version": PIPELINE_VERSION,
            "api_version": API_VERSIONS.get(result.source),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": int(result.response_time_seconds * 1000),
            "response_time_seconds": result.response_time_seconds,
            "error": result.error,
            "data_date": data_date.isoformat() if data_date else None,
            "raw_payload": result.raw_payload,
        }

    async def _collect_current(self, run_id: str) -> tuple[list[FetchResult], list[dict[str, Any]]]:
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        timeout = httpx.Timeout(settings.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http_client:
            tasks = [client.fetch(http_client, city) for city in self.cities for client in self.clients]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        normalized_results = self._normalize_results(results)
        bronze_records = [self._result_to_bronze_record(result, run_id, None) for result in normalized_results]
        return normalized_results, bronze_records

    async def _collect_historical(self, run_id: str, start_date: date, end_date: date) -> tuple[list[FetchResult], list[dict[str, Any]]]:
        selected_clients = [client for client in self.clients if getattr(client, "supports_historical", False)]
        skipped_clients = [client.source_name for client in self.clients if client not in selected_clients]
        for skipped_client in skipped_clients:
            logger.warning("Skipping unsupported historical API: %s", skipped_client)
        if not selected_clients:
            logger.warning("No historical APIs are available for backfill.")
            return [], []

        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        timeout = httpx.Timeout(settings.timeout_seconds)
        bronze_records: list[dict[str, Any]] = []
        collected_results: list[FetchResult] = []
        dates = self._date_range(start_date, end_date)
        total_days = len(dates)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http_client:
            for index, current_day in enumerate(dates, start=1):
                logger.info("Historical collection progress %s/%s | date=%s", index, total_days, current_day)
                tasks = [
                    client.fetch(http_client, city, start_date=current_day, end_date=current_day)
                    for city in self.cities
                    for client in selected_clients
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                normalized_results = self._normalize_results(results)
                collected_results.extend(normalized_results)
                bronze_records.extend(self._result_to_bronze_record(result, run_id, current_day) for result in normalized_results)
        return collected_results, bronze_records

    @staticmethod
    def _normalize_results(results: list[Any]) -> list[FetchResult]:
        normalized_results: list[FetchResult] = []
        for result in results:
            if isinstance(result, FetchResult):
                normalized_results.append(result)
            else:
                normalized_results.append(FetchResult(source="unknown", endpoint=[], city="unknown", record=None, raw_payload={}, status="failed", response_time_seconds=0.0, error=str(result)))
        return normalized_results

    @staticmethod
    def _build_api_summary(results: list[FetchResult]) -> dict[str, dict[str, int]]:
        api_summary: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failed": 0})
        for result in results:
            bucket = "success" if result.status == "success" else "failed"
            api_summary[result.source][bucket] += 1
        return dict(api_summary)

    @staticmethod
    def _build_failed_requests(results: list[FetchResult]) -> list[dict[str, str]]:
        return [{"source": result.source, "city": result.city, "error": result.error or "Unknown error"} for result in results if result.status != "success"]

    @staticmethod
    def _missing_values(records: list[Any]) -> dict[str, int]:
        monitored_fields = ["temperature","humidity","pressure","wind_speed","wind_direction","cloud_cover","rain","aqi","pm25","pm10","co","no","no2","so2","o3","nh3"]
        missing_values = Counter()
        for record in records:
            record_dump = record.model_dump()
            for field_name in monitored_fields:
                if record_dump.get(field_name) is None:
                    missing_values[field_name] += 1
        return dict(missing_values)

    async def run(self, *, start_date: date | None = None, end_date: date | None = None) -> PipelineArtifacts:
        run_id = generate_run_id()
        started_at = time.perf_counter()
        logger.info("Pipeline Started | run_id=%s", run_id)

        if start_date or end_date:
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required for historical runs.")
            if start_date > end_date:
                raise ValueError("start_date must be earlier than or equal to end_date.")
            collected_results, bronze_records = await self._collect_historical(run_id, start_date, end_date)
        else:
            collected_results, bronze_records = await self._collect_current(run_id)

        source_records = [record for record in (result.record for result in collected_results if result.record is not None) if record is not None]
        deduplicated_records = deduplicate_records(source_records)
        standardized_records = standardize_records(deduplicated_records, run_id)
        silver_records = [record.model_dump(mode="json") for record in standardized_records]
        gold_models = merge_records(standardized_records)
        gold_records = [record.model_dump(mode="json") for record in gold_models]

        invalid_records = len(deduplicated_records) - len(standardized_records)
        duplicates_removed = len(source_records) - len(deduplicated_records)
        rows_processed = len(standardized_records)
        rows_skipped = max(0, len(source_records) - len(standardized_records))
        failed_requests = self._build_failed_requests(collected_results)
        api_summary = self._build_api_summary(collected_results)
        missing_values = self._missing_values(gold_models)
        execution_time_seconds = time.perf_counter() - started_at

        summary = PipelineSummary(
            run_id=run_id,
            cities_processed=len(self.cities),
            total_api_calls=len(collected_results),
            successful_calls=sum(1 for result in collected_results if result.status == "success"),
            failed_calls=sum(1 for result in collected_results if result.status != "success"),
            rows_processed=rows_processed,
            rows_skipped=rows_skipped,
            invalid_records=invalid_records,
            duplicates_removed=duplicates_removed,
            silver_rows=len(silver_records),
            gold_rows=len(gold_records),
            execution_time_seconds=execution_time_seconds,
            failed_requests=failed_requests,
            api_summary=api_summary,
            missing_values=missing_values,
        )

        for result in collected_results:
            log_api_event(city=result.city, api=result.source, status=result.status.upper(), response_time_ms=int(result.response_time_seconds * 1000), reason=result.error)

        logger.info(
            "Pipeline Finished | run_id=%s | execution_time=%.2fs | calls=%s | success=%s | failed=%s",
            run_id,
            execution_time_seconds,
            summary.total_api_calls,
            summary.successful_calls,
            summary.failed_calls,
        )

        return PipelineArtifacts(bronze_records=bronze_records, silver_records=silver_records, gold_records=gold_records, summary=summary)

