from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

from gui.components import render_kpis, render_page_header, render_section_title
from gui.services import EVALUATION_SUMMARY_PATH, aqi_category, build_city_summaries, current_overview, load_dataset, load_json_report


render_page_header(
    "10 Pearls AQI Predictor",
    "Environmental intelligence dashboard for AQI monitoring, prediction, and model health.",
    eyebrow="AI-powered environmental monitoring platform",
)

frame = load_dataset()
overview = current_overview(frame)
summaries = build_city_summaries(frame)
evaluation_report = load_json_report(EVALUATION_SUMMARY_PATH)

current_aqi_value = overview.get("current_aqi")
average_aqi_value = overview.get("average_aqi")
render_kpis(
    [
        ("Current AQI", f"{current_aqi_value:.2f}" if current_aqi_value is not None else "Not available", "Latest city snapshot"),
        ("AQI category", overview.get("aqi_category", "Not available"), "AQI health band"),
        ("Average AQI", f"{average_aqi_value:.2f}" if average_aqi_value is not None else "Not available", "Across all active cities"),
        ("Active cities", f"{overview.get('active_cities', 0)}", "Cities in the ML-ready set"),
    ]
)

st.space("small")
render_kpis(
    [
        ("Highest AQI city", overview.get("highest_city", "Not available"), "Current highest city"),
        ("Lowest AQI city", overview.get("lowest_city", "Not available"), "Current lowest city"),
        ("Last data update", overview.get("last_update", "Not available"), "Latest record timestamp"),
        ("Model R²", f"{float(evaluation_report.get('best_r2')):.3f}" if evaluation_report.get("best_r2") is not None else "Not available", "Regression quality score"),
    ]
)

st.space("small")
render_section_title("System overview", "Current system state, city comparison, and live dataset snapshot.")

col1, col2 = st.columns([1.2, 1], vertical_alignment="top")
with col1:
    with st.container(border=True):
        st.subheader("AQI trend")
        if frame.empty:
            st.info("No dataset available.")
        else:
            trend = frame.copy()
            if "timestamp" in trend.columns:
                trend["date"] = trend["timestamp"].dt.date
                daily_aqi = trend.groupby("date", as_index=False)["aqi"].mean()
                st.line_chart(daily_aqi.set_index("date"), width="stretch", height=320)
            else:
                st.bar_chart(frame.groupby("city", as_index=False)["aqi"].mean(), x="city", y="aqi", width="stretch", height=320)
with col2:
    with st.container(border=True):
        st.subheader("City comparison")
        if frame.empty:
            st.info("No city comparison available.")
        else:
            city_aqi = frame.groupby("city", as_index=False)["aqi"].mean().sort_values("aqi", ascending=False)
            st.bar_chart(city_aqi, x="city", y="aqi", width="stretch", height=320)

with st.container(border=True):
    st.subheader("City snapshots")
    if summaries:
        snapshot_df = pd.DataFrame([asdict(summary) for summary in summaries])
        st.dataframe(snapshot_df[["city", "rows", "latest_aqi", "average_aqi", "latest_timestamp"]], hide_index=True, width="stretch")
    else:
        st.info("No city data available.")

with st.container(border=True):
    st.subheader("Latest city status")
    if summaries:
        cards = st.columns(min(3, max(1, len(summaries[:3]))))
        for index, summary in enumerate(summaries[:3]):
            with cards[index]:
                st.metric(summary.city, f"{summary.latest_aqi:.1f}" if summary.latest_aqi is not None else "Not available", border=True)
                st.caption(f"Category: {aqi_category(summary.latest_aqi)}")
                st.caption(f"Rows: {summary.rows:,}")
    else:
        st.info("No city status available.")
