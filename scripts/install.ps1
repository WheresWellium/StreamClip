# qClip production installer (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> qClip install"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker is required. Install Docker Desktop first."
}

$composeVersion = docker compose version 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Error "docker compose plugin is required."
}

$EnvFile = if ($env:ENV_FILE) { $env:ENV_FILE } else { ".env.production" }
$ComposeFile = if ($env:COMPOSE_FILE) { $env:COMPOSE_FILE } else { "docker-compose.prod.yml" }

if (-not (Test-Path $EnvFile)) {
  if (Test-Path ".env.production.example") {
    Write-Host "==> Creating $EnvFile from .env.production.example"
    Copy-Item ".env.production.example" $EnvFile
    Write-Host "    Edit $EnvFile with your secrets, then re-run this script."
    exit 0
  }
  Write-Error "Missing $EnvFile"
}

Write-Host "==> Pulling images"
docker compose -f $ComposeFile --env-file $EnvFile pull

Write-Host "==> Starting stack"
docker compose -f $ComposeFile --env-file $EnvFile up -d

$ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$WebPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { "3000" }

Write-Host "==> Waiting for API health"
$healthy = $false
for ($i = 1; $i -le 30; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:$ApiPort/api/health" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) {
      $healthy = $true
      Write-Host "    API healthy"
      break
    }
  } catch {
    Start-Sleep -Seconds 2
  }
}

if (-not $healthy) {
  Write-Warning "API health check timed out — check: docker compose -f $ComposeFile logs api"
  exit 1
}

Write-Host ""
Write-Host "qClip is running:"
Write-Host "  Web UI:  http://localhost:$WebPort"
Write-Host "  API:     http://localhost:$ApiPort/docs"
Write-Host ""
Write-Host "Complete onboarding at http://localhost:$WebPort/onboarding"
