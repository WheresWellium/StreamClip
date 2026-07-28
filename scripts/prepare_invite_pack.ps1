# Build Phase 0 invite pack from cohort.csv + issued keys (§8.15).
# Does NOT send email. Does NOT invent tester addresses.
#
# Modes:
#   Manual       — henna links + inline SCPRO key (existing cohort)
#   LemonSqueezy — henna links + personalized LS checkout URL (new cohort)
#
# Prerequisites (Manual):
#   docker compose exec -e PYTHONPATH=/app -T api python scripts/issue_beta_keys.py --csv cohort.csv `
#     > dist/phase0-invite-pack/keys.csv
#
# Prerequisites (LemonSqueezy):
#   Set STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL in environment or .env
#
#   .\scripts\prepare_invite_pack.ps1 -Mode LemonSqueezy -CohortCsv cohort.csv

param(
    [ValidateSet("Manual", "LemonSqueezy")]
    [string]$Mode = "Manual",
    [string]$KeysCsv = "",
    [string]$CohortCsv = "cohort.csv",
    [string]$OutDir = "dist/phase0-invite-pack",
    [string]$CheckoutUrl = "",
    [string]$HennaBase = "https://streamclip-henna.vercel.app",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$cohortPath = if ([IO.Path]::IsPathRooted($CohortCsv)) { $CohortCsv } else { Join-Path $root $CohortCsv }
if (-not (Test-Path $cohortPath)) {
    Write-Host "FAIL: cohort CSV not found: $cohortPath" -ForegroundColor Red
    exit 1
}

$checkoutBase = $CheckoutUrl
if (-not $checkoutBase) {
    $checkoutBase = $env:STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL
}
if ($Mode -eq "LemonSqueezy" -and -not $checkoutBase) {
    Write-Host "FAIL: LemonSqueezy mode requires checkout URL." -ForegroundColor Red
    Write-Host "Set STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL or pass -CheckoutUrl"
    exit 1
}

$keysPath = $null
if ($KeysCsv) {
    $keysPath = if ([IO.Path]::IsPathRooted($KeysCsv)) { $KeysCsv } else { Join-Path $root $KeysCsv }
}
if ($Mode -eq "Manual") {
    if (-not $keysPath -or -not (Test-Path $keysPath)) {
        Write-Host "FAIL: Manual mode requires -KeysCsv from issue_beta_keys.py output" -ForegroundColor Red
        exit 1
    }
}

$emailsDir = Join-Path (Join-Path $root $OutDir) "emails"
if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root $OutDir) | Out-Null
    New-Item -ItemType Directory -Force -Path $emailsDir | Out-Null
}

function Get-CohortRows {
    Import-Csv $cohortPath | ForEach-Object {
        $em = $_.email
        if (-not $em) { $em = $_.Email }
        $nm = $_.name
        if (-not $nm) { $nm = $_.Name }
        if ($em) {
            [PSCustomObject]@{
                Email = $em.Trim()
                Name  = if ($nm) { $nm.Trim() } else { ($em -split "@")[0] }
            }
        }
    }
}

function Get-KeyLast4 {
    param([string]$LicenseKey)
    if (-not $LicenseKey) {
        return ""
    }
    if ($LicenseKey.Length -le 4) {
        return $LicenseKey
    }
    return $LicenseKey.Substring($LicenseKey.Length - 4)
}

$keyByEmail = @{}
if ($Mode -eq "Manual" -and $keysPath) {
    Import-Csv $keysPath | ForEach-Object {
        $em = ($_.email).Trim()
        $key = ($_.license_key).Trim()
        if ($em -and $key) {
            $keyByEmail[$em.ToLowerInvariant()] = $key
        }
    }
}

$cohortRows = @(Get-CohortRows | Where-Object { $_.Email -and $_.Email -ne "email" })
if ($cohortRows.Count -eq 0) {
    Write-Host "FAIL: no cohort rows found in $cohortPath" -ForegroundColor Red
    exit 1
}

if ($Mode -eq "Manual") {
    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($member in $cohortRows) {
        $lookup = $member.Email.ToLowerInvariant()
        if (-not $keyByEmail.ContainsKey($lookup)) {
            $missing.Add($member.Email)
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host "FAIL: cohort/key mismatch. Missing license_key for $($missing.Count) cohort email(s):" -ForegroundColor Red
        foreach ($email in $missing) {
            Write-Host "  $email" -ForegroundColor Red
        }
        Write-Host "Do not re-run issue_beta_keys.py for re-send. Use the original keys CSV or fix cohort.csv." -ForegroundColor Yellow
        exit 1
    }
}

$manualTemplate = @"
Hi {name},

You're in - welcome to the qClip Phase 0 beta.

Get started (no GitHub account needed):
{henna_base}/BETA_DOWNLOAD/

Quickstart guide (step-by-step, ~15 min):
{henna_base}/BETA_TESTER_QUICKSTART/

Your license key - paste in Settings -> License after logging in:
{license_key}

Before activating, import the key into your local install (one time):
  docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py --key {license_key} --tier admin

This key gives you full access to every feature. No feature gates.

Use "Beta feedback" or "Report a bug" in the app header for support.
We read every submission even if you don't get an auto-reply yet.

Thanks,
Wellium
"@

$lsTemplate = @"
Hi {name},

You're in - welcome to the qClip Phase 0 beta.

1. Complete your free checkout (downloads + license key):
{checkout_url}

2. Install guide:
{henna_base}/BETA_DOWNLOAD/

3. Quickstart (~15 min):
{henna_base}/BETA_TESTER_QUICKSTART/

After checkout, paste your license key in Settings -> License.

Use "Beta feedback" or "Report a bug" in the app header for support.

Thanks,
Wellium
"@

$subject = "qClip Phase 0 beta - your access"
$count = 0
$indexRows = New-Object System.Collections.Generic.List[object]

foreach ($member in $cohortRows) {
    $email = $member.Email
    $name = $member.Name

    $safe = ($email -replace '[^a-zA-Z0-9._@-]', '_')

    if ($Mode -eq "Manual") {
        $lookup = $email.ToLowerInvariant()
        if (-not $keyByEmail.ContainsKey($lookup)) {
            Write-Host "WARN: no license_key for $email - skip" -ForegroundColor Yellow
            continue
        }
        $key = $keyByEmail[$lookup]
        $body = $manualTemplate.Replace("{name}", $name)
        $body = $body.Replace("{license_key}", $key)
        $body = $body.Replace("{henna_base}", $HennaBase.TrimEnd("/"))
        $indexRows.Add([PSCustomObject]@{
            email             = $email
            name              = $name
            license_key_last4 = Get-KeyLast4 $key
            email_file        = "emails/$safe.txt"
        })
    } else {
        $checkoutOut = & python "$root/scripts/build_ls_checkout_url.py" --base-url $checkoutBase --email $email --name $name 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAIL: build_ls_checkout_url for $email : $checkoutOut" -ForegroundColor Red
            exit 1
        }
        $checkoutLink = ($checkoutOut | Out-String).Trim()
        $body = $lsTemplate.Replace("{name}", $name)
        $body = $body.Replace("{checkout_url}", $checkoutLink)
        $body = $body.Replace("{henna_base}", $HennaBase.TrimEnd("/"))
        $indexRows.Add([PSCustomObject]@{
            email        = $email
            name         = $name
            checkout_url = $checkoutLink
            email_file   = "emails/$safe.txt"
        })
    }

    $file = Join-Path $emailsDir "$safe.txt"
    $content = "To: $email`r`nSubject: $subject`r`n`r`n$body"
    if (-not $DryRun) {
        Set-Content -Path $file -Value $content -Encoding utf8
    }
    $count++
}

$when = Get-Date -Format 'yyyy-MM-dd HH:mm'
$checklist = @(
    "Phase 0 invite pack - SEND CHECKLIST",
    "Generated: $when",
    "Mode: $Mode",
    "Count: $count",
    "",
    "Before send:",
    "- [ ] Rebuild this pack from cohort.csv + the original keys CSV",
    "- [ ] Dry-run this script and confirm cohort count matches output count",
    "- [ ] Compare index.csv last4 values against keys CSV (never paste full keys into docs/chat)",
    "- [ ] Open spot-check email bodies locally for name/key/download links",
    "- [ ] verify_ls_beta_config.ps1 (LemonSqueezy mode)",
    "- [ ] OPS_WEBHOOK_URL set (optional) - docs/OPS_ALERTING.md",
    "- [ ] Keys/checkout stored securely (do not commit dist/ or tmp/)",
    "",
    "After send:",
    "- [ ] H+0 monitor: docker compose exec -e PYTHONPATH=/app api python scripts/list_support_reports.py --limit 20"
) -join "`r`n"

$outRoot = Join-Path $root $OutDir
if ($DryRun) {
    Write-Host "DRY-RUN: would prepare $count email(s), mode=$Mode, out=$OutDir" -ForegroundColor Cyan
    if ($Mode -eq "Manual") {
        foreach ($row in $indexRows) {
            Write-Host "  $($row.email) key-last4=$($row.license_key_last4)"
        }
    }
    exit 0
}

$indexRows | Export-Csv -Path (Join-Path $outRoot "index.csv") -NoTypeInformation -Encoding utf8
Set-Content -Path (Join-Path $outRoot "PACK_SUMMARY.txt") -Value @(
    "Subject: $subject",
    "Mode: $Mode",
    "Generated: $when",
    "Count: $count",
    "Index redacts manual license keys to last4."
) -Encoding utf8
Set-Content -Path (Join-Path $outRoot "SEND_CHECKLIST.txt") -Value $checklist -Encoding utf8

Write-Host "Invite pack ready: $OutDir ($count emails, mode=$Mode)" -ForegroundColor Green
Write-Host "  index:     $OutDir\index.csv"
Write-Host "  summary:   $OutDir\PACK_SUMMARY.txt"
Write-Host "  checklist: $OutDir\SEND_CHECKLIST.txt"
Write-Host "  bodies:    $OutDir\emails\"
exit 0
