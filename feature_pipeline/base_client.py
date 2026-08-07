from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import logging
import time
from typing import Any

import httpx

from config import settings
from cities import City

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FetchResult:
    source: str
    endpoint: list[str]
    city: str
    record: dict[str, Any] | None
    raw_payload: dict[str, Any]
    status: str
    response_time_seconds: float
    error: str | None = None


class BaseClient(ABC):
    source_name: str
    supports_historical: bool = False

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.provider_concurrency)

    @abstractmethod
    def request_specs(
        self,
        city: City,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        raise NotImplementedError

    @abstractmethod
    def normalize(
        self,
        city: City,
        payloads: dict[str, Any],
        response_time_seconds: float,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def fetch(
        self,
        http_client: httpx.AsyncClient,
        city: City,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FetchResult:
        async with self._semaphore:
            logger.info(
                "Starting %s for %s%s",
                self.source_name,
                city.name,
                f" [{start_date} -> {end_date}]" if start_date or end_date else "",
            )
            started_at = time.perf_counter()
            collected_payloads: dict[str, Any] = {}
            errors: list[str] = []
            endpoints: list[str] = []

            for label, url, params in self.request_specs(city, start_date=start_date, end_date=end_date):
                endpoints.append(url)
                payload, error = await self._fetch_json(http_client, url, params)
                collected_payloads[label] = payload
                if error:
                    errors.append(f"{label}: {error}")

            response_time_seconds = time.perf_counter() - started_at
            try:
                record = self.normalize(
                    city,
                    collected_payloads,
                    response_time_seconds,
                    start_date=start_date,
                    end_date=end_date,
                )
                status = "partial" if errors else "success"
                logger.info(
                    "Finished %s for %s in %.2fs with status=%s",
                    self.source_name,
                    city.name,
                    response_time_seconds,
                    status,
                )
                return FetchResult(
                    source=self.source_name,
                    endpoint=endpoints,
                    city=city.name,
                    record=record,
                    raw_payload=collected_payloads,
                    status=status,
                    response_time_seconds=response_time_seconds,
                    error="; ".join(errors) if errors else None,
                )
            except Exception as exc:
                logger.exception("Normalization failed for %s in %s", self.source_name, city.name)
                return FetchResult(
                    source=self.source_name,
                    endpoint=endpoints,
                    city=city.name,
                    record=None,
                    raw_payload=collected_payloads,
                    status="failed",
                    response_time_seconds=response_time_seconds,
                    error=str(exc),
                )

    async def _fetch_json(
        self,
        http_client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        last_error: Exception | None = None
        for attempt in range(settings.retry_count + 1):
            try:
                response = await http_client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json(), None
            except Exception as exc:
                last_error = exc
                if attempt < settings.retry_count:
                    wait_for = settings.retry_backoff_seconds * (2**attempt)
                    await asyncio.sleep(wait_for)
                    continue
                logger.warning("Request failed for %s after %s attempts: %s", url, attempt + 1, exc)
                return None, str(exc)

        return None, str(last_error) if last_error else "Unknown error"

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def json_dumps(value: Any) -> str:
        return json.dumps(value, default=str, ensure_ascii=False)
