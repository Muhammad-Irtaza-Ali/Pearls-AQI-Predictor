from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseWriter(ABC):
    @abstractmethod
    def write(self, records: list[dict[str, Any]]) -> None:
        raise NotImplementedError

