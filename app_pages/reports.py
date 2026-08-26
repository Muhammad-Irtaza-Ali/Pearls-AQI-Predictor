from __future__ import annotations

from pathlib import Path

import streamlit as st

from gui.services import ROOT_DIR


st.title("Reports")

report_paths = [
    ROOT_DIR / "reports" / "data_quality_report.json",
    ROOT_DIR / "reports" / "model_training_report.json",
    ROOT_DIR / "reports" / "model_evaluation_summary.json",
    ROOT_DIR / "reports" / "project_status_report.md",
    ROOT_DIR / "reports" / "ml_ready_upload_report.json",
    ROOT_DIR / "reports" / "raw_supabase_upload_report.json",
]

for path in report_paths:
    with st.container(border=True):
        st.subheader(path.name)
        if path.exists():
            st.caption(str(path))
            if path.suffix.lower() in {".json", ".md", ".txt"}:
                st.code(path.read_text(encoding="utf-8"), language="json" if path.suffix.lower() == ".json" else "markdown")
            st.download_button("Download", path.read_bytes(), file_name=path.name)
        else:
            st.info("Not available")

