from __future__ import annotations

from pathlib import Path
from typing import Any


def write_records_to_postgres(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError("Postgres storage is not configured in this recovered source snapshot.")

