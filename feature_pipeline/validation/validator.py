from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from validation.schema import AirQualityRecord

logger = logging.getLogger(__name__)


def validate_record(record: dict[str, Any]) -> AirQualityRecord | None:
    try:
        return AirQualityRecord.model_validate(record)
    except ValidationError as exc:
        logger.warning("Validation failed for %s | %s", record.get("city", "unknown"), exc.errors())
        return None

