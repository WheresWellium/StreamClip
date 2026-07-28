# SMTP-only ops alerting verify (Phase 0 default path - no third-party connector).
#
# Confirms the api/worker containers can actually deliver operator email:
#   -DryRun  reports which SMTP_* vars the containers see (values redacted)
#   default  sends one real test email through core.notify.email.send_email
#
# Reads nothing from .env directly - it inspects the running containers, so it
# reflects what the app truly has, including compose interpolation mistakes.
#
# Usage (repo root):
#   .\scripts\verify_smtp_alerting.ps1 -Help
#   .\scripts\verify_smtp_alerting.ps1 -DryRun
#   .\scripts\verify_smtp_alerting.ps1
#   .\scripts\verify_smtp_alerting.ps1 -To me@example.com
#
# Exit codes:
#   0  PASS (or DryRun READY)
#   1  FAIL (config present but delivery broken)
#   2  SKIP (docker/stack/config missing - cannot verify)
param(
    [switch]$Help,
    [switch]$DryRun,
    [string]$To = "",
    [string]$Service = "api"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Show-Help {
    @"
verify_smtp_alerting.ps1 - operator email alerting check (SMTP-only path)

  -Help      Show this help and exit 0
  -DryRun    Report container SMTP config (redacted); no email sent; exit 0
  -To        Override recipient for the test send (default: BUG_REPORT_TO)
  -Service   Container to send from (default: api; use worker to test that too)

What alerting needs (set in local .env / .env.production, never git):
  SMTP_HOST       e.g. smtp.resend.com   (unset = email disabled)
  SMTP_PORT       default 587
  SMTP_USER       e.g. resend
  SMTP_PASSWORD   provider API key / app password
  SMTP_FROM       must be a verified sender for your provider
  SMTP_STARTTLS   true
  BUG_REPORT_TO   where operator alerts land

Covers these events once configured:
  bug_report / beta_feedback  - emailed by the worker on submit
  job_failed / stack_degraded - emailed when OPS_WEBHOOK_URL is unset

After a PASS:
  1. docker compose up -d api worker beat   (pick up env)
  2. Submit in-app Help (?) -> Beta feedback
  3. Confirm the message arrives in BUG_REPORT_TO

Docs: docs/OPS_ALERTING.md
"@ | Write-Host
}

if ($Help) {
    Show-Help
    exit 0
}

function Test-DockerAvailable {
    return [bool](Get-Command docker -ErrorAction SilentlyContinue)
}

function Test-ServiceRunning([string]$Name) {
    try {
        $services = docker compose ps --status running --services 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        return ($services -split "`r?`n" | Where-Object { $_.Trim() -eq $Name }).Count -gt 0
    }
    catch {
        return $false
    }
}

Write-Host "=== SMTP alerting verify ===" -ForegroundColor Cyan

if (-not (Test-DockerAvailable)) {
    Write-Host "SKIP: docker not found - cannot inspect containers." -ForegroundColor Yellow
    exit 2
}
if (-not (Test-ServiceRunning $Service)) {
    Write-Host "SKIP: '$Service' container is not running. Start it first:" -ForegroundColor Yellow
    Write-Host "  docker compose up -d api worker beat"
    exit 2
}

# Read config from inside the container: what the app sees is the only truth.
$reportScript = @'
import json, os
keys = ["SMTP_HOST","SMTP_PORT","SMTP_USER","SMTP_FROM","SMTP_STARTTLS","BUG_REPORT_TO"]
out = {k: os.environ.get(k, "") for k in keys}
out["SMTP_PASSWORD_set"] = bool(os.environ.get("SMTP_PASSWORD"))
out["OPS_WEBHOOK_URL_set"] = bool(os.environ.get("OPS_WEBHOOK_URL") or os.environ.get("N8N_OPS_WEBHOOK_URL"))
print(json.dumps(out))
'@

$raw = $reportScript | docker compose exec -T $Service python - 2>$null
if ($LASTEXITCODE -ne 0 -or -not $raw) {
    Write-Host "SKIP: could not read env from '$Service'." -ForegroundColor Yellow
    exit 2
}

$conf = $raw | ConvertFrom-Json
$recipient = if ($To) { $To } else { $conf.BUG_REPORT_TO }

Write-Host ("Service:        {0}" -f $Service)
Write-Host ("SMTP_HOST:      {0}" -f $(if ($conf.SMTP_HOST) { $conf.SMTP_HOST } else { "(unset)" }))
Write-Host ("SMTP_PORT:      {0}" -f $conf.SMTP_PORT)
Write-Host ("SMTP_USER:      {0}" -f $(if ($conf.SMTP_USER) { $conf.SMTP_USER } else { "(unset)" }))
Write-Host ("SMTP_PASSWORD:  {0}" -f $(if ($conf.SMTP_PASSWORD_set) { "set (redacted)" } else { "(unset)" }))
Write-Host ("SMTP_FROM:      {0}" -f $conf.SMTP_FROM)
Write-Host ("SMTP_STARTTLS:  {0}" -f $conf.SMTP_STARTTLS)
Write-Host ("BUG_REPORT_TO:  {0}" -f $(if ($conf.BUG_REPORT_TO) { $conf.BUG_REPORT_TO } else { "(unset)" }))
Write-Host ("OPS_WEBHOOK_URL:{0}" -f $(if ($conf.OPS_WEBHOOK_URL_set) { " set - webhook wins over email" } else { " unset - email is the alert channel" }))

$missing = @()
if (-not $conf.SMTP_HOST) { $missing += "SMTP_HOST" }
if (-not $recipient) { $missing += "BUG_REPORT_TO (or pass -To)" }

if ($DryRun) {
    Write-Host ""
    if ($missing.Count -gt 0) {
        Write-Host ("READY (not configured yet) - still need: {0}" -f ($missing -join ", ")) -ForegroundColor Yellow
        Write-Host "Add them to local .env / .env.production, then: docker compose up -d api worker beat"
    }
    else {
        Write-Host "READY - config present. Run without -DryRun to send a test email." -ForegroundColor Green
    }
    exit 0
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host ("SKIP: email not configured - missing {0}" -f ($missing -join ", ")) -ForegroundColor Yellow
    Write-Host "Forms still persist to the bug_reports table; only notification is off."
    Write-Host "See docs/OPS_ALERTING.md for provider settings."
    exit 2
}

Write-Host ""
Write-Host "Sending test email to $recipient ..." -ForegroundColor Cyan

# Exercise the real send path used by the notify tasks.
$sendScript = @'
import os, sys
from core.notify.email import send_email
to = os.environ["SC_VERIFY_TO"]
ok = send_email(
    to=to,
    subject="[qClip ops] SMTP alerting verify",
    body=(
        "This is a qClip operator alerting test.\n\n"
        "If you received this, bug_report / beta_feedback / job_failed /\n"
        "stack_degraded alerts will reach this inbox.\n"
    ),
)
print("SEND_OK" if ok else "SEND_FAIL")
sys.exit(0 if ok else 1)
'@

$result = $sendScript | docker compose exec -T -e "SC_VERIFY_TO=$recipient" $Service python - 2>&1
$sendExit = $LASTEXITCODE
$result | Write-Host

if ($sendExit -eq 0 -and ($result -match "SEND_OK")) {
    Write-Host ""
    Write-Host "PASS: test email accepted by $($conf.SMTP_HOST)." -ForegroundColor Green
    Write-Host "Check $recipient (and spam) to confirm delivery."
    Write-Host ""
    Write-Host "Next: submit in-app Help (?) -> Beta feedback for an end-to-end check."
    exit 0
}

Write-Host ""
Write-Host "FAIL: SMTP delivery failed. Common causes:" -ForegroundColor Red
Write-Host "  - SMTP_FROM is not a verified sender/domain with your provider"
Write-Host "  - wrong API key in SMTP_PASSWORD, or SMTP_USER should be the provider's fixed user"
Write-Host "  - port/TLS mismatch (587 + STARTTLS true is standard)"
Write-Host "  - container cannot reach the SMTP host (network/firewall)"
Write-Host "Docs: docs/OPS_ALERTING.md"
exit 1
