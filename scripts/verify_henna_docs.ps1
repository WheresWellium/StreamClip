# Fail if customer henna docs drift from the desktop package version or fail a
# strict MkDocs build. Run before every git push (see scripts/githooks/pre-push)
# and from publish_desktop_release.ps1.
#
# Escape hatch (emergencies only): STREAMCLIP_SKIP_HENNA_VERIFY=1
param(
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($env:STREAMCLIP_SKIP_HENNA_VERIFY -eq "1") {
    Write-Host "WARN: STREAMCLIP_SKIP_HENNA_VERIFY=1 - henna docs gate skipped." -ForegroundColor Yellow
    exit 0
}

Write-Host "=== Henna docs gate (customer site vs package.json) ===" -ForegroundColor Cyan

$pkgPath = Join-Path $root "apps\desktop\package.json"
$indexPath = Join-Path $root "docs\index.md"
$betaDlPath = Join-Path $root "docs\BETA_DOWNLOAD.md"
$mkdocsPath = Join-Path $root "mkdocs.yml"

foreach ($p in @($pkgPath, $indexPath, $betaDlPath, $mkdocsPath)) {
    if (-not (Test-Path $p)) { Write-Error "Missing required file: $p" }
}

$version = (Get-Content $pkgPath -Raw | ConvertFrom-Json).version
if ([string]::IsNullOrWhiteSpace($version)) {
    Write-Error "apps/desktop/package.json has empty version"
}
Write-Host "package.json version: $version"

$index = Get-Content $indexPath -Raw -Encoding UTF8
$betaDl = Get-Content $betaDlPath -Raw -Encoding UTF8
$tickVersion = '`' + $version + '`'
$failures = [System.Collections.Generic.List[string]]::new()

function Add-Fail([string]$msg) {
    $script:failures.Add($msg) | Out-Null
    Write-Host "FAIL: $msg" -ForegroundColor Red
}

# 1) Henna home (only published page) must carry the shipping version
if (-not $index.Contains($tickVersion)) {
    Add-Fail "docs/index.md missing $tickVersion (must match apps/desktop/package.json)"
}
$bannerRe = [regex]::Escape("Current Windows installer:") + "\s*\*\*" + [regex]::Escape($tickVersion)
if ($index -notmatch $bannerRe) {
    Add-Fail "docs/index.md missing banner: Current Windows installer: **$tickVersion**"
}

# 2) Operator BETA_DOWNLOAD banner must stay in lockstep
if ($betaDl -match '>\s*\*\*Current Windows build:\*\*\s*`([^`]+)`') {
    $bannerVer = $Matches[1]
    if ($bannerVer -ne $version) {
        Add-Fail "docs/BETA_DOWNLOAD.md banner is '$bannerVer' but package.json is '$version'"
    }
} else {
    Add-Fail "docs/BETA_DOWNLOAD.md missing Current Windows build banner"
}

# 3) Stable latest Windows download URL (never a pinned stale Windows tag)
$latestWin = "https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe"
if (-not $index.Contains($latestWin)) {
    Add-Fail "docs/index.md must link Windows download to releases/latest/download/qClip-Setup-win-x64.exe"
}
# Mac Apple Silicon shares Latest with Windows (qClip-mac-arm64.dmg on same tag)
$latestMac = "https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg"
if (-not $index.Contains($latestMac)) {
    Add-Fail "docs/index.md must link Mac download to releases/latest/download/qClip-mac-arm64.dmg"
}
if ($betaDl -notmatch "releases/latest/download/qClip-mac-arm64\.dmg") {
    Add-Fail "docs/BETA_DOWNLOAD.md must link Mac CTA to releases/latest/download/qClip-mac-arm64.dmg"
}

# 4) Ban stale private-repo / invite-kit-only messaging on the customer page
$banned = @(
    "invite kit zip",
    "collaborator-only",
    "not from GitHub",
    "anonymous browser hits return 404",
    "we'll review it",
    "every submission is read"
)
$indexLower = $index.ToLowerInvariant()
foreach ($phrase in $banned) {
    if ($indexLower.Contains($phrase.ToLowerInvariant())) {
        Add-Fail "docs/index.md still contains stale phrase: '$phrase'"
    }
}

# 5) F13-honest feedback channel required on henna
if ($index -notmatch "issues/new\?template=beta-bug\.yml") {
    Add-Fail "docs/index.md must point Help at the GitHub beta-bug template (F13)"
}

# 6) Strict MkDocs build + assert only customer home is published
if (-not $SkipBuild) {
    Write-Host "Running: python -m mkdocs build --strict"
    # MkDocs prints warnings to stderr; do not let PowerShell NativeCommandError abort.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    python -m mkdocs build --strict 2>&1 | ForEach-Object { Write-Host $_ }
    $mkExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($mkExit -ne 0) {
        Add-Fail "mkdocs build --strict failed (exit $mkExit)"
    } else {
        $siteIndex = Join-Path $root "site\index.html"
        if (-not (Test-Path $siteIndex)) {
            Add-Fail "site/index.html missing after mkdocs build"
        } else {
            $built = Get-Content $siteIndex -Raw -Encoding UTF8
            if (-not $built.Contains($version)) {
                Add-Fail "site/index.html does not contain version $version after build"
            }
        }
        foreach ($leak in @(
            "site\BETA_DOWNLOAD\index.html",
            "site\DESKTOP_FAILURE_TAXONOMY\index.html",
            "site\MASTER_TODO\index.html"
        )) {
            if (Test-Path (Join-Path $root $leak)) {
                Add-Fail "Excluded page leaked into site/: $leak"
            }
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "Henna docs gate FAILED ($($failures.Count) issue(s))." -ForegroundColor Red
    Write-Host "Fix docs/index.md (+ BETA_DOWNLOAD.md) to match apps/desktop/package.json ($version),"
    Write-Host "then re-run: .\scripts\verify_henna_docs.ps1"
    Write-Host "Emergency skip only: `$env:STREAMCLIP_SKIP_HENNA_VERIFY='1'"
    exit 1
}

Write-Host "Henna docs gate PASSED (version $version)." -ForegroundColor Green
exit 0
