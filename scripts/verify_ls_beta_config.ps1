# Verify Lemon Squeezy beta distribution env (operator preflight).
param(
    [string]$CheckoutUrl = "",
    [switch]$SkipHttpCheck
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Lemon Squeezy beta config verify ===" -ForegroundColor Cyan

$required = @(
    "STREAMCLIP_COMMERCE__LEMON_SQUEEZY_API_KEY",
    "STREAMCLIP_COMMERCE__LEMON_SQUEEZY_WEBHOOK_SECRET",
    "STREAMCLIP_COMMERCE__LEMON_SQUEEZY_BETA_VARIANT_ID",
    "STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL"
)

$missing = @()
foreach ($name in $required) {
    $val = [Environment]::GetEnvironmentVariable($name)
    if (-not $val) {
        $missing += $name
        Write-Host "MISSING $name" -ForegroundColor Red
    } else {
        Write-Host "OK    $name (set)" -ForegroundColor Green
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Set missing vars in .env / .env.production (never commit secrets)." -ForegroundColor Yellow
    Write-Host "See docs/BETA_DISTRIBUTION.md"
    exit 1
}

$checkout = $CheckoutUrl
if (-not $checkout) {
    $checkout = $env:STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL
}

if (-not $SkipHttpCheck -and $checkout) {
    try {
        $resp = Invoke-WebRequest -Uri $checkout -Method Head -MaximumRedirection 0 -ErrorAction SilentlyContinue
        $code = $resp.StatusCode
    } catch {
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        } else {
            Write-Host "WARN  checkout HEAD failed: $($_.Exception.Message)" -ForegroundColor Yellow
            $code = 0
        }
    }
    if ($code -ge 200 -and $code -lt 400) {
        Write-Host "OK    checkout URL responds ($code)" -ForegroundColor Green
    } elseif ($code -eq 302 -or $code -eq 301) {
        Write-Host "OK    checkout URL redirects ($code)" -ForegroundColor Green
    } else {
        Write-Host "WARN  checkout URL HTTP $code — verify in LS dashboard" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Next: complete LS test-mode checkout, then clean-VM smoke (docs/BETA_DISTRIBUTION.md)." -ForegroundColor Cyan
exit 0
