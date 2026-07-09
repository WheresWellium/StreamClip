# Build Phase 0 invite pack from cohort.csv + issued keys (§8.15).
# Does NOT send email. Does NOT invent tester addresses.
#
# Prerequisites:
#   1. Copy cohort.example.csv → cohort.csv and put real emails (gitignored)
#   2. Issue keys (writes keys CSV):
#        docker compose exec -e PYTHONPATH=/app -T api `
#          python scripts/issue_beta_keys.py --csv cohort.csv `
#          > dist/phase0-invite-pack/keys.csv
#   3. Run this script:
#        .\scripts\prepare_invite_pack.ps1 -KeysCsv dist\phase0-invite-pack\keys.csv
#
# Output (gitignored under dist/):
#   dist/phase0-invite-pack/keys.csv (if you redirected issue_beta_keys here)
#   dist/phase0-invite-pack/emails/<email-safe>.txt  — ready-to-paste bodies
#   dist/phase0-invite-pack/SEND_CHECKLIST.txt

param(
    [Parameter(Mandatory = $true)]
    [string]$KeysCsv,
    [string]$CohortCsv = "cohort.csv",
    [string]$OutDir = "dist/phase0-invite-pack"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$keysPath = if ([IO.Path]::IsPathRooted($KeysCsv)) { $KeysCsv } else { Join-Path $root $KeysCsv }
$cohortPath = if ([IO.Path]::IsPathRooted($CohortCsv)) { $CohortCsv } else { Join-Path $root $CohortCsv }

if (-not (Test-Path $keysPath)) {
    Write-Host "FAIL: keys CSV not found: $keysPath" -ForegroundColor Red
    Write-Host "Issue keys first, e.g.:"
    Write-Host '  docker compose exec -e PYTHONPATH=/app -T api python scripts/issue_beta_keys.py --csv cohort.csv > dist/phase0-invite-pack/keys.csv'
    exit 1
}

New-Item -ItemType Directory -Force -Path (Join-Path $root $OutDir) | Out-Null
$emailsDir = Join-Path (Join-Path $root $OutDir) "emails"
New-Item -ItemType Directory -Force -Path $emailsDir | Out-Null

# Optional name map from cohort.csv (email,name)
$names = @{}
if (Test-Path $cohortPath) {
    Import-Csv $cohortPath | ForEach-Object {
        $em = $_.email
        if (-not $em) { $em = $_.Email }
        $nm = $_.name
        if (-not $nm) { $nm = $_.Name }
        if ($em) {
            $names[$em.Trim().ToLowerInvariant()] = if ($nm) { $nm.Trim() } else { "" }
        }
    }
}

$template = @"
Hi {name},

You're in - welcome to the StreamClip Phase 0 beta.

Get started (no GitHub account needed):
https://streamclip-henna.vercel.app/BETA_DOWNLOAD/

Quickstart guide (step-by-step, ~15 min):
https://streamclip-henna.vercel.app/BETA_TESTER_QUICKSTART/

Your license key - paste in Settings -> License after logging in:
{license_key}

This key gives you full access to every feature. No feature gates.

Use "Beta feedback" or "Report a bug" in the app header for support.
We read every submission even if you don't get an auto-reply yet.

Thanks,
Wellium
"@

$subject = "StreamClip Phase 0 beta - your access"
$rows = Import-Csv $keysPath
$count = 0
$index = New-Object System.Collections.Generic.List[string]
$index.Add("Subject: $subject")
$index.Add("")
$index.Add("email,name,license_key,email_file")

foreach ($row in $rows) {
    $email = ($row.email).Trim()
    if (-not $email -or $email -eq "email") { continue }
    $key = ($row.license_key).Trim()
    if (-not $key) {
        Write-Host "WARN: missing license_key for $email - skip" -ForegroundColor Yellow
        continue
    }
    $lookup = $email.ToLowerInvariant()
    $name = ""
    if ($names.ContainsKey($lookup)) {
        $name = $names[$lookup]
    }
    if (-not $name) {
        $name = ($email -split "@")[0]
    }
    $body = $template.Replace("{name}", $name).Replace("{license_key}", $key)
    $safe = ($email -replace '[^a-zA-Z0-9._@-]', '_')
    $file = Join-Path $emailsDir "$safe.txt"
    $content = "To: $email`r`nSubject: $subject`r`n`r`n$body"
    Set-Content -Path $file -Value $content -Encoding utf8
    $index.Add("$email,$name,$key,emails/$safe.txt")
    $count++
}

$when = Get-Date -Format 'yyyy-MM-dd HH:mm'
$checklist = @(
    "Phase 0 invite pack - SEND CHECKLIST",
    "Generated: $when",
    "Count: $count",
    "",
    "Before send:",
    "- [ ] OPS_WEBHOOK_URL set (optional but recommended) - docs/OPS_ALERTING.md",
    "- [ ] BETA_ON_CALL.md TBD contacts filled",
    "- [ ] Keys stored in password manager (do not commit keys.csv)",
    "",
    "Send each file under emails/ via your mail client (copy body).",
    "Do not commit this folder (dist/ is gitignored).",
    "",
    "After send:",
    "- [ ] H+0 monitor: docker compose exec -e PYTHONPATH=/app api python scripts/list_support_reports.py --limit 20",
    "- [ ] BETA_GO_LIVE.md section 7 launch-day table"
) -join "`r`n"

$outRoot = Join-Path $root $OutDir
Set-Content -Path (Join-Path $outRoot "index.csv") -Value ($index -join "`n") -Encoding utf8
Set-Content -Path (Join-Path $outRoot "SEND_CHECKLIST.txt") -Value $checklist -Encoding utf8

Write-Host "Invite pack ready: $OutDir ($count emails)" -ForegroundColor Green
Write-Host "  index:     $OutDir\index.csv"
Write-Host "  checklist: $OutDir\SEND_CHECKLIST.txt"
Write-Host "  bodies:    $OutDir\emails\"
exit 0
