# Preflight for Windows EV / Authenticode signing (§4.10).
# Canonical runbook: docs/DESKTOP_SIGNING.md
#
# Unsigned beta (default):  .\scripts\verify_desktop_signing_ready.ps1
# Signed release gate:      .\scripts\verify_desktop_signing_ready.ps1 -RequireSigning
# Decision matrix only:     .\scripts\verify_desktop_signing_ready.ps1 -DryRun
param(
    [switch]$RequireSigning,
    [switch]$DryRun,
    [string]$CertificatePath = $env:CSC_LINK,
    [string]$CertificatePassword = $env:CSC_KEY_PASSWORD,
    [string]$Thumbprint = $env:CSC_THUMBPRINT,
    [string]$SignTool = $env:SIGNTOOL
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-SigningConfigured {
    # PFX pair (OV/legacy) OR cert-store thumbprint (EV token / HSM, post-2023 norm)
    if ($Thumbprint) { return $true }
    return [bool]$CertificatePath -and [bool]$CertificatePassword
}

function Find-ThumbprintStore([string]$Sha1) {
    foreach ($store in @("Cert:\CurrentUser\My", "Cert:\LocalMachine\My")) {
        try {
            if (Get-ChildItem $store -ErrorAction SilentlyContinue |
                    Where-Object { $_.Thumbprint -eq $Sha1 }) { return $store }
        }
        catch { }
    }
    return $null
}

function Test-CertificateResolvable {
    if (-not $CertificatePath) { return $false }
    if (Test-Path -LiteralPath $CertificatePath) { return $true }
    # CI often stores base64 PFX in CSC_LINK
    if ($CertificatePath.Length -gt 256) { return $true }
    return $false
}

function Resolve-SignToolPath {
    param([string]$Hint)
    if ($Hint -and (Test-Path -LiteralPath $Hint)) { return $Hint }
    $kitsRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (-not (Test-Path $kitsRoot)) { return $null }
    return Get-ChildItem $kitsRoot -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\x64\\" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

$requireFromEnv = $env:STREAMCLIP_REQUIRE_SIGNED_INSTALLER -eq "1"
if ($requireFromEnv) { $RequireSigning = $true }

$warnings = @()
$errors = @()
$configured = Test-SigningConfigured
$resolvedSignTool = Resolve-SignToolPath -Hint $SignTool

Write-Host "=== Desktop signing preflight ===" -ForegroundColor Cyan
Write-Host ("Path:              {0}" -f $(if ($configured) { "SIGNED (CSC_* set)" } else { "UNSIGNED (beta default)" }))
Write-Host ("RequireSigning:    {0}" -f $(if ($RequireSigning) { "yes" } else { "no" }))
Write-Host ("DryRun:            {0}" -f $(if ($DryRun) { "yes" } else { "no" }))
Write-Host ("STREAMCLIP_REQUIRE_SIGNED_INSTALLER: {0}" -f $(if ($requireFromEnv) { "1" } else { "(unset)" }))

if (-not $configured) {
    if ($RequireSigning) {
        $errors += "Signing credentials required: set CSC_THUMBPRINT (EV token/HSM) or CSC_LINK + CSC_KEY_PASSWORD (PFX / CI secrets WINDOWS_CSC_LINK + WINDOWS_CSC_KEY_PASSWORD)"
    } else {
        $warnings += "CSC_THUMBPRINT / CSC_LINK unset - installer will be UNSIGNED (SmartScreen warning)"
    }
} elseif ($Thumbprint) {
    $normalized = $Thumbprint.Replace(" ", "").ToUpper()
    if ($normalized -notmatch "^[0-9A-F]{40}$") {
        $errors += "CSC_THUMBPRINT is not a 40-hex-char SHA1 thumbprint"
    } else {
        $foundStore = Find-ThumbprintStore -Sha1 $normalized
        if ($foundStore) {
            Write-Host "CSC_THUMBPRINT:    $normalized found in $foundStore (token/HSM mode)" -ForegroundColor DarkGray
        } elseif ($RequireSigning) {
            $errors += "CSC_THUMBPRINT $normalized not in cert store - plug in the EV token / install CA middleware, then retry"
        } else {
            $warnings += "CSC_THUMBPRINT $normalized not in cert store yet (token unplugged or middleware missing)"
        }
    }
    if (-not $resolvedSignTool) {
        $warnings += "signtool.exe not found - required for thumbprint signing (install Windows SDK Build Tools or set SIGNTOOL)"
    } else {
        Write-Host "signtool:          $resolvedSignTool" -ForegroundColor DarkGray
    }
    Write-Host "NOTE: thumbprint mode signs the installer post-build via sign_windows_artifact.ps1 (electron-builder builds unsigned; see DESKTOP_SIGNING.md Path C)" -ForegroundColor DarkGray
} else {
    if (-not (Test-CertificateResolvable)) {
        $errors += "CSC_LINK is not a readable file path and does not look like base64 PFX content"
    } else {
        if (Test-Path -LiteralPath $CertificatePath) {
            Write-Host "CSC_LINK:          file $($CertificatePath)" -ForegroundColor DarkGray
        } else {
            Write-Host "CSC_LINK:          base64 PFX content (length $($CertificatePath.Length))" -ForegroundColor DarkGray
        }
    }
    if (-not $resolvedSignTool) {
        $warnings += "signtool.exe not found locally - electron-builder may still sign via winCodeSign; set SIGNTOOL for manual sign_windows_artifact.ps1"
    } else {
        Write-Host "signtool:          $resolvedSignTool" -ForegroundColor DarkGray
    }
}

$pkgPath = Join-Path $root "apps\desktop\package.json"
if (Test-Path $pkgPath) {
    $signFlag = node --input-type=commonjs -e "const p=require(process.argv[1]); process.stdout.write(String(!!(p.build&&p.build.win&&p.build.win.signAndEditExecutable)));" -- $pkgPath
    Write-Host ("package.json signAndEditExecutable: {0} (enable_electron_signing.ps1 -Mode Auto toggles at build)" -f $signFlag) -ForegroundColor DarkGray
}

foreach ($w in $warnings) {
    Write-Host "WARN  $w" -ForegroundColor Yellow
}
foreach ($e in $errors) {
    Write-Host "FAIL  $e" -ForegroundColor Red
}

if ($DryRun) {
    Write-Host ""
    Write-Host "Dry-run next steps:" -ForegroundColor Cyan
    if ($configured -and $errors.Count -eq 0) {
        Write-Host "  SIGNED PATH -> set STREAMCLIP_REQUIRE_SIGNED_INSTALLER=1; build_desktop_installer.ps1; sign_windows_artifact.ps1 -VerifyOnly; publish_desktop_release.ps1 -RequireSigned"
    } else {
        Write-Host "  UNSIGNED PATH -> build_desktop_installer.ps1; publish_desktop_release.ps1 (beta SmartScreen caveat)"
        Write-Host "  When EV arrives -> docs/DESKTOP_SIGNING.md Path C (CSC_THUMBPRINT) or Path D (Azure)"
        Write-Host "  Legacy PFX -> docs/DESKTOP_SIGNING.md Path B (CSC_LINK + CSC_KEY_PASSWORD)"
    }
    if ($errors.Count -gt 0) {
        Write-Host "Dry-run complete with FAIL items above (exit 0 - dry-run does not fail-closed)." -ForegroundColor Yellow
        exit 0
    }
    Write-Host "Dry-run complete." -ForegroundColor Green
    exit 0
}

if ($errors.Count -gt 0) { exit 1 }

if ($configured) {
    Write-Host "Desktop signing preflight: CSC_* configured." -ForegroundColor Green
} else {
    Write-Host "Desktop signing preflight: unsigned build path OK." -ForegroundColor Green
}
exit 0
