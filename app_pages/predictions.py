from __future__ import annotations

from datetime import datetime, time, timezone

import pandas as pd
import streamlit as st

from gui.components import render_page_header, render_section_title
from feature_pipeline.modeling.predictor import predict_dataframe, predict_single
from gui.services import aqi_category, available_models, best_model_name, city_options, load_dataset


render_page_header(
    "AQI predictions",
    "Run real-time AQI inference from the best trained model using city and weather inputs.",
    eyebrow="Prediction workspace",
)
frame = load_dataset()
cities = city_options(frame)
comparison_rows = available_models()
default_model = st.session_state.get("selected_model", best_model_name() or "gradient_boosting")

if comparison_rows:
    available_model_names = [str(row.get("name")) for row in comparison_rows if row.get("name")]
    if default_model not in available_model_names:
        default_model = available_model_names[0]
else:
    available_model_names = [default_model]

selected_model = st.selectbox(
    "Prediction model",
    options=available_model_names,
    index=available_model_names.index(default_model) if default_model in available_model_names else 0,
    help="Choose which trained model to use for predictions.",
)
st.session_state["selected_model"] = selected_model

with st.container(border=True):
    render_section_title("Single prediction", "Enter city and weather conditions to estimate AQI.")
    with st.form("prediction_form", border=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            city = st.selectbox("City", cities if cities else ["Karachi"])
            latitude = st.number_input("Latitude", value=24.8607, format="%.4f")
            longitude = st.number_input("Longitude", value=67.0011, format="%.4f")
            date_value = st.date_input("Date", value=datetime.now(timezone.utc).date())
            time_value = st.time_input("Time", value=time(12, 0))
        with col2:
            temperature = st.number_input("Temperature", value=29.5, format="%.2f")
            humidity = st.number_input("Humidity", value=72.0, format="%.2f")
            pressure = st.number_input("Pressure", value=1008.0, format="%.2f")
            wind_speed = st.number_input("Wind speed", value=4.2, format="%.2f")
            wind_direction = st.number_input("Wind direction", value=180.0, format="%.2f")
        with col3:
            cloud_cover = st.number_input("Cloud cover", value=15.0, format="%.2f")
            rain = st.number_input("Rain", value=0.0, format="%.2f")
            pm25 = st.number_input("PM2.5", value=18.2, format="%.2f")
            pm10 = st.number_input("PM10", value=31.4, format="%.2f")

        row1, row2 = st.columns(2)
        with row1:
            co = st.number_input("CO", value=0.5, format="%.2f")
            no = st.number_input("NO", value=1.2, format="%.2f")
            no2 = st.number_input("NO2", value=9.4, format="%.2f")
        with row2:
            so2 = st.number_input("SO2", value=2.1, format="%.2f")
            o3 = st.number_input("O3", value=33.0, format="%.2f")
            nh3 = st.number_input("NH3", value=0.8, format="%.2f")

        submitted = st.form_submit_button("Run prediction")

    if submitted:
        timestamp = datetime.combine(date_value, time_value, tzinfo=timezone.utc).isoformat()
        record = {
            "latitude": latitude,
            "longitude": longitude,
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "cloud_cover": cloud_cover,
            "rain": rain,
            "pm25": pm25,
            "pm10": pm10,
            "co": co,
            "no": no,
            "no2": no2,
            "so2": so2,
            "o3": o3,
            "nh3": nh3,
            "city": city,
            "timestamp": timestamp,
        }

        current_aqi = None
        if not frame.empty and "city" in frame.columns and "aqi" in frame.columns:
            city_history = frame[frame["city"] == city].copy()
            if not city_history.empty:
                if "timestamp" in city_history.columns and city_history["timestamp"].notna().any():
                    city_history = city_history.sort_values("timestamp")
                current_row = city_history.iloc[-1]
                if pd.notna(current_row.get("aqi")):
                    current_aqi = float(current_row.get("aqi"))

        result = predict_single(record, model_name=selected_model)
        left, right = st.columns(2)
        with left:
            st.metric("Predicted AQI", f"{result.prediction:.2f}", border=True)
        with right:
            st.metric("Model used", result.model_name, border=True)
        if current_aqi is not None:
            comparison_col1, comparison_col2 = st.columns(2)
            with comparison_col1:
                st.metric("Current AQI", f"{current_aqi:.2f}", border=True)
            with comparison_col2:
                st.metric("Current category", aqi_category(current_aqi), border=True)
        st.markdown("**Input payload**")
        st.json(result.input_row)

with st.container(border=True):
    render_section_title("Batch prediction", "Upload a CSV of feature rows for bulk inference.")
    uploaded = st.file_uploader("Upload a CSV with model features", type=["csv"])
    if uploaded is not None:
        batch_frame = pd.read_csv(uploaded)
        predicted = predict_dataframe(batch_frame, model_name=selected_model)
        st.dataframe(predicted.head(200), hide_index=True, width="stretch")
        st.download_button("Download predictions", predicted.to_csv(index=False).encode("utf-8"), file_name="predictions.csv")
