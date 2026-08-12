from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import json
from pathlib import Path
from typing import Any

import pandas as pd


FEATURE_COLUMNS = [
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "rain",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
]

OUTPUT_COLUMNS = [
    "timestamp",
    "data_date",
    "city",
    "latitude",
    "longitude",
    *FEATURE_COLUMNS,
    "aqi",
]

SOURCE_FEATURE_COLUMNS = FEATURE_COLUMNS + ["aqi"]


@dataclass(slots=True)
class DatasetQualitySummary:
    total_records: int
    duplicate_snapshots_removed: int
    exact_duplicates_removed: int
    invalid_records: int
    source_conflicts: int
    target_available_records: int
    cleaned_records: int
    missing_values_before: dict[str, int]
    missing_values_after: dict[str, int]
    records_per_city: dict[str, int]
    date_coverage: dict[str, str | int | None]
    imputed_values: dict[str, int]
    dropped_rows_without_target: int
    dropped_rows_after_merge: int


def _load_table(path: str | Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path, low_memory=False)
    for column in ["timestamp", "retrieved_at"]:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce", utc=True)
    if "data_date" in dataframe.columns:
        dataframe["data_date"] = pd.to_datetime(dataframe["data_date"], errors="coerce").dt.date
    return dataframe


def _parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def _is_invalid_aqicn_record(row: pd.Series) -> bool:
    if str(row.get("source", "")).lower() != "aqicn":
        return False

    error_text = str(row.get("error", "") or "").lower()
    if "invalid key" in error_text:
        return True

    payload = _parse_jsonish(row.get("raw_payload"))
    if isinstance(payload, dict):
        payload_text = json.dumps(payload, ensure_ascii=False).lower()
        return "invalid key" in payload_text or '"status": "error"' in payload_text
    return "invalid key" in str(payload).lower()


def _prepare_source_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    source_table = dataframe.copy()
    source_table = source_table[source_table["source"].isin(["openweather", "openmeteo"])].copy()
    source_table = source_table[source_table["status"].isin(["success", "partial"])].copy()
    source_table["data_date"] = source_table["data_date"].where(source_table["data_date"].notna(), source_table["timestamp"].dt.date)

    numeric_columns = ["latitude", "longitude", "response_time_ms", "response_time_seconds", *SOURCE_FEATURE_COLUMNS]
    for column in numeric_columns:
        if column in source_table.columns:
            source_table[column] = pd.to_numeric(source_table[column], errors="coerce")

    source_table["feature_score"] = source_table.apply(_feature_score, axis=1)
    source_table["target_score"] = source_table["aqi"].notna().astype(int) * 100
    source_table["status_score"] = source_table["status"].map({"success": 20, "partial": 10}).fillna(0).astype(int)
    source_table["timestamp_score"] = source_table["timestamp"].notna().astype(int) * 5
    source_table["quality_score"] = (
        source_table["feature_score"]
        + source_table["target_score"]
        + source_table["status_score"]
        + source_table["timestamp_score"]
        - pd.to_numeric(source_table.get("response_time_ms"), errors="coerce").fillna(0).clip(lower=0).div(1000).round().astype(int)
    )

    source_table = source_table.sort_values(
        by=["city", "data_date", "source", "quality_score", "feature_score", "target_score", "retrieved_at", "timestamp", "response_time_ms"],
        ascending=[True, True, True, False, False, False, False, False, True],
        na_position="last",
    )
    source_table = source_table.drop_duplicates(subset=["city", "data_date", "source"], keep="first")
    return source_table


def _feature_score(row: pd.Series) -> int:
    return int(sum(pd.notna(row.get(column)) for column in FEATURE_COLUMNS))


def _row_quality_score(row: pd.Series) -> int:
    feature_score = _feature_score(row)
    target_score = int(pd.notna(row.get("aqi"))) * 100
    status_value = str(row.get("status", "")).lower()
    status_score = 20 if status_value == "success" else 10 if status_value == "partial" else 0
    timestamp_score = int(pd.notna(row.get("timestamp"))) * 5
    response_time_ms = pd.to_numeric(pd.Series([row.get("response_time_ms")]), errors="coerce").fillna(0).iloc[0]
    latency_penalty = int(round(max(float(response_time_ms), 0.0) / 1000.0))
    return int(feature_score + target_score + status_score + timestamp_score - latency_penalty)


def _merge_city_date_group(group: pd.DataFrame) -> dict[str, Any]:
    openweather = group[group["source"] == "openweather"].copy()
    openmeteo = group[group["source"] == "openmeteo"].copy()
    base_row = None
    other_row = None

    if not openweather.empty and not openmeteo.empty:
        weather_row = openweather.sort_values(
            by=["quality_score", "feature_score", "target_score", "retrieved_at", "timestamp", "response_time_ms"],
            ascending=[False, False, False, False, False, True],
            na_position="last",
        ).iloc[0]
        meteo_row = openmeteo.sort_values(
            by=["quality_score", "feature_score", "target_score", "retrieved_at", "timestamp", "response_time_ms"],
            ascending=[False, False, False, False, False, True],
            na_position="last",
        ).iloc[0]
        base_row = weather_row if _row_quality_score(weather_row) >= _row_quality_score(meteo_row) else meteo_row
        other_row = meteo_row if base_row is weather_row else weather_row
    elif not openweather.empty:
        base_row = openweather.sort_values(
            by=["quality_score", "feature_score", "target_score", "retrieved_at", "timestamp", "response_time_ms"],
            ascending=[False, False, False, False, False, True],
            na_position="last",
        ).iloc[0]
    elif not openmeteo.empty:
        base_row = openmeteo.sort_values(
            by=["quality_score", "feature_score", "target_score", "retrieved_at", "timestamp", "response_time_ms"],
            ascending=[False, False, False, False, False, True],
            na_position="last",
        ).iloc[0]
    else:
        return {}

    merged: dict[str, Any] = {}
    merged["city"] = base_row.get("city")
    merged["timestamp"] = base_row.get("timestamp")
    merged["data_date"] = base_row.get("data_date")
    merged["latitude"] = base_row.get("latitude")
    merged["longitude"] = base_row.get("longitude")

    if pd.notna(merged["timestamp"]):
        merged["timestamp"] = pd.Timestamp(merged["timestamp"]).to_pydatetime()
    if pd.notna(merged["data_date"]):
        merged["data_date"] = pd.Timestamp(merged["data_date"]).date()

    for column in FEATURE_COLUMNS:
        value = base_row.get(column)
        if pd.isna(value) and other_row is not None:
            value = other_row.get(column)
        merged[column] = value

    primary_aqi = base_row.get("aqi")
    if pd.isna(primary_aqi) and other_row is not None:
        primary_aqi = other_row.get("aqi")
    merged["aqi"] = primary_aqi
    return merged


def _merge_sources(source_table: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    rows: list[dict[str, Any]] = []
    source_conflicts = 0

    for (_, _), group in source_table.groupby(["city", "data_date"], dropna=False):
        openweather = group[group["source"] == "openweather"].head(1)
        openmeteo = group[group["source"] == "openmeteo"].head(1)
        if not openweather.empty and not openmeteo.empty:
            weather_row = openweather.iloc[0]
            meteo_row = openmeteo.iloc[0]
            if pd.notna(weather_row.get("aqi")) and pd.notna(meteo_row.get("aqi")) and weather_row.get("aqi") != meteo_row.get("aqi"):
                source_conflicts += 1
        merged_row = _merge_city_date_group(group)
        if merged_row:
            rows.append(merged_row)

    merged = pd.DataFrame(rows)
    if merged.empty:
        return merged, source_conflicts

    merged["timestamp"] = pd.to_datetime(merged["timestamp"], errors="coerce", utc=True)
    merged["data_date"] = pd.to_datetime(merged["data_date"], errors="coerce").dt.date
    return merged, source_conflicts


def _deduplicate_and_align(dataset: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    aligned = dataset.copy()
    aligned["timestamp"] = pd.to_datetime(aligned["timestamp"], errors="coerce", utc=True)
    aligned["data_date"] = pd.to_datetime(aligned["data_date"], errors="coerce").dt.date
    aligned.loc[aligned["data_date"].isna() & aligned["timestamp"].notna(), "data_date"] = aligned.loc[
        aligned["data_date"].isna() & aligned["timestamp"].notna(),
        "timestamp",
    ].dt.date

    exact_duplicates_removed = int(aligned.duplicated().sum())
    aligned = aligned.drop_duplicates()

    aligned = aligned.sort_values(
        by=["city", "data_date", "timestamp"],
        ascending=[True, True, False],
        na_position="last",
    )
    aligned = aligned.drop_duplicates(subset=["city", "data_date"], keep="first")
    return aligned, exact_duplicates_removed


def _impute_missing_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    imputed = dataset.copy()
    imputed_values: dict[str, int] = {}

    for column in FEATURE_COLUMNS:
        if column not in imputed.columns:
            continue
        city_medians = imputed.groupby("city")[column].transform("median")
        global_median = pd.to_numeric(imputed[column], errors="coerce").median()
        missing_before = int(pd.to_numeric(imputed[column], errors="coerce").isna().sum())
        imputed[column] = pd.to_numeric(imputed[column], errors="coerce").fillna(city_medians).fillna(global_median)
        imputed_values[column] = missing_before - int(pd.to_numeric(imputed[column], errors="coerce").isna().sum())

    return imputed, imputed_values


def _repair_city_event_dates(dataset: pd.DataFrame) -> pd.DataFrame:
    repaired = dataset.copy()
    repaired = repaired.sort_values(by=["city", "data_date", "timestamp"], na_position="last").reset_index(drop=True)

    def _repair_group(group: pd.DataFrame) -> pd.DataFrame:
        group = group.copy().reset_index(drop=True)
        last_seen_date = None
        repaired_dates: list[Any] = []

        for value in pd.to_datetime(group["data_date"], errors="coerce").dt.date.tolist():
            if pd.notna(value):
                last_seen_date = value
                repaired_dates.append(value)
                continue

            if last_seen_date is not None:
                last_seen_date = last_seen_date + timedelta(days=1)
                repaired_dates.append(last_seen_date)
            else:
                repaired_dates.append(value)

        group["data_date"] = repaired_dates
        return group

    repaired = repaired.groupby("city", group_keys=False).apply(_repair_group, include_groups=False)
    return repaired.reset_index(drop=True)


def build_ml_ready_dataset(
    silver_path: str | Path,
    bronze_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, DatasetQualitySummary]:
    silver = _load_table(silver_path)
    bronze = _load_table(bronze_path) if bronze_path is not None else pd.DataFrame()

    total_records = int(len(silver))
    exact_duplicates_removed = int(silver.duplicated().sum())

    bronze_invalid_records = 0
    if not bronze.empty and "source" in bronze.columns:
        aqicn_failed = bronze[bronze.apply(_is_invalid_aqicn_record, axis=1)]
        bronze_invalid_records = int(len(aqicn_failed))

    silver_invalid_records = 0
    if "source" in silver.columns:
        aqicn_failed = silver[silver.apply(_is_invalid_aqicn_record, axis=1)]
        silver_invalid_records = int(len(aqicn_failed))

    invalid_records = max(bronze_invalid_records, silver_invalid_records)

    source_table = _prepare_source_table(silver)
    duplicate_snapshots_removed = int(total_records - len(source_table))

    merged, source_conflicts = _merge_sources(source_table)
    merged, merged_exact_duplicates_removed = _deduplicate_and_align(merged)

    merged["aqi"] = pd.to_numeric(merged["aqi"], errors="coerce")
    missing_values_before = merged.isna().sum().to_dict()

    pre_target_filter_rows = int(len(merged))
    merged = merged[merged["aqi"].between(0, 500, inclusive="both")].copy()
    dropped_rows_without_target = int(pre_target_filter_rows - len(merged))

    merged, imputed_values = _impute_missing_features(merged)
    merged["aqi"] = pd.to_numeric(merged["aqi"], errors="coerce")

    merged = merged.dropna(subset=["aqi"]).copy()
    merged = _repair_city_event_dates(merged)

    merged["timestamp"] = pd.to_datetime(merged["timestamp"], errors="coerce", utc=True)
    fallback_timestamp = pd.to_datetime(merged["data_date"], errors="coerce", utc=True)
    merged["timestamp"] = merged["timestamp"].fillna(fallback_timestamp)
    merged["timestamp"] = merged["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    merged["data_date"] = pd.to_datetime(merged["data_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    merged = merged[OUTPUT_COLUMNS].copy()

    missing_values_after = merged.isna().sum().to_dict()
    records_per_city = merged["city"].value_counts().sort_index().to_dict()
    coverage_dates = pd.to_datetime(merged["data_date"], errors="coerce").dropna()
    coverage_timestamps = pd.to_datetime(merged["timestamp"], errors="coerce", utc=True).dropna()
    date_coverage = {
        "start_date": str(coverage_dates.min().date()) if not coverage_dates.empty else None,
        "end_date": str(coverage_dates.max().date()) if not coverage_dates.empty else None,
        "unique_days": int(pd.Series(coverage_dates.dt.date).nunique()) if not coverage_dates.empty else 0,
        "unique_timestamps": int(coverage_timestamps.nunique()) if not coverage_timestamps.empty else 0,
    }

    summary = DatasetQualitySummary(
        total_records=total_records,
        duplicate_snapshots_removed=duplicate_snapshots_removed,
        exact_duplicates_removed=exact_duplicates_removed + merged_exact_duplicates_removed,
        invalid_records=invalid_records,
        source_conflicts=source_conflicts,
        target_available_records=int(len(merged)),
        cleaned_records=int(len(merged)),
        missing_values_before={key: int(value) for key, value in missing_values_before.items()},
        missing_values_after={key: int(value) for key, value in missing_values_after.items()},
        records_per_city={key: int(value) for key, value in records_per_city.items()},
        date_coverage=date_coverage,
        imputed_values={key: int(value) for key, value in imputed_values.items()},
        dropped_rows_without_target=dropped_rows_without_target,
        dropped_rows_after_merge=int(total_records - len(merged)),
    )

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(path, index=False)

    return merged, summary


def quality_report(summary: DatasetQualitySummary) -> dict[str, Any]:
    return {
        "total_records": summary.total_records,
        "duplicate_snapshots_removed": summary.duplicate_snapshots_removed,
        "exact_duplicates_removed": summary.exact_duplicates_removed,
        "invalid_records": summary.invalid_records,
        "source_conflicts": summary.source_conflicts,
        "target_available_records": summary.target_available_records,
        "cleaned_records": summary.cleaned_records,
        "missing_values_before": summary.missing_values_before,
        "missing_values_after": summary.missing_values_after,
        "records_per_city": summary.records_per_city,
        "date_coverage": summary.date_coverage,
        "imputed_values": summary.imputed_values,
        "dropped_rows_without_target": summary.dropped_rows_without_target,
        "dropped_rows_after_merge": summary.dropped_rows_after_merge,
        "hopsworks_ready": summary.cleaned_records > 0 and summary.missing_values_after.get("aqi", 0) == 0,
        "recommended_upload": "data/gold/ml_ready_records.csv",
    }
