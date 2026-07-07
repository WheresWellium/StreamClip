# Build static Next.js UI for desktop sidecar (ADR-001 §4.7).
# Copies export to static/ui for FastAPI to serve.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$uiOut = Join-Path $root "static\ui"
$webDir = Join-Path $root "web"
$middleware = Join-Path $webDir "middleware.ts"
$middlewareDev = Join-Path $webDir "middleware.dev.ts"
$middlewareMoved = $false

Write-Host "Building static UI (NEXT_STATIC_EXPORT=1)..." -ForegroundColor Cyan
Push-Location $webDir
$env:NEXT_STATIC_EXPORT = "1"
$env:NEXT_PRIVATE_WORKER_THREADS = "false"

# Next.js static export does not support middleware — stash it for the build.
if (Test-Path $middleware) {
    if (Test-Path $middlewareDev) { Remove-Item $middlewareDev -Force }
    Move-Item $middleware $middlewareDev
    $middlewareMoved = $true
}

npm run build
$buildOk = $LASTEXITCODE -eq 0

if ($middlewareMoved -and (Test-Path $middlewareDev)) {
    Move-Item $middlewareDev $middleware
}

Pop-Location

if (-not $buildOk) {
    Write-Host "Static export failed." -ForegroundColor Red
    exit 1
}

$exportDir = Join-Path $webDir "out"
if (-not (Test-Path $exportDir)) {
    Write-Host "ERROR: web/out not found after build" -ForegroundColor Red
    exit 1
}

Write-Host "Copying web/out -> static/ui ..."
if (Test-Path $uiOut) { Remove-Item -Recurse -Force $uiOut }
New-Item -ItemType Directory -Path $uiOut | Out-Null
Copy-Item -Recurse (Join-Path $exportDir "*") $uiOut

Write-Host "Static UI ready at static/ui/" -ForegroundColor Green
