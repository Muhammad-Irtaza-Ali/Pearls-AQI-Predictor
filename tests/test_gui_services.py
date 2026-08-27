from __future__ import annotations

import pandas as pd

from gui.services import aqi_category, current_overview


def test_aqi_category_maps_expected_bands() -> None:
    assert aqi_category(25) == "Good"
    assert aqi_category(75) == "Moderate"
    assert aqi_category(125) == "Unhealthy for Sensitive Groups"
    assert aqi_category(175) == "Unhealthy"
    assert aqi_category(250) == "Very Unhealthy"
    assert aqi_category(350) == "Hazardous"
    assert aqi_category(None) == "Not available"


def test_current_overview_uses_latest_city_snapshot() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2026-08-01T00:00:00Z",
                "city": "Karachi",
                "aqi": 120,
            },
            {
                "timestamp": "2026-08-01T03:00:00Z",
                "city": "Karachi",
                "aqi": 140,
            },
            {
                "timestamp": "2026-08-01T01:00:00Z",
                "city": "Lahore",
                "aqi": 80,
            },
        ]
    )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)

    overview = current_overview(frame)

    assert overview["current_aqi"] == 140.0
    assert overview["aqi_category"] == "Unhealthy for Sensitive Groups"
    assert overview["highest_city"] == "Karachi"
    assert overview["lowest_city"] == "Lahore"
    assert overview["active_cities"] == 2
