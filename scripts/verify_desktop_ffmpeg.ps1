# Verify ffmpeg bin resolution (ADR-001 §4.5).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Running ffmpeg bin resolution tests..."
python -m pytest tests/test_ffmpeg_bins.py tests/test_ffmpeg_utils.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ffmpeg verification passed." -ForegroundColor Green
