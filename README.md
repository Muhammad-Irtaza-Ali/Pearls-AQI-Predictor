# 10 Pearls AQI Predictor

An end-to-end data science project for collecting, preparing, monitoring, and predicting Air Quality Index (AQI) values across multiple cities.

## Project Links

- **Live Streamlit dashboard:** [10 Pearls AQI Predictor](https://10pearls-aqi-predictorr.streamlit.app/)
- **Live FastAPI backend:** [Pearls AQI Backend](https://pearls-aqi-backend-production.up.railway.app/)
- **API documentation:** [FastAPI Swagger UI](https://pearls-aqi-backend-production.up.railway.app/docs)
- **Project description:** [Google Drive project brief](https://drive.google.com/file/d/1HPf17hvqI6icNTjRPkPuydkV1ub_lO5/view?usp=sharing)

## Project Overview

The project collects weather and air-pollution observations, validates and standardizes them, prepares machine-learning features, stores the data in external services, trains regression models, and serves predictions through a public API and dashboard.

The system is designed as a serverless-style stack. GitHub Actions handles scheduled automation, Supabase stores operational data, Hopsworks stores ML-ready features, Railway hosts the FastAPI backend, and Streamlit Community Cloud hosts the user interface.

The current prediction workflow estimates AQI from supplied city, time, weather, and pollutant conditions. The dashboard is ready for future multi-day forecasting once forecast inputs and a forecast horizon are added to the model contract.

## Technology Stack

- **Python** for ingestion, validation, feature preparation, training, and serving
- **Pandas and NumPy** for data processing
- **Scikit-learn** for Ridge, Random Forest, and Gradient Boosting regression
- **FastAPI and Uvicorn** for the prediction and data API
- **Streamlit** for the interactive dashboard
- **Supabase** for raw and model-ready operational data
- **Hopsworks** for the ML feature store and training source
- **SHAP** with a local fallback for explainability
- **GitHub Actions** for CI, hourly ingestion, daily training, and manual backfills
- **Railway** for the public FastAPI backend
- **GitHub** for source control and deployment triggers

## Main Features

### Feature pipeline

The pipeline fetches data asynchronously from OpenWeather, Open-Meteo, and AQICN. It records API status, response time, source metadata, errors, timestamps, and run IDs. Records then pass through validation, cleaning, standardization, deduplication, and model-ready projection.

### Bronze, Silver, and Gold layers

- **Bronze:** raw API responses and ingestion metadata
- **Silver:** validated and standardized records
- **Gold:** compact records used for training, scoring, reporting, and dashboard data

The latest model-ready records are exposed securely through:

```text
GET /data/ml-ready
```

### Historical backfill

Historical dates can be collected for training data and evaluation. Backfills are available from the command line and through a manually triggered GitHub Actions workflow.

### Machine-learning models

The training pipeline compares Ridge Regression, Random Forest Regressor, and Gradient Boosting Regressor. The data is split chronologically so later observations are held out for testing.

Models are evaluated with:

- **RMSE:** penalizes large prediction errors more strongly
- **MAE:** average absolute AQI error in AQI points
- **R²:** proportion of target variation explained by the model

The model with the lowest RMSE is selected and recorded in the local model registry.

### Dashboard

The Streamlit dashboard includes AQI overview and trends, city comparisons, single predictions, batch CSV predictions, explainability, model performance, data-quality reports, pipeline reports, and system status.

The prediction page sends requests to the deployed FastAPI backend. Dashboard data is requested from Supabase through the backend, so database service-role credentials are never exposed to the browser.

## Repository Structure

```text
streamlit_app.py                 Streamlit entry point
app_pages/                       Dashboard navigation pages
gui/                             Streamlit services and API client
feature_pipeline/api/main.py    FastAPI application
feature_pipeline/pipeline.py    Async ingestion orchestration
feature_pipeline/modeling/      Training, registry, prediction, explainability
feature_pipeline/storage/       Supabase, Hopsworks, CSV, and snapshot writers
feature_pipeline/validation/    Schemas, validation, and cleaning
feature_pipeline/reporting/     Quality, metrics, and pipeline reports
database/                        Supabase table schemas
scripts/                         CLI utilities
.github/workflows/               CI and scheduled automation
railway.toml                     Railway API deployment configuration
requirements.txt                 Python dependencies
```

## Run Locally

Use Python **3.12** on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a local `.env` file with your private credentials. Never commit this file.

Start FastAPI in one terminal:

```powershell
python -m uvicorn feature_pipeline.api.main:app --reload --host 127.0.0.1 --port 8000
```

Open the local API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Start Streamlit in a second terminal:

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"
python -m streamlit run streamlit_app.py
```

Open the dashboard at [http://localhost:8501](http://localhost:8501).

## Environment Variables

### FastAPI and dashboard data

```env
SUPABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ML_READY_TABLE=ml_ready_records
```

### Frontend API URL

For local development:

```env
API_BASE_URL=http://127.0.0.1:8000
```

For Streamlit Cloud, add this in **Settings → Secrets**:

```toml
API_BASE_URL = "https://pearls-aqi-backend-production.up.railway.app"
```

### Ingestion and Hopsworks

The scheduled pipeline also uses these secrets when enabled:

```env
OPENWEATHER_API_KEY=...
OPENWEATHER_LOCATION_IDS={"Karachi":"..."}
AQICN_API_KEY=...
OPENMETEO_API_KEY=...
HOPSWORKS_ENABLED=true
HOPSWORKS_PROJECT=...
HOPSWORKS_API_KEY=...
HOPSWORKS_HOST=...
HOPSWORKS_ML_FEATURE_GROUP=aqi_ml_ready_features
HOPSWORKS_ML_FEATURE_GROUP_VERSION=1
HOPSWORKS_MODEL_NAME=aqi_predictor
HOPSWORKS_MODEL_VERSION=1
```

## Deployment

### FastAPI on Railway

The backend is deployed at:

```text
https://pearls-aqi-backend-production.up.railway.app
```

Railway uses `railway.toml` and starts the application with:

```bash
uvicorn feature_pipeline.api.main:app --host 0.0.0.0 --port $PORT
```

Add the Supabase variables to the Railway service. The backend needs them for `/data/ml-ready`.

The backend also needs trained model artifacts for `/predict` and `/batch-predict`:

```text
models/latest/manifest.json
models/latest/*.joblib
```

Training publishes the approved model to the Hopsworks Model Registry under `HOPSWORKS_MODEL_NAME`. Railway downloads that model at runtime. Set `HOPSWORKS_MODEL_VERSION` to the published version; when it is omitted, the backend attempts to use the latest registered version. Railway should install `requirements-api.txt`, which adds the Hopsworks client to the shared application dependencies.

### Streamlit Cloud

The frontend is deployed at:

```text
https://10pearls-aqi-predictorr.streamlit.app/
```

Use these Streamlit Cloud settings:

- Repository: `Muhammad-Irtaza-Ali/Pearls-AQI-Predictor`
- Branch: `main`
- Main file: `streamlit_app.py`
- Python version: `3.12`

Add the `API_BASE_URL` secret shown above, then reboot the app after changing it.

## GitHub Actions Automation

- **CI:** runs on pushes to `main` and pull requests. It installs dependencies, compiles the project, imports FastAPI, and checks the Streamlit entry point.
- **Hourly ingestion:** runs at `0 * * * *` UTC.
- **Daily training:** runs at `30 1 * * *` UTC.
- **Historical backfill:** started manually with date inputs.

Required GitHub repository secrets must be configured before scheduled workflows can access external APIs and stores. Workflow artifacts contain run reports and logs for inspection.

## Useful Commands

Run current ingestion:

```powershell
python feature_pipeline\run_pipeline.py
```

Run a historical backfill:

```powershell
python feature_pipeline\backfill\backfill.py --start-date 2023-01-01 --end-date 2023-01-07
```

Train models from Hopsworks or the automatic fallback source:

```powershell
python scripts\train_models.py --source auto
```

Generate the model evaluation summary:

```powershell
python scripts\generate_model_evaluation.py
```

Inspect the model registry:

```powershell
python scripts\model_registry.py
```

Run tests:

```powershell
python -m pytest -q
```

## Project Status and Honest Limitations

- The ingestion, validation, storage, reporting, API, dashboard, CI, and scheduled workflow pieces are implemented.
- The project currently predicts AQI from supplied conditions. A complete three-day forecast requires future weather and pollutant inputs or a dedicated time-series forecast model.
- TensorFlow, PyTorch, Flask, and Apache Airflow are not currently required by the implementation; the project uses scikit-learn, FastAPI, and GitHub Actions instead.
- Local `data/`, `reports/`, and `models/` outputs are generated artifacts and are excluded from normal source control. Production data is read through Supabase and ML features are stored in Hopsworks.
- Model accuracy must be reported from a generated evaluation file after training. Do not claim RMSE, MAE, or R² values without a current evaluation run.

## Data and Security Notes

- Keep `.env`, Supabase service-role keys, Hopsworks API keys, and provider API keys private.
- Do not place service-role credentials in Streamlit Cloud frontend code.
- The backend acts as the trusted layer for Supabase reads and model inference.
- Supabase schemas are available in `database/`.
