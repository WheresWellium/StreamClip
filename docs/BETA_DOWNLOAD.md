# Download StreamClip (Windows)

**Turn long-form video into viral vertical shorts** — install once, no Docker, no terminal.

!!! success "Current release"
    **v1.0.0-beta.1** · Windows 64-bit · ~325 MB · [Release notes](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.1)

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Windows installer**

    ---

    One-click setup. Opens from your desktop or Start menu.

    [:octicons-download-24: Download for Windows (64-bit)](https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe){ .md-button .md-button--primary }

-   :material-shield-alert:{ .lg .middle } **First install**

    ---

    Windows SmartScreen may warn on unsigned beta builds. Click **More info → Run anyway**. See [known issues](BETA_KNOWN_ISSUES.md#desktop-exe-phase-2).

</div>

Alternative link (pinned to this release): [StreamClip-Setup-win-x64.exe (v1.0.0-beta.1)](https://github.com/WheresWellium/StreamClip/releases/download/v1.0.0-beta.1/StreamClip-Setup-win-x64.exe)

---

## System requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10/11 (64-bit) | Windows 11 |
| RAM | 16 GB | 32 GB |
| Disk | 10 GB free (app + models) | 20 GB SSD |
| GPU | CPU-only works (slow) | NVIDIA with NVENC |
| Network | First-run model download | Broadband |

No Docker. No Git. No Python install required.

---

## Install in 3 steps

1. **Download** the installer above (`StreamClip-Setup-win-x64.exe`).
2. **Run** the installer — accept defaults or choose a folder. Shortcuts are created on the desktop and Start menu.
3. **Launch StreamClip** — first start may take a few minutes while AI models download (progress shown in-app).

The app runs locally at `http://127.0.0.1:8765/` inside a desktop window. Your videos never leave your machine unless you publish.

---

## After install — first clip

1. Open **StreamClip** from the desktop shortcut.
2. Click **New job**.
3. Paste a **public video URL** or upload a file.
4. Wait for processing — GPU is much faster than CPU-only.
5. Approve a clip → optional **YouTube Shorts** publish from Settings → Distribution.

Full acceptance flows: [Beta test plan](BETA_TESTER_PLAN.md) §4.3 (T0 flows).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| SmartScreen blocks install | More info → Run anyway ([details](BETA_KNOWN_ISSUES.md)) |
| App won't start | Reboot; ensure 10 GB+ disk free; check `%LOCALAPPDATA%\StreamClip\logs` |
| Very slow clips | Enable NVIDIA GPU in Windows; close other GPU apps |
| Download link 404 | Use the [pinned v1.0.0-beta.1 link](#download-streamclip-windows) above or [GitHub Releases](https://github.com/WheresWellium/StreamClip/releases) |

Report bugs with: Windows version, GPU model, job id, and steps to reproduce. Channel is in your invite email.

---

## For operators (self-host Docker)

Technical self-host via Docker is documented separately — not required for this installer path:

- [Beta quickstart (Docker)](BETA_TESTER_QUICKSTART.md)
- [Distribution runbook](distribution-runbook.md)

---

*Jet Stream / StreamClip · Phase 0 creator beta · [Known issues](BETA_KNOWN_ISSUES.md)*
