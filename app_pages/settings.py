from __future__ import annotations

import streamlit as st

from gui.services import clear_cached_data, load_dataset


st.title("Settings")
frame = load_dataset()

with st.container(border=True):
    st.subheader("Refresh")
    if st.button("Refresh data and reports"):
        clear_cached_data()
        st.rerun()

with st.container(border=True):
    st.subheader("Data paths")
    st.write("ML-ready dataset:", "data/gold/ml_ready_records.csv")
    st.write("Training report:", "models/latest/training_report.json")
    st.write("Evaluation summary:", "reports/model_evaluation_summary.json")
    st.write("Available rows:", f"{len(frame):,}" if not frame.empty else "Not available")

