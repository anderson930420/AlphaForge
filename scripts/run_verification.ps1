$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$sampleData = Join-Path $repoRoot "sample_data\sample_ohlcv.csv"
$outputsDir = Join-Path $repoRoot "outputs"

if (-not (Test-Path $venvPython)) {
    throw "Missing Python executable at $venvPython"
}

if (-not (Test-Path $sampleData)) {
    throw "Missing sample data file at $sampleData"
}

Write-Host "Running pytest..."
& $venvPython -m pytest
if ($LASTEXITCODE -ne 0) {
    throw "pytest failed with exit code $LASTEXITCODE"
}

Write-Host "Running CLI smoke test..."
& $venvPython -m alphaforge.cli run `
    --data $sampleData `
    --symbol SAMPLE `
    --short-window 2 `
    --long-window 4 `
    --experiment-name smoke_test `
    --output-dir $outputsDir
if ($LASTEXITCODE -ne 0) {
    throw "CLI smoke test failed with exit code $LASTEXITCODE"
}

Write-Host "Verification complete."
