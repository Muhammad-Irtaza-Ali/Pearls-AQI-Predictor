from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.components import render_page_header, render_section_title
from gui.services import aqi_category, build_city_summaries, city_options, filter_frame, load_dataset


render_page_header(
    "City AQI monitoring",
    "Track live AQI levels, pollutant snapshots, and city trends across the monitoring network.",
    eyebrow="City operations",
)
frame = load_dataset()
cities = city_options(frame)
selected_city = st.selectbox("City", cities if cities else ["Not available"])

if frame.empty or not cities:
    st.warning("No city data available.")
else:
    city_frame = frame[frame["city"] == selected_city].copy()
    city_frame = city_frame.sort_values("timestamp") if "timestamp" in city_frame.columns else city_frame
    latest = city_frame.iloc[-1]

    with st.container(horizontal=True):
        st.metric("Latest AQI", f"{latest['aqi']:.1f}", border=True)
        st.metric("Category", aqi_category(float(latest["aqi"])), border=True)
        st.metric("Temperature", f"{latest['temperature']:.1f} °C", border=True)
        st.metric("Humidity", f"{latest['humidity']:.1f} %", border=True)

    with st.container(horizontal=True):
        st.metric("Pressure", f"{latest['pressure']:.1f} hPa", border=True)
        st.metric("Wind speed", f"{latest['wind_speed']:.1f} m/s", border=True)
        st.metric("Rows", f"{len(city_frame):,}", border=True)
        st.metric("Last update", str(latest["timestamp"]), border=True)

    render_section_title("City analytics", "Trend and pollutant snapshot for the selected city.")
    col1, col2 = st.columns(2, vertical_alignment="top")
    with col1:
        with st.container(border=True):
            st.subheader("AQI trend")
            st.line_chart(city_frame.set_index("timestamp")["aqi"], width="stretch", height=320)
    with col2:
        with st.container(border=True):
            st.subheader("Pollutant snapshot")
            pollutant_columns = [col for col in ["pm25", "pm10", "co", "no", "no2", "so2", "o3", "nh3"] if col in city_frame.columns]
            latest_pollutants = pd.DataFrame({"pollutant": pollutant_columns, "value": [float(latest[col]) for col in pollutant_columns]})
            st.bar_chart(latest_pollutants, x="pollutant", y="value", width="stretch", height=320)

    with st.container(border=True):
        st.subheader("City history")
        st.dataframe(city_frame.tail(250), hide_index=True, width="stretch")
