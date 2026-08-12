from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)


def _sync_feature_group_records(
    records: list[dict[str, Any]],
    *,
    feature_group: str | None = None,
    feature_group_version: int | None = None,
    sync_script_name: str = "hopsworks_sync_job.py",
) -> bool:
    if not settings.hopsworks_enabled:
        return False
    if not settings.hopsworks_api_key or not settings.hopsworks_project or not settings.hopsworks_host:
        logger.warning("Hopsworks sync skipped because credentials are missing")
        return False
    if not records:
        return False

    dataframe = pd.DataFrame(records)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as temp_file:
        json.dump(dataframe.to_dict(orient="records"), temp_file, default=str)
        temp_path = temp_file.name

    try:
        if settings.hopsworks_python_exe:
            sync_script = os.path.join(os.path.dirname(__file__), sync_script_name)
            command = [
                settings.hopsworks_python_exe,
                sync_script,
                temp_path,
                settings.hopsworks_host,
                settings.hopsworks_project,
                settings.hopsworks_api_key,
                feature_group or settings.hopsworks_feature_group,
                str(feature_group_version or settings.hopsworks_feature_group_version),
            ]
            completed = subprocess.run(command, capture_output=True, text=True)
            if completed.returncode == 0:
                logger.info(
                    "Hopsworks feature sync complete | group=%s | version=%s | rows=%s",
                    settings.hopsworks_feature_group,
                    settings.hopsworks_feature_group_version,
                    len(dataframe),
                )
                return True
            logger.warning(
                "Hopsworks sync failed with exit code %s | stdout=%s | stderr=%s",
                completed.returncode,
                completed.stdout.strip(),
                completed.stderr.strip(),
            )
            return False

        logger.warning("Hopsworks sync skipped because HOPSWORKS_PYTHON_EXE is not set")
        return False
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def write_feature_group(records: list[dict[str, Any]], run_id: str) -> bool:
    dataframe = pd.DataFrame(records)
    dataframe["run_id"] = run_id
    return _sync_feature_group_records(dataframe.to_dict(orient="records"))


def write_feature_group_records(records: list[dict[str, Any]]) -> bool:
    return _sync_feature_group_records(records)


def write_ml_ready_feature_group(records: list[dict[str, Any]]) -> bool:
    return _sync_feature_group_records(
        records,
        feature_group=settings.hopsworks_ml_feature_group,
        feature_group_version=settings.hopsworks_ml_feature_group_version,
        sync_script_name="hopsworks_ml_ready_sync_job.py",
    )
