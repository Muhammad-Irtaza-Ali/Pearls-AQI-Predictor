# Pearls AQI Predictor — Project Status Report

Generated on: 2026-08-12

## Attachment Review

- File reviewed: `AQI_predict-1.pdf`
- Metadata shows:
  - Title: `AQI_predict.pdf`
  - Creator/Producer: Canva
  - Created: 2024-11-28
- The PDF is a Canva-made project brief/roadmap for the AQI Predictor idea.
- The current repository has progressed beyond the brief into an implemented pipeline.

## What The Project Does

- Collects AQI and weather data from multiple APIs asynchronously.
- Supports current ingestion and historical backfill.
- Validates, cleans, standardizes, deduplicates, and merges records.
- Produces Bronze / Silver / Gold layers.
- Generates quality, metrics, and drift reports.
- Stores raw data in Supabase and ML-ready data in Hopsworks.

## Key File Map

### Ingestion
- `feature_pipeline/run_pipeline.py` — entry point for live ingestion.
- `feature_pipeline/pipeline.py` — orchestrates async collection, validation, fusion, and summaries.
- `feature_pipeline/base_client.py` — shared async API client behavior, retries, timing.
- `feature_pipeline/openweather_client.py` — OpenWeather ingestion.
- `feature_pipeline/openmeteo_client.py` — Open-Meteo ingestion.
- `feature_pipeline/aqicn_client.py` — AQICN ingestion.
- `feature_pipeline/backfill/backfill.py` — historical backfill runner.

### Data Prep
- `feature_pipeline/validation/cleaner.py` — normalization and deduplication helpers.
- `feature_pipeline/validation/schema.py` — record schema and type validation.
- `feature_pipeline/validation/validator.py` — validation gate.
- `feature_pipeline/standardization/standardizer.py` — attaches run metadata and normalizes records.
- `feature_pipeline/fusion/merge_data.py` — merges validated records into gold.
- `feature_pipeline/fusion/model_ready.py` — projects gold into a clean ML-ready schema.
- `feature_pipeline/preparation/ml_ready_dataset.py` — builds the final ML-ready dataset and quality report.

### Storage
- `feature_pipeline/storage/csv_writer.py` — generic CSV writer.
- `feature_pipeline/storage/run_merger.py` — merges run snapshots into canonical CSVs.
- `feature_pipeline/storage/supabase_writer.py` — writes raw/validated rows to Supabase.
- `feature_pipeline/storage/hopsworks_writer.py` — pushes feature data to Hopsworks.
- `feature_pipeline/storage/hopsworks_sync_job.py` — Hopsworks sync helper.
- `feature_pipeline/storage/hopsworks_ml_ready_sync_job.py` — ML-ready Hopsworks sync helper.
- `feature_pipeline/storage/snapshots.py` — per-run snapshot writer.

### Reporting
- `feature_pipeline/reporting/report_generator.py` — pipeline run report JSON.
- `feature_pipeline/reporting/metrics_report.py` — metrics JSON.
- `feature_pipeline/reporting/quality_report.py` — data quality JSON.
- `feature_pipeline/reporting/output_writer.py` — writes outputs and syncs storage targets.
- `feature_pipeline/drift/*` — descriptive drift statistics and drift reports.

### Scripts
- `scripts/merge_all_runs.py` — rebuilds canonical Bronze/Silver/Gold CSVs.
- `scripts/prepare_ml_ready_dataset.py` — builds `data/gold/ml_ready_records.csv`.
- `scripts/upload_raw_to_supabase.py` — uploads Bronze/raw rows to Supabase.
- `scripts/upload_ml_ready_dataset.py` — uploads Bronze/raw to Supabase and ML-ready Gold to Hopsworks.
- `scripts/sync_all_runs.py` — syncs all historical runs.

## Current Progress

- Async multi-city, multi-API ingestion: implemented.
- Historical backfill: implemented.
- Bronze/Silver/Gold layers: implemented.
- ML-ready gold dataset: implemented and cleaned.
- Supabase raw upload: completed.
- Hopsworks ML-ready upload: completed.
- Drift statistics and reporting: implemented.
- CI/CD automation: not yet implemented.
- Model training / serving: not yet present in this repo.

## Data Quality Snapshot

- Raw bronze rows: 68,789
- ML-ready rows: 9,219
- Raw data stays unchanged in Bronze.
- ML-ready Gold is cleaned, deduplicated, aligned, and leakage-reduced.

## Comparison To Attachment

- The attachment reads like a project concept/roadmap.
- The repository now contains the actual production-style implementation.
- Most of the collection, cleaning, storage, and reporting scope has been delivered.
- The main remaining gap is downstream ML training/serving automation.

