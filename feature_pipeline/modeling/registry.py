from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from modeling.trainer import TrainedModelResult, TrainingReport

logger = logging.getLogger("model_registry")


REGISTRY_DIR = Path("models") / "registry"
REGISTRY_PATH = REGISTRY_DIR / "model_registry.json"
CURRENT_MODEL_PATH = REGISTRY_DIR / "current_model.json"


@dataclass(slots=True)
class RegisteredModel:
    registry_id: str
    run_id: str
    model_name: str
    version: int
    approved: bool
    promoted_at: str | None
    artifact_path: str
    artifact_sha256: str
    metrics: dict[str, float]
    source: str
    training_started_at: str
    training_finished_at: str
    feature_group: str | None
    feature_group_version: int | None
    rows_total: int
    rows_train: int
    rows_test: int
    feature_columns: list[str]
    dataset_path: str | None
    manifest_path: str
    created_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_registry() -> dict[str, Any]:
    registry = _safe_load_json(REGISTRY_PATH)
    registry.setdefault("models", [])
    registry.setdefault("current_model", None)
    return registry


def write_registry(registry: dict[str, Any]) -> Path:
    _safe_write_json(REGISTRY_PATH, registry)
    return REGISTRY_PATH


def _load_current() -> dict[str, Any] | None:
    current = _safe_load_json(CURRENT_MODEL_PATH)
    return current or None


def get_current_model() -> dict[str, Any] | None:
    current = _load_current()
    if current:
        return current

    registry = load_registry()
    approved_models = [entry for entry in registry.get("models", []) if entry.get("approved")]
    if not approved_models:
        return None
    return sorted(
        approved_models,
        key=lambda entry: (
            float(entry.get("metrics", {}).get("rmse", float("inf"))),
            str(entry.get("created_at", "")),
        ),
    )[0]


def list_models() -> list[dict[str, Any]]:
    registry = load_registry()
    models = registry.get("models", [])
    return sorted(
        models,
        key=lambda entry: (
            str(entry.get("created_at", "")),
            str(entry.get("run_id", "")),
            str(entry.get("model_name", "")),
        ),
        reverse=True,
    )


def _next_version(models: list[dict[str, Any]], model_name: str) -> int:
    versions = [int(entry.get("version", 0)) for entry in models if entry.get("model_name") == model_name]
    return max(versions, default=0) + 1


def register_training_run(
    report: TrainingReport,
    results: list[TrainedModelResult],
    *,
    manifest_path: str | Path,
) -> tuple[Path, Path, RegisteredModel]:
    registry = load_registry()
    existing_models = list(registry.get("models", []))
    manifest_path = Path(manifest_path)
    current_model = get_current_model()
    current_best_rmse = float(current_model.get("metrics", {}).get("rmse", float("inf"))) if current_model else float("inf")
    proposed_best_result = min(results, key=lambda item: item.rmse) if results else None
    should_promote_new_model = bool(proposed_best_result and proposed_best_result.rmse <= current_best_rmse)

    promoted_model: RegisteredModel | None = None
    for result in results:
        artifact_path = Path(result.artifact_path)
        entry = RegisteredModel(
            registry_id=f"{report.run_id}:{result.name}",
            run_id=report.run_id,
            model_name=result.name,
            version=_next_version(existing_models, result.name),
            approved=should_promote_new_model and result.name == report.best_model,
            promoted_at=_now_iso() if should_promote_new_model and result.name == report.best_model else None,
            artifact_path=str(artifact_path),
            artifact_sha256=_sha256(artifact_path) if artifact_path.exists() else "",
            metrics={"mae": float(result.mae), "rmse": float(result.rmse), "r2": float(result.r2)},
            source=report.source,
            training_started_at=report.started_at,
            training_finished_at=report.finished_at,
            feature_group=report.feature_group,
            feature_group_version=report.feature_group_version,
            rows_total=report.rows_total,
            rows_train=report.rows_train,
            rows_test=report.rows_test,
            feature_columns=list(report.feature_columns),
            dataset_path=report.dataset_path,
            manifest_path=str(manifest_path),
            created_at=_now_iso(),
        )
        existing_models.append(asdict(entry))
        if entry.approved:
            promoted_model = entry

    if promoted_model is None and results:
        fallback_result = min(results, key=lambda item: item.rmse)
        if should_promote_new_model:
            promoted_model = RegisteredModel(
                registry_id=f"{report.run_id}:{fallback_result.name}",
                run_id=report.run_id,
                model_name=fallback_result.name,
                version=_next_version(existing_models, fallback_result.name),
                approved=True,
                promoted_at=_now_iso(),
                artifact_path=str(fallback_result.artifact_path),
                artifact_sha256=_sha256(Path(fallback_result.artifact_path)) if Path(fallback_result.artifact_path).exists() else "",
                metrics={"mae": float(fallback_result.mae), "rmse": float(fallback_result.rmse), "r2": float(fallback_result.r2)},
                source=report.source,
                training_started_at=report.started_at,
                training_finished_at=report.finished_at,
                feature_group=report.feature_group,
                feature_group_version=report.feature_group_version,
                rows_total=report.rows_total,
                rows_train=report.rows_train,
                rows_test=report.rows_test,
                feature_columns=list(report.feature_columns),
                dataset_path=report.dataset_path,
                manifest_path=str(manifest_path),
                created_at=_now_iso(),
            )
            existing_models.append(asdict(promoted_model))

    registry["models"] = existing_models
    approved_entries = [entry for entry in existing_models if entry.get("approved")]
    if approved_entries:
        approved_entries.sort(
            key=lambda entry: (
                float(entry.get("metrics", {}).get("rmse", float("inf"))),
                str(entry.get("created_at", "")),
            )
        )
        current_model = approved_entries[0]
        registry["current_model"] = current_model
        _safe_write_json(CURRENT_MODEL_PATH, current_model)
    else:
        registry["current_model"] = None

    registry_path = write_registry(registry)
    logger.info(
        "Registered training run %s | models=%s | approved=%s",
        report.run_id,
        len(results),
        bool(registry.get("current_model")),
    )
    return registry_path, CURRENT_MODEL_PATH, promoted_model or RegisteredModel(
        registry_id="",
        run_id=report.run_id,
        model_name="",
        version=0,
        approved=False,
        promoted_at=None,
        artifact_path="",
        artifact_sha256="",
        metrics={},
        source=report.source,
        training_started_at=report.started_at,
        training_finished_at=report.finished_at,
        feature_group=report.feature_group,
        feature_group_version=report.feature_group_version,
        rows_total=report.rows_total,
        rows_train=report.rows_train,
        rows_test=report.rows_test,
        feature_columns=list(report.feature_columns),
        dataset_path=report.dataset_path,
        manifest_path=str(manifest_path),
        created_at=_now_iso(),
    )


def resolve_registered_model(model_name: str | None = None) -> dict[str, Any] | None:
    models = list_models()
    if not models:
        return None

    if model_name:
        matching_models = [entry for entry in models if entry.get("model_name") == model_name]
        if matching_models:
            matching_models.sort(
                key=lambda entry: (
                    int(entry.get("version", 0)),
                    str(entry.get("created_at", "")),
                ),
                reverse=True,
            )
            return matching_models[0]

    current_model = get_current_model()
    if current_model:
        return current_model
    return models[0]
