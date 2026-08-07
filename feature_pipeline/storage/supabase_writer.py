from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SupabaseWriteResult:
    inserted_rows: int
    skipped: bool
    message: str | None = None


def _row_key(record: dict[str, Any]) -> str:
    normalized = json.dumps(record, sort_keys=True, default=str, ensure_ascii=False)
    return sha1(normalized.encode("utf-8")).hexdigest()


def _build_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key or "",
        "Authorization": f"Bearer {settings.supabase_service_role_key or ''}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _build_rows(records: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        row = dict(record)
        row["record_key"] = _row_key({**row, "run_id": run_id})
        rows.append(row)
    return rows


def write_raw_records(records: list[dict[str, Any]], run_id: str) -> SupabaseWriteResult:
    if not settings.supabase_enabled:
        return SupabaseWriteResult(inserted_rows=0, skipped=True, message="Supabase disabled")
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return SupabaseWriteResult(inserted_rows=0, skipped=True, message="Supabase credentials missing")
    if not records:
        return SupabaseWriteResult(inserted_rows=0, skipped=True, message="No records to write")

    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.supabase_raw_table}"
    rows = _build_rows(records, run_id)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=_build_headers(), params={"on_conflict": "record_key"}, json=rows)
            response.raise_for_status()
        logger.info("Supabase raw sync complete | table=%s | rows=%s", settings.supabase_raw_table, len(rows))
        return SupabaseWriteResult(inserted_rows=len(rows), skipped=False)
    except Exception as exc:
        logger.warning("Supabase raw sync failed: %s", exc)
        return SupabaseWriteResult(inserted_rows=0, skipped=True, message=str(exc))

