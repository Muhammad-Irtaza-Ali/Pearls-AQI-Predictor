from __future__ import annotations

import streamlit as st

from gui.services import load_json_report, load_text_report, PROJECT_STATUS_PATH, RAW_UPLOAD_REPORT_PATH, ML_READY_UPLOAD_REPORT_PATH


st.title("Data pipeline")

status_text = load_text_report(PROJECT_STATUS_PATH)
raw_report = load_json_report(RAW_UPLOAD_REPORT_PATH)
ml_report = load_json_report(ML_READY_UPLOAD_REPORT_PATH)

st.subheader("Pipeline flow")
with st.container(border=True):
    st.write("API Sources → Bronze → Validation → Silver → Standardization → Fusion → Gold → Feature Store / Model Data → ML Prediction → Dashboard")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("Raw upload")
        st.json(raw_report if raw_report else {"message": "Not available"})
with col2:
    with st.container(border=True):
        st.subheader("ML-ready upload")
        st.json(ml_report if ml_report else {"message": "Not available"})

with st.container(border=True):
    st.subheader("Project status report")
    st.text(status_text if status_text else "Not available")

