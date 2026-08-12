from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
FEATURE_PIPELINE_DIR = ROOT_DIR / "feature_pipeline"
if str(FEATURE_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_PIPELINE_DIR))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _record_key(record: dict[str, Any]) -> str:
    normalized = json.dumps(record, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _post_json(url: str, api_key: str, rows: list[dict[str, Any]]) -> None:
    request = Request(
        url,
        data=json.dumps(rows, default=str).encode("utf-8"),
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:  # nosec: B310 - trusted Supabase endpoint from .env
        response.read()


def _sync_supabase_layer(snapshot_dir: Path, table_name: str, supabase_url: str, api_key: str) -> int:
    run_files = sorted(snapshot_dir.glob("runs/*.csv"))
    if not run_files:
        print(f"No snapshots found for {snapshot_dir}")
        return 0

    inserted_rows = 0
    base_url = supabase_url.rstrip("/") + "/rest/v1/"
    for run_file in run_files:
        rows = _csv_rows(run_file)
        if not rows:
            continue
        for row in rows:
            row["record_key"] = _record_key(row)
        batch_size = 500
        for start_index in range(0, len(rows), batch_size):
            batch = rows[start_index : start_index + batch_size]
            url = f"{base_url}{table_name}?{urlencode({'on_conflict': 'record_key'})}"
            try:
                _post_json(url, api_key, batch)
                inserted_rows += len(batch)
                print(f"Supabase synced {len(batch)} rows from {run_file.name} -> {table_name}")
            except (HTTPError, URLError, TimeoutError) as exc:
                print(f"Supabase sync failed for {run_file.name} -> {table_name}: {exc}")
    return inserted_rows


def _sync_hopsworks_layer(snapshot_dir: Path, python_exe: str, host: str, project: str, api_key: str, feature_group: str, feature_group_version: str) -> int:
    sync_script = ROOT_DIR / "feature_pipeline" / "storage" / "hopsworks_sync_job.py"
    run_files = sorted(snapshot_dir.glob("runs/*.csv"))
    if not run_files:
        print(f"No snapshots found for {snapshot_dir}")
        return 0

    synced_rows = 0
    for run_file in run_files:
        rows = _csv_rows(run_file)
        if not rows:
            continue
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as temp_file:
            json.dump(rows, temp_file, default=str)
            temp_path = Path(temp_file.name)
        try:
            completed = subprocess.run(
                [python_exe, str(sync_script), str(temp_path), host, project, api_key, feature_group, feature_group_version],
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0:
                synced_rows += len(rows)
                print(f"Hopsworks synced {len(rows)} rows from {run_file.name} -> {feature_group}")
            else:
                print(
                    f"Hopsworks sync failed for {run_file.name}: exit={completed.returncode}\n"
                    f"stdout={completed.stdout.strip()}\nstderr={completed.stderr.strip()}"
                )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
    return synced_rows


def main() -> int:
    _load_dotenv(ROOT_DIR / ".env")

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_api_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    raw_table = os.getenv("SUPABASE_RAW_TABLE", "raw_records").strip()
    validated_table = os.getenv("SUPABASE_VALIDATED_TABLE", "validated_records").strip()

    hopsworks_enabled = os.getenv("HOPSWORKS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    hopsworks_python_exe = os.getenv("HOPSWORKS_PYTHON_EXE", "").strip()
    hopsworks_host = os.getenv("HOPSWORKS_HOST", "").strip()
    hopsworks_project = os.getenv("HOPSWORKS_PROJECT", "").strip()
    hopsworks_api_key = os.getenv("HOPSWORKS_API_KEY", "").strip()
    hopsworks_feature_group = os.getenv("HOPSWORKS_FEATURE_GROUP", "daily_aqi_features").strip()
    hopsworks_feature_group_version = os.getenv("HOPSWORKS_FEATURE_GROUP_VERSION", "1").strip()

    bronze_dir = ROOT_DIR / "data" / "bronze"
    silver_dir = ROOT_DIR / "data" / "silver"
    gold_dir = ROOT_DIR / "data" / "gold"

    if supabase_url and supabase_api_key:
        print("Syncing bronze snapshots to Supabase raw table...")
        bronze_count = _sync_supabase_layer(bronze_dir, raw_table, supabase_url, supabase_api_key)
        print("Syncing silver snapshots to Supabase validated table...")
        silver_count = _sync_supabase_layer(silver_dir, validated_table, supabase_url, supabase_api_key)
        print(f"Supabase sync complete | bronze_rows={bronze_count} | silver_rows={silver_count}")
    else:
        print("Supabase credentials missing; skipping Supabase sync.")

    if hopsworks_enabled and hopsworks_python_exe and hopsworks_host and hopsworks_project and hopsworks_api_key:
        print("Syncing gold snapshots to Hopsworks...")
        gold_count = _sync_hopsworks_layer(
            gold_dir,
            hopsworks_python_exe,
            hopsworks_host,
            hopsworks_project,
            hopsworks_api_key,
            hopsworks_feature_group,
            hopsworks_feature_group_version,
        )
        print(f"Hopsworks sync complete | gold_rows={gold_count}")
    else:
        print("Hopsworks credentials missing or disabled; skipping Hopsworks sync.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

