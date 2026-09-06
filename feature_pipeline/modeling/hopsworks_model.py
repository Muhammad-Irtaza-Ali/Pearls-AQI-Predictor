from __future__ import annotations

import logging
from pathlib import Path
import shutil
import tempfile
from typing import Any

from feature_pipeline.config import settings

logger = logging.getLogger("hopsworks_model")


def _normalize_host(host: str) -> str:
    return host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")


def _login() -> Any:
    import hopsworks  # type: ignore

    if not settings.hopsworks_project or not settings.hopsworks_api_key or not settings.hopsworks_host:
        raise RuntimeError("Hopsworks model credentials are not configured")
    return hopsworks.login(
        host=_normalize_host(settings.hopsworks_host),
        project=settings.hopsworks_project,
        api_key_value=settings.hopsworks_api_key,
    )


def download_approved_model(cache_dir: str | Path | None = None) -> tuple[str, Any] | None:
    if not settings.hopsworks_enabled:
        return None

    destination = Path(cache_dir or Path(tempfile.gettempdir()) / "pearls-aqi-model")
    destination.mkdir(parents=True, exist_ok=True)

    try:
        project = _login()
        model_registry = project.get_model_registry()
        if settings.hopsworks_model_version is None:
            models = model_registry.get_models(settings.hopsworks_model_name)
            if not models:
                raise FileNotFoundError(f"No Hopsworks model found: {settings.hopsworks_model_name}")
            model = max(models, key=lambda item: int(item.version))
        else:
            model = model_registry.get_model(settings.hopsworks_model_name, settings.hopsworks_model_version)
        downloaded_path = model.download_model(destination.as_posix())
        model_path = Path(downloaded_path or destination)
        if not model_path.exists():
            model_path = destination
        artifact_paths = sorted(model_path.glob("*.joblib"))
        if not artifact_paths:
            raise FileNotFoundError(f"No .joblib artifact found in downloaded model: {model_path}")

        import joblib

        artifact_path = artifact_paths[0]
        return str(getattr(model, "name", settings.hopsworks_model_name)), joblib.load(artifact_path)
    except Exception as exc:
        logger.warning("Hopsworks model download failed: %s", exc)
        return None


def publish_model(
    artifact_path: str | Path,
    *,
    model_name: str | None = None,
    metrics: dict[str, float] | None = None,
) -> int | None:
    if not settings.hopsworks_enabled:
        return None

    try:
        project = _login()
        model_registry = project.get_model_registry()
        model = model_registry.python.create_model(
            name=model_name or settings.hopsworks_model_name,
            metrics=metrics or {},
            description="Approved AQI prediction model",
        )
        with tempfile.TemporaryDirectory(prefix="hopsworks-model-") as model_dir:
            model_file = Path(model_dir) / Path(artifact_path).name
            shutil.copy2(artifact_path, model_file)
            model.save(model_dir)
        logger.info("Published model to Hopsworks | name=%s | version=%s", model.name, model.version)
        return int(model.version)
    except Exception as exc:
        logger.warning("Hopsworks model publish failed: %s", exc)
        return None