from __future__ import annotations

from typing import Any

from storage.writer import BaseWriter


class PostgresWriter(BaseWriter):
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._enabled = False

    def write(self, records: list[dict[str, Any]]) -> None:
        if not self._enabled:
            raise RuntimeError("PostgresWriter is not enabled in this CSV-only setup.")

