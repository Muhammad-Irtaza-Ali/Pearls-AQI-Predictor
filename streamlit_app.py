from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="10 Pearls AQI Predictor",
    page_icon=":material/air:",
    layout="wide",
    initial_sidebar_state="expanded",
)


dashboard = st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True)
cities = st.Page("app_pages/cities.py", title="Cities", icon=":material/location_city:")
predictions = st.Page("app_pages/predictions.py", title="Predictions", icon=":material/smart_toy:")
explainability = st.Page("app_pages/explainability.py", title="Explainability", icon=":material/psychology:")
pipeline = st.Page("app_pages/pipeline.py", title="Data pipeline", icon=":material/schema:")
model_performance = st.Page("app_pages/model_performance.py", title="Model performance", icon=":material/analytics:")
data_quality = st.Page("app_pages/data_quality.py", title="Data quality", icon=":material/verified:")
reports = st.Page("app_pages/reports.py", title="Reports", icon=":material/description:")
settings = st.Page("app_pages/settings.py", title="Settings", icon=":material/settings:")

navigation = st.navigation(
    {
        "overview": [dashboard, cities, predictions, explainability],
        "operations": [pipeline, model_performance, data_quality, reports, settings],
    }
)

navigation.run()

