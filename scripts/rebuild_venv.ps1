param(
    [Parameter(Mandatory = $true)]
    [string] $PythonExe
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"

if (-not (Test-Path $pyprojectPath)) {
    throw "pyproject.toml not found at $pyprojectPath"
}

if (Test-Path $venvPath) {
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

& $PythonExe --version
if ($LASTEXITCODE -ne 0) {
    throw "Python executable could not be launched: $PythonExe"
}

& $PythonExe -m venv $venvPath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create virtual environment"
}

$venvPython = Join-Path $venvPath "Scripts\\python.exe"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip"
}

& $venvPython -m pip install -e "$repoRoot[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install project dependencies"
}

Write-Host "Virtual environment rebuilt at $venvPath"
Write-Host "Next step: powershell -ExecutionPolicy Bypass -File .\\scripts\\run_verification.ps1"
