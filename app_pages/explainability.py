from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from feature_pipeline.modeling.explainability import explain_prediction
from gui.components import render_page_header, render_section_title
from gui.services import best_model_name, city_options, load_dataset


render_page_header(
    "Explainability",
    "Inspect why the model predicts a particular AQI value using a LIME-style local surrogate.",
    eyebrow="Model interpretation",
)

frame = load_dataset()
cities = city_options(frame)
default_model = st.session_state.get("selected_model", best_model_name() or "gradient_boosting")

with st.container(border=True):
    render_section_title("Explain a record", "Pick a city and inspect the latest available record for that location.")
    with st.form("explainability_form", border=False):
        city = st.selectbox("City", cities if cities else ["Karachi"])
        submitted = st.form_submit_button("Explain latest record")

    if submitted:
        city_frame = frame[frame["city"] == city].copy() if not frame.empty and "city" in frame.columns else pd.DataFrame()
        if city_frame.empty:
            st.warning("No data is available for the selected city.")
        else:
            if "timestamp" in city_frame.columns and city_frame["timestamp"].notna().any():
                city_frame = city_frame.sort_values("timestamp")
            latest_row = city_frame.iloc[-1]
            record = latest_row.to_dict()
            model_name = default_model

            try:
                explanation = explain_prediction(record, model_name=model_name, reference_frame=frame)
            except Exception as exc:
                st.error(f"Explainability is unavailable right now: {exc}")
            else:
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric("Model", explanation.model_name, border=True)
                with metric_col2:
                    st.metric("Predicted AQI", f"{explanation.prediction:.2f}", border=True)
                with metric_col3:
                    st.metric("Baseline", f"{explanation.baseline_prediction:.2f}", border=True)

                st.markdown("**Latest record**")
                st.json(record)

                local_df = pd.DataFrame([asdict(item) for item in explanation.local_contributions])
                if not local_df.empty:
                    st.markdown("**Local contributions**")
                    st.dataframe(
                        local_df[["feature", "transformed_feature", "contribution", "value"]],
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "transformed_feature": st.column_config.TextColumn("Model feature"),
                            "contribution": st.column_config.NumberColumn("Contribution", format="%.2f"),
                            "value": st.column_config.NumberColumn("Model-space value", format="%.2f"),
                        },
                    )
                    st.bar_chart(local_df.set_index("feature")["contribution"], width="stretch", height=300)

                global_df = pd.DataFrame([asdict(item) for item in explanation.global_importance])
                if not global_df.empty:
                    st.markdown("**Global feature importance**")
                    st.dataframe(
                        global_df,
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "importance": st.column_config.NumberColumn("Importance", format="%.4f"),
                        },
                    )
                    st.bar_chart(global_df.set_index("feature")["importance"], width="stretch", height=300)
