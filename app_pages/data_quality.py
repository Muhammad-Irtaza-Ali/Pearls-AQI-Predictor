from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.services import load_dataset, load_json_report, QUALITY_REPORT_PATH


st.title("Data quality")
quality_report = load_json_report(QUALITY_REPORT_PATH)
frame = load_dataset()

if not quality_report:
    st.warning("No quality report available.")
else:
    with st.container(horizontal=True):
        st.metric("Total records", f"{quality_report.get('total_records', 'Not available'):,}" if quality_report.get("total_records") is not None else "Not available", border=True)
        st.metric("Cleaned records", f"{quality_report.get('cleaned_records', 'Not available'):,}" if quality_report.get("cleaned_records") is not None else "Not available", border=True)
        st.metric("Source conflicts", f"{quality_report.get('source_conflicts', 'Not available'):,}" if quality_report.get("source_conflicts") is not None else "Not available", border=True)
        st.metric("Target available", f"{quality_report.get('target_available_records', 'Not available'):,}" if quality_report.get("target_available_records") is not None else "Not available", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Records per city")
            city_counts = pd.DataFrame(list(quality_report.get("records_per_city", {}).items()), columns=["city", "rows"])
            st.bar_chart(city_counts, x="city", y="rows", width="stretch", height=320)
    with col2:
        with st.container(border=True):
            st.subheader("Missing before cleaning")
            missing_before = pd.DataFrame(list(quality_report.get("missing_values_before", {}).items()), columns=["feature", "missing"])
            st.bar_chart(missing_before, x="feature", y="missing", width="stretch", height=320)

    with st.container(border=True):
        st.subheader("Report details")
        st.json(quality_report)

