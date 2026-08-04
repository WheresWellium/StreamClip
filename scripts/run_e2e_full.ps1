#Requires -Version 5.1
<#
.SYNOPSIS
  Full Playwright e2e: mock UI journey + live happy-path (desktop sidecar or Docker API).

.DESCRIPTION
  1) web ui-journey (mock API - no backend required)
  2) live happy-path with E2E_RUN=1 against -ApiBase (default http://127.0.0.1:8765)
     Starts Next.js on :3000 with API_INTERNAL_URL if the web is not already up.

.EXAMPLE
  .\scripts\run_e2e_full.ps1
  .\scripts\run_e2e_full.ps1 -ApiBase http://localhost:8000
  .\scripts\run_e2e_full.ps1 -SkipLive
#>
param(
    [string]$ApiBase = "http://127.0.0.1:8765",
    [switch]$SkipLive,
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Web = Join-Path $Root "web"
$ApiBase = $ApiBase.TrimEnd("/")
$webUrl = "http://127.0.0.1:$WebPort"
$startedWeb = $false
$webProc = $null
$tmpDir = Join-Path $Root "tmp"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$npmCmd = if (Test-Path "$env:ProgramFiles\nodejs\npm.cmd") {
    "$env:ProgramFiles\nodejs\npm.cmd"
} else {
    "npm.cmd"
}

function Test-HttpOk([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $r.StatusCode -ge 200 -and $r.StatusCode -lt 500
    } catch {
        return $false
    }
}

Push-Location $Web
try {
    if (-not (Test-HttpOk $webUrl)) {
        Write-Host "Starting Next.js on :$WebPort (API_INTERNAL_URL=$ApiBase)..."
        $env:API_INTERNAL_URL = $ApiBase
        $env:NEXT_PUBLIC_DEV_TOOLS = "1"
        $outLog = Join-Path $tmpDir "e2e-next-stdout.log"
        $errLog = Join-Path $tmpDir "e2e-next-stderr.log"
        $webProc = Start-Process -FilePath $npmCmd -ArgumentList @("run", "dev", "--", "-p", "$WebPort") `
            -WorkingDirectory $Web -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $outLog `
            -RedirectStandardError $errLog
        $startedWeb = $true
        $deadline = (Get-Date).AddMinutes(3)
        while ((Get-Date) -lt $deadline) {
            if (Test-HttpOk $webUrl) { break }
            Start-Sleep -Seconds 2
        }
        if (-not (Test-HttpOk $webUrl)) {
            Write-Host "FAIL Next.js did not become ready on $webUrl" -ForegroundColor Red
            Write-Host "See $outLog / $errLog"
            exit 1
        }
    } else {
        Write-Host "Reusing existing Next.js at $webUrl"
    }

    $env:PLAYWRIGHT_BASE_URL = $webUrl

    Write-Host "=================================================================="
    Write-Host "  E2E: mock UI journey (create / review / failure / onboarding)"
    Write-Host "=================================================================="
    & $npmCmd run test:e2e:ui-journey
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL ui-journey exit=$LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "PASS ui-journey" -ForegroundColor Green

    if ($SkipLive) {
        Write-Host "SkipLive set - done."
        exit 0
    }

    Write-Host "=================================================================="
    Write-Host "  E2E: live happy-path (E2E_RUN=1) API=$ApiBase"
    Write-Host "=================================================================="

    if (-not (Test-HttpOk "$ApiBase/api/health")) {
        Write-Host "FAIL API not healthy at $ApiBase/api/health" -ForegroundColor Red
        Write-Host "Start desktop sidecar or Docker API, then re-run."
        exit 1
    }

    $env:E2E_RUN = "1"
    $env:E2E_API_BASE = $ApiBase
    npx playwright test e2e/happy-path.spec.ts
    $liveCode = $LASTEXITCODE
    Remove-Item Env:\E2E_RUN -ErrorAction SilentlyContinue
    Remove-Item Env:\E2E_API_BASE -ErrorAction SilentlyContinue

    if ($liveCode -ne 0) {
        Write-Host "FAIL live happy-path exit=$liveCode" -ForegroundColor Red
        exit $liveCode
    }
    Write-Host "PASS live happy-path" -ForegroundColor Green
    Write-Host "FULL E2E GREEN" -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
    if ($startedWeb -and $null -ne $webProc) {
        $pidToStop = $webProc.Id
        Write-Host "Stopping Next.js pid=$pidToStop..."
        Stop-Process -Id $pidToStop -Force -ErrorAction SilentlyContinue
        $filter = "ParentProcessId=$pidToStop"
        Get-CimInstance Win32_Process -Filter $filter -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }
}
