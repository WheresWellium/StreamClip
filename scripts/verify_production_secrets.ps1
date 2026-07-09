# Fail fast on weak or missing production secrets before docker compose up.
param(
    [string]$EnvFile = ".env.production"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$path = Join-Path $root $EnvFile

if (-not (Test-Path $path)) {
    Write-Host "FAIL: $EnvFile not found. Copy .env.production.example first." -ForegroundColor Red
    exit 1
}

$vars = @{}
Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    $vars[$key] = $val
}

$weak = @(
    "change-me",
    "change-me-strong-password",
    "change-me-minio-secret",
    "change-me-use-openssl-rand-hex-32",
    "change-me-in-production-use-openssl-rand",
    "streamclip_secret",
    "CHANGEME"
)

function Test-Weak([string]$value) {
    if (-not $value) { return $true }
    $lower = $value.ToLowerInvariant()
    foreach ($w in $weak) {
        if ($lower -eq $w.ToLowerInvariant()) { return $true }
    }
    return $false
}

$errors = @()
$warnings = @()

function Require-Key([string]$key, [int]$minLen = 8) {
    if (-not $vars.ContainsKey($key) -or -not $vars[$key]) {
        $script:errors += "Missing required: $key"
        return
    }
    if ($vars[$key].Length -lt $minLen) {
        $script:errors += "$key is too short (min $minLen chars)"
    }
    if (Test-Weak $vars[$key]) {
        $script:errors += "$key still uses a placeholder/default value"
    }
}

Require-Key "POSTGRES_PASSWORD" 16
Require-Key "STREAMCLIP_AUTH_SECRET_KEY" 32
Require-Key "MINIO_ROOT_PASSWORD" 16

if ($vars["STREAMCLIP_PUBLIC_BASE_URL"] -match "minio:9000") {
    $errors += "STREAMCLIP_PUBLIC_BASE_URL must be browser-reachable (not minio:9000)"
}

$distEnabled = ($vars["STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED"] -eq "true") -or
    ($vars["STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED"] -eq "true")
if ($distEnabled) {
    Require-Key "STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY" 32
    if (-not $vars["STREAMCLIP_DISTRIBUTION__WEB_ORIGIN"]) {
        $errors += "STREAMCLIP_DISTRIBUTION__WEB_ORIGIN required when distribution is enabled"
    }
}

if (-not $vars["STREAMCLIP_OBSERVABILITY__METRICS_API_KEY"]) {
    $warnings += "STREAMCLIP_OBSERVABILITY__METRICS_API_KEY unset - /metrics loopback-only in production"
}

if (-not $vars["OPS_WEBHOOK_URL"]) {
    $warnings += "OPS_WEBHOOK_URL unset - no Discord/Slack/agent inbox for bug_report / job_failed / stack_degraded (docs/OPS_ALERTING.md)"
}

if (-not $vars["STREAMCLIP_OBSERVABILITY__SENTRY_DSN"]) {
    $warnings += "STREAMCLIP_OBSERVABILITY__SENTRY_DSN unset - API/worker crashes will not appear in Sentry"
}

if (-not $vars["WINDOWS_CSC_LINK"] -and -not $vars["CSC_LINK"]) {
    $warnings += "WINDOWS_CSC_LINK / CSC_LINK unset - desktop installer will be UNSIGNED (§4.10)"
}

if (-not $vars["MACOS_CSC_NAME"] -and -not $vars["APPLE_ID"]) {
    $warnings += "MACOS_CSC_NAME / APPLE_ID unset - macOS DMG will be unsigned and not notarized (§5)"
}

if ($vars["STREAMCLIP_AUTH_ALLOW_ANONYMOUS"] -eq "true") {
    $warnings += "STREAMCLIP_AUTH_ALLOW_ANONYMOUS=true - fine for beta; set false for locked-down installs"
}

foreach ($w in $warnings) {
    Write-Host "WARN  $w" -ForegroundColor Yellow
}

if ($errors.Count -gt 0) {
    foreach ($e in $errors) {
        Write-Host "FAIL  $e" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Production secrets check passed ($EnvFile)." -ForegroundColor Green
exit 0
