from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger("hopsworks_sync")

FEATURE_GROUP_COLUMNS = [
    "timestamp",
    "data_date",
    "city",
    "country",
    "latitude",
    "longitude",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "rain",
    "aqi",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
    "source",
    "endpoint",
    "status",
    "run_id",
    "pipeline_version",
    "api_version",
    "retrieved_at",
    "response_time_ms",
    "response_time_seconds",
]

NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "rain",
    "aqi",
    "pm25",
    "pm10",
    "co",
    "no",
    "no2",
    "so2",
    "o3",
    "nh3",
    "response_time_ms",
    "response_time_seconds",
]

DATETIME_COLUMNS = ["timestamp", "data_date", "retrieved_at"]

TEXT_COLUMNS = [
    "city",
    "country",
    "source",
    "endpoint",
    "status",
    "run_id",
    "pipeline_version",
    "api_version",
]


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def _normalize_host(host: str) -> str:
    normalized = host.strip().rstrip("/")
    if normalized.startswith("https://"):
        normalized = normalized.removeprefix("https://")
    elif normalized.startswith("http://"):
        normalized = normalized.removeprefix("http://")
    return normalized


def _default_cert_folder() -> str:
    return str(Path(__file__).resolve().parents[2] / ".hopsworks-certs")


def _default_tmp_folder() -> Path:
    tmp_folder = Path(__file__).resolve().parents[2] / ".hopsworks-tmp"
    tmp_folder.mkdir(parents=True, exist_ok=True)
    return tmp_folder


def _patch_hopsworks_temp_paths() -> None:
    from hopsworks_common.client import base as hopsworks_base_client
    from hopsworks_common.client import hopsworks as hopsworks_client

    temp_folder = _default_tmp_folder()

    def _local_path(filename: str) -> str:
        return str(temp_folder / filename)

    def _patched_write_pem(self: Any, keystore_path: str, keystore_pw: str, truststore_path: str, truststore_pw: str, prefix: str) -> tuple[str, str, str]:
        import jks  # type: ignore

        ks = jks.KeyStore.load(Path(keystore_path), keystore_pw, try_decrypt_keys=True)
        ts = jks.KeyStore.load(Path(truststore_path), truststore_pw, try_decrypt_keys=True)

        ca_chain_path = _local_path(f"{prefix}_ca_chain.pem")
        client_cert_path = _local_path(f"{prefix}_client_cert.pem")
        client_key_path = _local_path(f"{prefix}_client_key.pem")

        self._write_ca_chain(ks, ts, ca_chain_path)
        self._write_client_cert(ks, client_cert_path)
        self._write_client_key(ks, client_key_path)

        return ca_chain_path, client_cert_path, client_key_path

    def _patched_get_ca_chain_path(self: Any) -> str:
        return _local_path("ca_chain.pem")

    def _patched_get_client_cert_path(self: Any) -> str:
        return _local_path("client_cert.pem")

    def _patched_get_client_key_path(self: Any) -> str:
        return _local_path("client_key.pem")

    hopsworks_base_client.Client._write_pem = _patched_write_pem  # type: ignore[assignment]
    hopsworks_client.Client._get_ca_chain_path = _patched_get_ca_chain_path  # type: ignore[assignment]
    hopsworks_client.Client._get_client_cert_path = _patched_get_client_cert_path  # type: ignore[assignment]
    hopsworks_client.Client._get_client_key_path = _patched_get_client_key_path  # type: ignore[assignment]


def _prepare_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    feature_dataframe = dataframe.copy()
    feature_dataframe = feature_dataframe[[column for column in FEATURE_GROUP_COLUMNS if column in feature_dataframe.columns]]

    for column in DATETIME_COLUMNS:
        if column in feature_dataframe.columns:
            feature_dataframe[column] = pd.to_datetime(feature_dataframe[column], errors="coerce", utc=True)

    for column in NUMERIC_COLUMNS:
        if column in feature_dataframe.columns:
            feature_dataframe[column] = pd.to_numeric(feature_dataframe[column], errors="coerce")

    for column in TEXT_COLUMNS:
        if column in feature_dataframe.columns:
            feature_dataframe[column] = feature_dataframe[column].map(
                lambda value: None
                if pd.isna(value)
                else value
                if isinstance(value, str)
                else str(value)
            )

    return feature_dataframe


def _sync_feature_group(
    project_handle: Any,
    dataframe: pd.DataFrame,
    *,
    group_name: str,
    group_version: int,
) -> int:
    feature_store = project_handle.get_feature_store()
    feature_group = feature_store.get_or_create_feature_group(
        name=group_name,
        version=group_version,
        primary_key=["city", "data_date"],
        event_time="timestamp",
        description="Model-ready AQI features",
        time_travel_format="HUDI",
        hudi_precombine_key="retrieved_at",
    )
    feature_group.insert(dataframe, write_options={"wait_for_job": True})
    return group_version


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    args = argv or sys.argv[1:]
    if len(args) < 6:
        logger.error("Usage: hopsworks_sync_job.py <records_json> <host> <project> <api_key> <group> <version>")
        return 2

    records_path = Path(args[0])
    host = _normalize_host(args[1])
    project = args[2]
    api_key = args[3]
    group_name = args[4]
    group_version = int(args[5])

    try:
        import hopsworks  # type: ignore
    except Exception as exc:
        logger.error("Hopsworks package is unavailable in this interpreter: %s", exc)
        return 3

    _patch_hopsworks_temp_paths()

    records = json.loads(records_path.read_text(encoding="utf-8"))
    dataframe = pd.DataFrame(records)
    if dataframe.empty:
        logger.info("No records to sync")
        return 0

    dataframe = _prepare_dataframe(dataframe)

    project_handle = hopsworks.login(
        host=host,
        project=project,
        api_key_value=api_key,
        engine="python",
        cert_folder=_default_cert_folder(),
    )
    try:
        synced_version = _sync_feature_group(
            project_handle,
            dataframe,
            group_name=group_name,
            group_version=group_version,
        )
    except Exception as exc:
        error_text = str(exc).lower()
        if "delta library is not installed" not in error_text:
            raise
        logger.warning("Retrying Hopsworks sync with feature group version %s because Delta is unavailable", group_version + 1)
        synced_version = _sync_feature_group(
            project_handle,
            dataframe,
            group_name=group_name,
            group_version=group_version + 1,
        )

    logger.info("Synced %s rows to Hopsworks feature group %s v%s", len(dataframe), group_name, synced_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
