from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from config import settings

logger = logging.getLogger("model_data_loader")


def _patch_temp_environment() -> None:
    temp_folder = Path(__file__).resolve().parents[2] / ".hopsworks-tmp"
    temp_folder.mkdir(parents=True, exist_ok=True)
    temp_text = str(temp_folder)
    os.environ["TMPDIR"] = temp_text
    os.environ["TEMP"] = temp_text
    os.environ["TMP"] = temp_text
    tempfile.tempdir = temp_text
    tempfile.gettempdir = lambda: temp_text  # type: ignore[assignment]
    try:
        from hopsworks_common import constants as hopsworks_constants  # type: ignore

        hopsworks_constants.CLIENT.CERT_FOLDER_DEFAULT = temp_text
    except Exception:
        pass


@dataclass(slots=True)
class TrainingDataSource:
    dataframe: pd.DataFrame
    source: str
    local_path: Path | None = None
    feature_group: str | None = None
    feature_group_version: int | None = None


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    dataframe = pd.read_csv(path, low_memory=False)
    return dataframe


def _direct_hopsworks_read(feature_group: str, feature_group_version: int) -> pd.DataFrame:
    _patch_temp_environment()

    import hopsworks  # type: ignore

    host = (settings.hopsworks_host or "").strip()
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")

    project_handle = hopsworks.login(
        host=host,
        project=settings.hopsworks_project,
        api_key_value=settings.hopsworks_api_key,
    )
    feature_store = project_handle.get_feature_store()
    feature_group_handle = feature_store.get_feature_group(feature_group, feature_group_version)
    dataframe = feature_group_handle.read(dataframe_type="pandas")
    if hasattr(dataframe, "to_pandas"):
        dataframe = dataframe.to_pandas()
    if not isinstance(dataframe, pd.DataFrame):
        dataframe = pd.DataFrame(dataframe)
    return dataframe


def _export_hopsworks_via_helper(feature_group: str, feature_group_version: int) -> pd.DataFrame:
    python_exe = (settings.hopsworks_python_exe or "").strip()
    if not python_exe:
        raise RuntimeError("HOPSWORKS_PYTHON_EXE is not set")

    helper_script = Path(__file__).resolve().with_name("hopsworks_export.py")
    with tempfile.TemporaryDirectory(prefix="hopsworks-export-") as temp_dir:
        output_path = Path(temp_dir) / "ml_ready_dataset.csv"
        command = [python_exe, str(helper_script), str(output_path), feature_group, str(feature_group_version)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                "Hopsworks export failed "
                f"(exit={completed.returncode})\nstdout={completed.stdout}\nstderr={completed.stderr}"
            )
        return _read_csv(output_path)


def load_training_dataframe(
    *,
    source: str = "auto",
    local_path: str | Path | None = None,
    feature_group: str | None = None,
    feature_group_version: int | None = None,
) -> TrainingDataSource:
    feature_group_name = feature_group or settings.hopsworks_ml_feature_group
    feature_group_version_value = feature_group_version or settings.hopsworks_ml_feature_group_version
    local_dataset_path = Path(local_path or Path("data") / "gold" / "ml_ready_records.csv")

    normalized_source = source.strip().lower()
    if normalized_source not in {"auto", "local", "hopsworks"}:
        raise ValueError(f"Unsupported source: {source}")

    if normalized_source in {"auto", "hopsworks"} and settings.hopsworks_enabled:
        try:
            dataframe = _direct_hopsworks_read(feature_group_name, feature_group_version_value)
            logger.info(
                "Loaded %s rows from Hopsworks feature group %s v%s",
                len(dataframe),
                feature_group_name,
                feature_group_version_value,
            )
            return TrainingDataSource(
                dataframe=dataframe,
                source="hopsworks",
                feature_group=feature_group_name,
                feature_group_version=feature_group_version_value,
            )
        except Exception as direct_exc:
            logger.warning("Direct Hopsworks read failed: %s", direct_exc)

        if settings.hopsworks_python_exe:
            try:
                dataframe = _export_hopsworks_via_helper(feature_group_name, feature_group_version_value)
                logger.info(
                    "Loaded %s rows from Hopsworks via helper for feature group %s v%s",
                    len(dataframe),
                    feature_group_name,
                    feature_group_version_value,
                )
                return TrainingDataSource(
                    dataframe=dataframe,
                    source="hopsworks",
                    feature_group=feature_group_name,
                    feature_group_version=feature_group_version_value,
                )
            except Exception as helper_exc:
                logger.warning("Hopsworks helper export failed: %s", helper_exc)

        if normalized_source == "hopsworks":
            raise RuntimeError(
                "Requested Hopsworks training source, but both direct read and helper export failed."
            )

    dataframe = _read_csv(local_dataset_path)
    logger.info("Loaded %s rows from local CSV %s", len(dataframe), local_dataset_path)
    return TrainingDataSource(dataframe=dataframe, source="local", local_path=local_dataset_path)
