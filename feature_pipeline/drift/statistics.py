from __future__ import annotations

from typing import Any

import pandas as pd


def compute_column_statistics(current: pd.Series, previous: pd.Series) -> dict[str, Any]:
    return {
        "current_mean": current.mean(),
        "previous_mean": previous.mean(),
        "current_median": current.median(),
        "previous_median": previous.median(),
        "current_min": current.min(),
        "previous_min": previous.min(),
        "current_max": current.max(),
        "previous_max": previous.max(),
        "current_std": current.std(),
        "previous_std": previous.std(),
        "current_missing_count": int(current.isna().sum()),
        "previous_missing_count": int(previous.isna().sum()),
        "current_missing_percentage": float(current.isna().mean() * 100),
        "previous_missing_percentage": float(previous.isna().mean() * 100),
        "current_unique_values": int(current.nunique(dropna=True)),
        "previous_unique_values": int(previous.nunique(dropna=True)),
    }

