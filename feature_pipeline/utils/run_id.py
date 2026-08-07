from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def generate_run_id() -> str:
    return f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"

