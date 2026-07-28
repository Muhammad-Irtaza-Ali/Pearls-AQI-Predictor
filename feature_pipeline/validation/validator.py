from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from validation.cleaner import clean_record
from validation.schema import AirQualityRecord

logger = logging.getLogger(__name__)


def validate_record(record: dict[str, Any]) -> AirQualityRecord | None:
    cleaned = clean_record(record)
    try:
        return AirQualityRecord.model_validate(cleaned)
    except ValidationError as exc:
        logger.warning("Validation failed for %s | %s", cleaned.get("city"), exc.errors())
        return None

