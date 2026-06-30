# StreamClip — start full stack (Docker)
# Usage: .\scripts\start.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Find-Docker {
    $paths = @(
        "docker",
        "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
        "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe"
    )
    foreach ($p in $paths) {
        if (Get-Command $p -ErrorAction SilentlyContinue) {
            return (Get-Command $p).Source
        }
        if (Test-Path $p) { return $p }
    }
    return $null
}

$docker = Find-Docker
if (-not $docker) {
    Write-Host ""
    Write-Host "Docker not found yet." -ForegroundColor Yellow
    Write-Host "1. Finish installing Docker Desktop"
    Write-Host "2. Open Docker Desktop and wait until it says 'Engine running'"
    Write-Host "3. Close and reopen this terminal, then run: .\scripts\start.ps1"
    Write-Host ""
    exit 1
}

Write-Host "Using Docker: $docker" -ForegroundColor Cyan
Write-Host "Building and starting StreamClip (first run may take several minutes)..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Web UI:    http://localhost:3000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  MinIO:     http://localhost:9001  (streamclip / streamclip_secret)"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services."
Write-Host ""

& $docker compose up --build
