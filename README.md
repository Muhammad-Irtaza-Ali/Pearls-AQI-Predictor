# Pearls-AQI-Predictor

## Project Summary

This project is an end-to-end AQI data engineering pipeline that:

- collects data asynchronously from OpenWeather, Open-Meteo, and AQICN
- supports historical backfill and current hourly ingestion
- validates, cleans, standardizes, deduplicates, and fuses records
- builds Bronze / Silver / Gold layers
- produces a clean ML-ready Gold dataset
- stores raw data in Supabase and ML-ready data in Hopsworks
- generates pipeline, quality, metrics, and drift reports

### Current Progress

- Raw Bronze data: uploaded to Supabase
- ML-ready Gold data: uploaded to Hopsworks
- Clean Gold file: `data/gold/ml_ready_records.csv`
- Canonical merged Gold file: `data/gold/merged_records.csv`
- Data quality report: `reports/data_quality_report.json`
- Upload report: `reports/ml_ready_upload_report.json`

### Main Files

- `feature_pipeline/run_pipeline.py` - live pipeline entry point
- `feature_pipeline/pipeline.py` - async ingestion orchestration
- `feature_pipeline/preparation/ml_ready_dataset.py` - ML-ready dataset builder
- `feature_pipeline/modeling/trainer.py` - trains the three AQI regression models
- `feature_pipeline/api/main.py` - AQI prediction API
- `streamlit_app.py` - Streamlit GUI dashboard
- `scripts/upload_raw_to_supabase.py` - raw Bronze upload
- `scripts/upload_ml_ready_dataset.py` - raw to Supabase, ML-ready to Hopsworks
- `scripts/predict_aqi.py` - inference CLI
- `scripts/run_model_api.py` - start the prediction API
- `.github/workflows/ci.yml` - basic GitHub Actions validation
- `reports/project_status_report.md` - full project status and attachment comparison

## Run

Current live ingestion:

```powershell
python feature_pipeline\run_pipeline.py
```

Or use the helper script:

```powershell
.\scripts\run_pipeline.ps1
```

Historical backfill:

```powershell
python feature_pipeline\backfill\backfill.py --start-date 2023-01-01 --end-date 2023-01-01
```

Train three ML models from the Hopsworks ML-ready dataset:

```powershell
python scripts\train_models.py --source hopsworks
```

Run the prediction API:

```powershell
& .\.venv-hopsworks\Scripts\python.exe scripts\run_model_api.py
```

Run the Streamlit GUI:

```powershell
& ..\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## Deployment

This repository is set up for deployment on Render via `render.yaml`.

### Render

1. Push the repo to GitHub.
2. Connect the repo to Render.
3. Render will read `render.yaml` and run:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port $PORT
```

### Notes

- The Streamlit app is designed to run even when local CSV snapshots are missing.
- Prediction pages will show a warning if the trained model artifacts are not available in the deployed environment.
- If you want the deployed app to use the latest ML-ready data and model artifacts, sync them before deployment or store them in your external data services.

## CI / CD

- GitHub Actions CI: `.github/workflows/ci.yml`
- Render auto-deploy config: `render.yaml`
- The CI workflow checks imports and compile-time health on every push and pull request.

## Supabase and Hopsworks

Set these in `.env` to sync raw and model-ready data:

```env
SUPABASE_ENABLED=true
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_RAW_TABLE=raw_records

HOPSWORKS_ENABLED=true
HOPSWORKS_PROJECT=your_hopsworks_project
HOPSWORKS_API_KEY=your_hopsworks_api_key
HOPSWORKS_HOST=your_hopsworks_host
HOPSWORKS_PYTHON_EXE=C:\path\to\your\hopsworks\venv\Scripts\python.exe
HOPSWORKS_FEATURE_GROUP=daily_aqi_features
HOPSWORKS_FEATURE_GROUP_VERSION=1
```

The pipeline still keeps local CSV snapshots, and also syncs:
- bronze/raw rows to Supabase
- gold/model-ready rows to Hopsworks

For Hopsworks, use a separate Python 3.12/3.13 virtual environment and point `HOPSWORKS_PYTHON_EXE` to that interpreter.

To create the Hopsworks environment after installing Python 3.12 or 3.13:

```powershell
.\scripts\setup_hopsworks_env.ps1
```

## Schema Files

- `database/supabase_schema.sql` creates the raw Supabase table
- `feature_pipeline/storage/hopsworks_schema.py` defines the Hopsworks feature group contract
