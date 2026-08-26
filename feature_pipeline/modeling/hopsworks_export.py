from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
import sys
from typing import Any

import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
FEATURE_PIPELINE_DIR = CURRENT_DIR.parent
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))

from config import settings  # noqa: E402

logger = logging.getLogger("hopsworks_export")


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def _normalize_host(host: str) -> str:
    normalized = host.strip().rstrip("/")
    if normalized.startswith("https://"):
        normalized = normalized.removeprefix("https://")
    elif normalized.startswith("http://"):
        normalized = normalized.removeprefix("http://")
    return normalized


def _default_tmp_folder() -> Path:
    tmp_folder = Path(__file__).resolve().parents[2] / ".hopsworks-tmp"
    tmp_folder.mkdir(parents=True, exist_ok=True)
    return tmp_folder


def _patch_temp_environment(temp_folder: Path) -> None:
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


def _patch_hopsworks_temp_paths() -> None:
    from hopsworks_common.client import base as hopsworks_base_client
    from hopsworks_common.client import hopsworks as hopsworks_client

    temp_folder = _default_tmp_folder()
    _patch_temp_environment(temp_folder)

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


def _get_feature_group_dataframe(feature_group: str, feature_group_version: int) -> pd.DataFrame:
    import hopsworks  # type: ignore

    _patch_hopsworks_temp_paths()

    project_handle = hopsworks.login(
        host=_normalize_host(settings.hopsworks_host or ""),
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


def export_feature_group(
    output_path: str | Path,
    feature_group: str | None = None,
    feature_group_version: int | None = None,
) -> int:
    dataframe = _get_feature_group_dataframe(
        feature_group or settings.hopsworks_ml_feature_group,
        feature_group_version or settings.hopsworks_ml_feature_group_version,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)
    logger.info("Exported %s rows from Hopsworks to %s", len(dataframe), path)
    return int(len(dataframe))


def main() -> int:
    _configure_logging()

    if len(sys.argv) < 4:
        logger.error("Usage: hopsworks_export.py <output_csv> <feature_group> <feature_group_version>")
        return 2

    try:
        output_path = sys.argv[1]
        feature_group = sys.argv[2]
        feature_group_version = int(sys.argv[3])
        row_count = export_feature_group(output_path, feature_group, feature_group_version)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Failed to export Hopsworks feature group: %s", exc)
        return 1

    print(f"Exported {row_count} rows from Hopsworks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
