from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from storage.writer import BaseWriter


class CSVWriter(BaseWriter):
    def __init__(self, output_path: str) -> None:
        self.output_path = output_path

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str, ensure_ascii=False)
        return value

    def write(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        normalized_records = [
            {key: self._normalize_value(value) for key, value in record.items()}
            for record in records
        ]
        frame = pd.DataFrame(normalized_records)
        write_header = not os.path.exists(self.output_path)
        frame.to_csv(self.output_path, mode="a" if not write_header else "w", header=write_header, index=False)

