# One-shot OPS_WEBHOOK_URL mock verify (no Discord/Sentry secrets required).
# Starts a local HTTP receiver, POSTs a synthetic payload from the api container
# via host.docker.internal, asserts JSON arrived, then tears down.
#
# Does NOT read or write .env. Local OPS_WEBHOOK_URL may be unset - the probe
# injects a temporary mock URL into `docker compose exec`.
#
# Usage (repo root):
#   .\scripts\verify_ops_webhook.ps1 -Help
#   .\scripts\verify_ops_webhook.ps1 -DryRun          # preflight only (stack may be down)
#   .\scripts\verify_ops_webhook.ps1                  # full mock probe (stack must be up)
#
# Exit codes:
#   0  PASS (or DryRun READY / intentional SKIP with guidance)
#   1  FAIL (probe ran but delivery path broken)
#   2  SKIP (stack/python/docker missing - full verify not possible)
param(
    [switch]$Help,
    [switch]$DryRun,
    [int]$Port = 18765,
    [int]$TimeoutSec = 20
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Show-Help {
    @"
verify_ops_webhook.ps1 - mock OPS webhook path check (no real secrets)

  -Help      Show this help and exit 0
  -DryRun    Check python / docker / api container; print operator next steps; exit 0
  -Port      Local mock receiver port (default 18765)
  -TimeoutSec  Wait for mock payload (default 20)

Full verify (stack up):
  .\scripts\verify_ops_webhook.ps1

Operator go-live after PASS:
  1. Create Zapier/Make Catch Hook or custom JSON inbox
  2. Paste real OPS_WEBHOOK_URL into local .env / .env.production (never git)
  3. Optional Resend: SMTP_HOST=smtp.resend.com SMTP_USER=resend SMTP_PASSWORD=<api_key> ...
  4. Restart: docker compose up -d api worker beat
  5. Submit in-app Beta feedback; confirm receiver JSON

Docs: docs/OPS_ALERTING.md
"@ | Write-Host
}

if ($Help) {
    Show-Help
    exit 0
}

function Test-CommandAvailable([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-ApiContainerUp {
    try {
        $null = docker compose ps --status running --services 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        $services = docker compose ps --status running --services 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        return ($services -split "`r?`n" | Where-Object { $_.Trim() -eq "api" }).Count -gt 0
    }
    catch {
        return $false
    }
}

function Write-OperatorNextSteps {
    Write-Host ""
    Write-Host "Operator next steps (secrets stay local - never commit):" -ForegroundColor Cyan
    Write-Host "  Contract: POST JSON; Content-Type application/json; User-Agent StreamClip-Ops/1.0; no HMAC"
    Write-Host "  1. Create Zapier/Make Catch Hook or custom JSON inbox"
    Write-Host "     (native Discord/Slack hooks need an adapter - see docs/OPS_ALERTING.md)"
    Write-Host "  2. Set OPS_WEBHOOK_URL=... in .env and/or .env.production (api+worker+beat)"
    Write-Host "  3. Optional Resend SMTP (verified domain):"
    Write-Host "       SMTP_HOST=smtp.resend.com"
    Write-Host "       SMTP_PORT=587"
    Write-Host "       SMTP_USER=resend"
    Write-Host "       SMTP_PASSWORD=<resend_api_key>"
    Write-Host "       SMTP_FROM=alerts@your-verified-domain.example"
    Write-Host "       SMTP_STARTTLS=true"
    Write-Host "       BUG_REPORT_TO=ops@your-domain.example"
    Write-Host "  4. Restart: docker compose up -d api worker beat"
    Write-Host "  5. Live check: Help (?) -> Beta feedback -> confirm JSON + ops_webhook_sent logs"
    Write-Host "  Docs: docs/OPS_ALERTING.md"
}

$pythonOk = Test-CommandAvailable "python"
$dockerOk = Test-CommandAvailable "docker"
$apiUp = $false
if ($dockerOk) {
    $apiUp = Test-ApiContainerUp
}

Write-Host "Preflight:" -ForegroundColor Cyan
Write-Host ("  python : {0}" -f ($(if ($pythonOk) { "ok" } else { "MISSING" })))
Write-Host ("  docker : {0}" -f ($(if ($dockerOk) { "ok" } else { "MISSING" })))
Write-Host ("  api    : {0}" -f ($(if ($apiUp) { "running" } else { "not running" })))
Write-Host "  Note   : local OPS_WEBHOOK_URL is not required for mock verify (injected in-container)."

if ($DryRun) {
    if ($pythonOk -and $dockerOk -and $apiUp) {
        Write-Host "READY: run .\scripts\verify_ops_webhook.ps1 (without -DryRun) for mock PASS." -ForegroundColor Green
        Write-OperatorNextSteps
        exit 0
    }
    Write-Host "SKIP (DryRun): stack or toolchain incomplete - mock probe not run." -ForegroundColor Yellow
    if (-not $pythonOk) { Write-Host "  Fix: install Python 3 and ensure 'python' is on PATH" }
    if (-not $dockerOk) { Write-Host "  Fix: install Docker Desktop / docker CLI" }
    if ($dockerOk -and -not $apiUp) {
        Write-Host "  Fix: from repo root, start stack then retry:"
        Write-Host "       docker compose up -d api worker beat"
    }
    Write-OperatorNextSteps
    exit 0
}

if (-not $pythonOk) {
    Write-Host "SKIP: python not on PATH - cannot start mock receiver." -ForegroundColor Yellow
    Write-Host "  Run: .\scripts\verify_ops_webhook.ps1 -DryRun   for checklist without stack." -ForegroundColor DarkGray
    Write-OperatorNextSteps
    exit 2
}
if (-not $dockerOk) {
    Write-Host "SKIP: docker not on PATH - cannot exec into api container." -ForegroundColor Yellow
    Write-OperatorNextSteps
    exit 2
}
if (-not $apiUp) {
    Write-Host "SKIP: api container not running - mock verify needs Docker stack." -ForegroundColor Yellow
    Write-Host "  Start: docker compose up -d api worker beat" -ForegroundColor DarkGray
    Write-Host "  Or:   .\scripts\verify_ops_webhook.ps1 -DryRun" -ForegroundColor DarkGray
    Write-OperatorNextSteps
    exit 2
}

$outFile = Join-Path $env:TEMP "streamclip-ops-webhook-verify.jsonl"
if (Test-Path $outFile) { Remove-Item $outFile -Force }

$receiverPy = @"
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

OUT = sys.argv[1]
PORT = int(sys.argv[2])

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        with open(OUT, "ab") as f:
            f.write(body + b"\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *args):
        return

HTTPServer(("0.0.0.0", PORT), H).handle_request()
"@

$pyFile = Join-Path $env:TEMP "streamclip_ops_receiver.py"
Set-Content -Path $pyFile -Value $receiverPy -Encoding utf8

Write-Host "Starting mock OPS receiver on :$Port ..." -ForegroundColor Cyan
$proc = Start-Process -FilePath "python" -ArgumentList @($pyFile, $outFile, "$Port") `
    -PassThru -WindowStyle Hidden

try {
    # Give the listener a moment before the container POSTs (avoids first-attempt refuse).
    Start-Sleep -Milliseconds 1500
    if ($proc.HasExited) {
        Write-Host "FAIL: mock receiver exited early (exit $($proc.ExitCode))" -ForegroundColor Red
        exit 1
    }

    $hook = "http://host.docker.internal:$Port/ops"
    Write-Host "POSTing synthetic payload from api container -> $hook" -ForegroundColor Cyan
    docker compose exec -T -e "OPS_WEBHOOK_URL=$hook" api python -c @"
from core.notify.ops_webhook import post_ops_webhook
ok = post_ops_webhook({
    'event': 'ops_webhook_verify',
    'app': 'streamclip',
    'message': 'verify_ops_webhook.ps1 synthetic probe',
})
print('POST_OK' if ok else 'POST_FAIL')
raise SystemExit(0 if ok else 1)
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: post_ops_webhook returned false (container cannot reach host:$Port?)" -ForegroundColor Red
        Write-Host "  Tip: Docker Desktop must resolve host.docker.internal; firewall must allow :$Port" -ForegroundColor DarkGray
        exit 1
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path $outFile) -and ((Get-Item $outFile).Length -gt 0)) { break }
        Start-Sleep -Milliseconds 200
    }

    if (-not (Test-Path $outFile) -or ((Get-Item $outFile).Length -eq 0)) {
        Write-Host "FAIL: no payload received at mock receiver" -ForegroundColor Red
        exit 1
    }

    $body = Get-Content $outFile -Raw
    if ($body -notmatch 'ops_webhook_verify') {
        Write-Host "FAIL: payload missing event ops_webhook_verify" -ForegroundColor Red
        Write-Host $body
        exit 1
    }

    Write-Host "PASS: OPS webhook path verified (mock received ops_webhook_verify)." -ForegroundColor Green
    Write-Host "Payload file: $outFile" -ForegroundColor DarkGray
    Write-Host "Mock only - .env was not modified." -ForegroundColor DarkGray
    Write-OperatorNextSteps
    exit 0
}
finally {
    if ($null -ne $proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pyFile -Force -ErrorAction SilentlyContinue
}
