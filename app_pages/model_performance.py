from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.components import render_page_header, render_section_title
from gui.services import EVALUATION_SUMMARY_PATH, TRAINING_REPORT_PATH, available_models, best_model_name, load_json_report
from feature_pipeline.modeling.registry import get_current_model, list_models


render_page_header(
    "Model performance",
    "Compare trained models, review metrics, and choose the active model for prediction.",
    eyebrow="Model selection",
)

training_report = load_json_report(TRAINING_REPORT_PATH)
evaluation_report = load_json_report(EVALUATION_SUMMARY_PATH)
comparison_rows = available_models()
best_model = best_model_name() or str(training_report.get("best_model", "Not available"))
selected_model = st.session_state.get("selected_model", best_model)

if comparison_rows:
    model_names = [str(row.get("name")) for row in comparison_rows if row.get("name")]
    default_index = model_names.index(selected_model) if selected_model in model_names else 0
    active_model = st.selectbox(
        "Choose active model",
        options=model_names,
        index=default_index,
        help="This model will be used for single and batch predictions in the app.",
    )
    st.session_state["selected_model"] = active_model
else:
    active_model = best_model
    st.session_state["selected_model"] = active_model

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Best model", best_model, border=True)
with col2:
    st.metric("Active model", active_model, border=True)
with col3:
    st.metric(
        "Best RMSE",
        f"{float(evaluation_report.get('best_rmse', 0.0)):.2f}" if evaluation_report.get("best_rmse") is not None else "Not available",
        border=True,
    )
with col4:
    st.metric(
        "Model accuracy (R2)",
        f"{float(evaluation_report.get('best_r2', 0.0)):.3f}" if evaluation_report.get("best_r2") is not None else "Not available",
        border=True,
    )

st.caption("For this regression problem, higher R2 and lower RMSE/MAE indicate a stronger model.")

current_model = get_current_model()
registry_models = list_models()

with st.container(border=True):
    render_section_title("Registry", "This is the approved model registry record used by predictions.")
    if current_model:
        reg_col1, reg_col2, reg_col3 = st.columns(3)
        with reg_col1:
            st.metric("Registry model", str(current_model.get("model_name", "Not available")), border=True)
        with reg_col2:
            st.metric("Registry version", str(current_model.get("version", "Not available")), border=True)
        with reg_col3:
            st.metric("Registry RMSE", f"{float(current_model.get('metrics', {}).get('rmse', 0.0)):.2f}", border=True)
    else:
        st.info("No approved registry model is available yet.")

    if registry_models:
        registry_df = pd.DataFrame(
            [
                {
                    "model": entry.get("model_name"),
                    "version": entry.get("version"),
                    "approved": entry.get("approved"),
                    "rmse": entry.get("metrics", {}).get("rmse"),
                    "mae": entry.get("metrics", {}).get("mae"),
                    "r2": entry.get("metrics", {}).get("r2"),
                    "run_id": entry.get("run_id"),
                }
                for entry in registry_models
            ]
        )
        st.dataframe(registry_df, hide_index=True, width="stretch")

if comparison_rows:
    render_section_title("Model comparison", "Lower RMSE is better. The selected model is highlighted as the active choice.")
    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df = comparison_df.rename(
        columns={
            "name": "model",
            "rmse": "rmse",
            "mae": "mae",
            "r2": "r2",
            "fit_seconds": "fit_seconds",
        }
    )
    comparison_df["active"] = comparison_df["model"].eq(active_model)
    display_columns = ["model", "rmse", "mae", "r2", "fit_seconds", "active"]
    st.dataframe(comparison_df[display_columns], hide_index=True, width="stretch")
    st.bar_chart(comparison_df.set_index("model")["rmse"], width="stretch", height=320)

    best_row = comparison_df.sort_values("rmse", ascending=True).iloc[0]
    st.info(
        f"Best model by RMSE: {best_row['model']} | RMSE={best_row['rmse']:.2f} | "
        f"MAE={best_row['mae']:.2f} | R2={best_row['r2']:.3f}"
    )
else:
    st.warning("No model comparison data is available yet.")

if training_report:
    with st.container(border=True):
        render_section_title("Training report", "This is the latest training summary saved by the pipeline.")
        st.json(training_report)
else:
    st.warning("No training report available.")
