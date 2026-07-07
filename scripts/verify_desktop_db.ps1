# Verify ADR-001 §4.1 SQLite database profile (migrations + CRUD smoke test).
# Runs on host Python — no Docker required.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Installing aiosqlite if missing..." -ForegroundColor Cyan
python -m pip install -q aiosqlite

Write-Host "Running SQLite profile tests..." -ForegroundColor Cyan
python -m pytest tests/test_sqlite_profile.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "SQLite desktop DB verification passed." -ForegroundColor Green
