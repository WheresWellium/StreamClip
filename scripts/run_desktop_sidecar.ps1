# Launch desktop sidecar locally (dev — no PyInstaller).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:STREAMCLIP_CONFIG = "config/desktop.yaml"
$env:STREAMCLIP_WEB__SERVE_STATIC = "true"

Write-Host "Starting desktop sidecar on http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "  UI placeholder: /   API docs: /docs"
python -m desktop_sidecar
