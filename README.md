# Pearls-AQI-Predictor

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
