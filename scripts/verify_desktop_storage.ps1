# Verify ADR-001 §4.3 local storage HTTP routes.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Running local storage HTTP tests..."
python -m pytest tests/test_local_storage_http.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Local storage verification passed." -ForegroundColor Green
