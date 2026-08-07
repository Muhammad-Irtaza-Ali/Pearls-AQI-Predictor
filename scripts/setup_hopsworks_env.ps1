param(
    [string]$EnvironmentPath = ".venv-hopsworks"
)

$supportedPythonCommands = @("python3.13", "python3.12")
$pythonCommand = $null

foreach ($candidate in $supportedPythonCommands) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $pythonCommand = $candidate
        break
    }
}

if (-not $pythonCommand) {
    throw "Python 3.12 or 3.13 is required for Hopsworks. Install it first, then rerun this script."
}

& $pythonCommand -m venv $EnvironmentPath
$pythonExe = Join-Path $EnvironmentPath "Scripts\python.exe"
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install "hopsworks[python]" pandas

Write-Host "Hopsworks virtual environment created at $EnvironmentPath"
Write-Host "Set HOPSWORKS_PYTHON_EXE to: $(Resolve-Path $pythonExe)"

