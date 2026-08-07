Push-Location (Join-Path $PSScriptRoot "..")
try {
    .\.venv\Scripts\python.exe feature_pipeline\run_pipeline.py
} finally {
    Pop-Location
}

