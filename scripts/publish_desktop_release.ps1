# Build Windows installer locally and optionally upload to GitHub Releases.
# Also uploads latest.yml (electron-updater) when present and bumps BETA_DOWNLOAD.md.
# Signing runbook: docs/DESKTOP_SIGNING.md
#
# Unsigned beta (current):  .\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N
# Signed gate:              .\scripts\publish_desktop_release.ps1 -Version ... -SkipBuild -RequireSigned
# No upload / no docs bump: .\scripts\publish_desktop_release.ps1 -Version ... -SkipBuild -DryRun
param(
    [string]$Version = "",
    [switch]$SkipBuild,
    [switch]$PublishOnly,
    [switch]$NoDocsBump,
    [switch]$RequireSigned,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Single source of truth for the release version is apps/desktop/package.json
# (electron-builder stamps latest.yml from it). Deriving $Version from there —
# and asserting they match — prevents the recurring drift where package.json,
# the git tag, and latest.yml disagree and auto-update silently stops working.
$pkgPath = Join-Path $root "apps\desktop\package.json"
$pkgVersion = (Get-Content $pkgPath -Raw | ConvertFrom-Json).version
if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = $pkgVersion
    Write-Host "Version not passed; using package.json: $Version" -ForegroundColor Cyan
} elseif ($Version -ne $pkgVersion) {
    Write-Error "Version mismatch: -Version '$Version' != apps/desktop/package.json '$pkgVersion'. Bump package.json or pass the matching -Version so the tag, installer, and latest.yml agree."
}

$releaseDir = Join-Path $root "apps\desktop\release"
$installer = Join-Path $releaseDir "qClip-Setup-win-x64.exe"
$latestYml = Join-Path $releaseDir "latest.yml"

if (-not $PublishOnly -and -not $SkipBuild) {
    if ($DryRun) {
        Write-Host "Dry-run: would build via build_desktop_installer.ps1 (use -SkipBuild to inspect an existing exe)." -ForegroundColor Yellow
    } else {
        Write-Host "=== Building qClip Windows installer ===" -ForegroundColor Cyan
        & "$PSScriptRoot\build_desktop_installer.ps1"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} elseif ($SkipBuild -and -not $PublishOnly) {
    Write-Host "Skipping build (-SkipBuild); publishing existing installer if present." -ForegroundColor Yellow
}

if (-not (Test-Path $installer)) {
    Write-Error "Installer not found: $installer"
}

$mb = [math]::Round((Get-Item $installer).Length / 1MB)
$sigStatus = "Unknown"
$sigPublisher = ""
try {
    $sig = Get-AuthenticodeSignature -FilePath $installer
    $sigStatus = [string]$sig.Status
    if ($sig.SignerCertificate) {
        $sigPublisher = [string]$sig.SignerCertificate.Subject
    }
} catch {
    $sigStatus = "Unreadable"
}

$isSignedValid = $sigStatus -eq "Valid"
Write-Host ""
Write-Host "Installer ready ($mb MB):" -ForegroundColor Green
Write-Host "  $installer"
Write-Host ("  Authenticode: {0}{1}" -f $sigStatus, $(if ($sigPublisher) { " | $sigPublisher" } else { "" })) `
    -ForegroundColor $(if ($isSignedValid) { "Green" } else { "Yellow" })
if (Test-Path $latestYml) {
    Write-Host "  $latestYml"
    # Guard against uploading auto-update metadata that points at a different
    # version than the installer we built (stale latest.yml).
    $ymlMatch = Select-String -Path $latestYml -Pattern '^version:\s*(.+)$' | Select-Object -First 1
    if ($ymlMatch) {
        $ymlVersion = $ymlMatch.Matches.Groups[1].Value.Trim()
        if ($ymlVersion -ne $pkgVersion) {
            Write-Error "latest.yml version '$ymlVersion' != package.json '$pkgVersion' - auto-update metadata is stale. Rebuild the installer before publishing."
        }
    }
} else {
    Write-Host "WARNING: latest.yml missing - electron-updater auto-update metadata will not ship." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Stable download URL (after GitHub Release publish):" -ForegroundColor Cyan
Write-Host "  https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe"
Write-Host ""
Write-Host "Docs page:" -ForegroundColor Cyan
Write-Host "  https://streamclip-henna.vercel.app/"
Write-Host "Signing runbook: docs/DESKTOP_SIGNING.md"
Write-Host ""

if ($RequireSigned -and -not $isSignedValid) {
    Write-Error "RequireSigned set but Authenticode Status is '$sigStatus' (want Valid). See docs/DESKTOP_SIGNING.md Path B."
}

if ($DryRun) {
    Write-Host "=== Publish dry-run (no gh, no docs bump) ===" -ForegroundColor Cyan
    Write-Host ("Tag:            v{0}" -f $Version)
    Write-Host ("Path:           {0}" -f $(if ($isSignedValid) { "SIGNED" } else { "UNSIGNED (beta)" }))
    Write-Host ("RequireSigned:  {0}" -f $(if ($RequireSigned) { "yes" } else { "no" }))
    Write-Host ("NoDocsBump:     {0}" -f $(if ($NoDocsBump) { "yes" } else { "no (would bump docs/index.md + BETA_DOWNLOAD.md)" }))
    Write-Host "Dry-run complete." -ForegroundColor Green
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI (gh) to publish, or upload manually:" -ForegroundColor Yellow
    Write-Host "  gh release create v$Version `"$installer`" --title `"qClip v$Version`""
    exit 0
}

$tag = "v$Version"
$assets = @($installer)
if (Test-Path $latestYml) { $assets += $latestYml }

if ($isSignedValid) {
    $releaseNotes = @"
Windows 64-bit installer (Authenticode signed). SmartScreen reputation may still warm up on early downloads.

Docs: https://streamclip-henna.vercel.app/
Signing: docs/DESKTOP_SIGNING.md
"@
} else {
    $releaseNotes = @"
Windows 64-bit installer. SmartScreen may warn on unsigned beta builds - More info, Run anyway.

Docs: https://streamclip-henna.vercel.app/
"@
}

Write-Host "Publishing release $tag ..." -ForegroundColor Cyan

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
gh release view $tag 1>$null 2>$null
$releaseExists = $LASTEXITCODE -eq 0
$ErrorActionPreference = $prevEap

if ($releaseExists) {
    Write-Host "Release $tag exists - uploading assets with --clobber" -ForegroundColor Yellow
    gh release upload $tag @assets --clobber
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    gh release create $tag @assets `
        --title "qClip $tag" `
        --notes $releaseNotes `
        --latest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Release create failed. Retry upload: gh release upload $tag `"$installer`" --clobber" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

if (-not $NoDocsBump) {
    # UTF-8 safe bump via Python (PowerShell Set-Content corrupts emoji/emdash).
    # Bump henna home (published) + operator BETA_DOWNLOAD in lockstep with package.json.
    $env:STREAMCLIP_DOCS_BUMP_VERSION = $Version
    $env:STREAMCLIP_DOCS_BUMP_BETA = (Join-Path $root "docs\BETA_DOWNLOAD.md")
    $env:STREAMCLIP_DOCS_BUMP_INDEX = (Join-Path $root "docs\index.md")
    $py = @'
import os
import re
from pathlib import Path

version = os.environ["STREAMCLIP_DOCS_BUMP_VERSION"]
today = __import__("datetime").date.today().isoformat()


def bump_beta(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if f"`{version}`" in text and re.search(
        rf"> \*\*Current Windows build:\*\* `{re.escape(version)}`", text
    ):
        return "already current"
    text2, n = re.subn(
        r"(> \*\*Current Windows build:\*\* `)[^`]+(`)",
        rf"\g<1>{version}\2",
        text,
        count=1,
    )
    if not n:
        raise SystemExit("Windows build banner not found in BETA_DOWNLOAD.md")
    path.write_text(text2, encoding="utf-8", newline="")
    return "bumped"


def bump_index(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    tick = f"`{version}`"
    if f"Current Windows installer: **{tick}**" in text:
        return "already current"
    # Match version tick then optional parenthetical date — avoid eating
    # surrounding punctuation/encoding when the date blob is already messy.
    text2, n = re.subn(
        r"(Current Windows installer:\s*\*\*`)[^`]+(`\*\*)(?:\s*\([^)]*\))?",
        rf"\g<1>{version}\2 ({today})",
        text,
        count=1,
    )
    if not n:
        raise SystemExit("Current Windows installer banner not found in docs/index.md")
    # Keep the download-table version pin in sync when present.
    text2, _ = re.subn(
        r"(\]\([^)]*qClip-Setup-win-x64\.exe\)\s*\(`)[^`]+(`\))",
        rf"\g<1>{version}\2",
        text2,
        count=1,
    )
    path.write_text(text2, encoding="utf-8", newline="")
    return "bumped"


beta = Path(os.environ["STREAMCLIP_DOCS_BUMP_BETA"])
index = Path(os.environ["STREAMCLIP_DOCS_BUMP_INDEX"])
print(f"BETA_DOWNLOAD.md: {bump_beta(beta)}")
print(f"docs/index.md: {bump_index(index)}")
'@
    $result = $py | python -
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host $result -ForegroundColor Green
    Remove-Item Env:STREAMCLIP_DOCS_BUMP_VERSION -ErrorAction SilentlyContinue
    Remove-Item Env:STREAMCLIP_DOCS_BUMP_BETA -ErrorAction SilentlyContinue
    Remove-Item Env:STREAMCLIP_DOCS_BUMP_INDEX -ErrorAction SilentlyContinue
}

Write-Host "Running henna docs gate ..." -ForegroundColor Cyan
& "$PSScriptRoot\verify_henna_docs.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Published. Henna home + GitHub latest download are the customer truth." -ForegroundColor Green
