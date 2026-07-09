# Jet Stream docs

**Jet Stream** *(codebase: StreamClip)* turns long-form video into viral vertical shorts — self-hosted, private, no cloud subscription required. All processing runs on your machine.

---

!!! tip "Beta testers — start here"
    **No GitHub account needed.** Works on **Windows and Mac** via Docker.
    [**Get StreamClip →**](BETA_DOWNLOAD.md) — pick your OS, activate your license, make your first clip.

---

## Find your guide

| You are… | Go to |
|----------|-------|
| **A creator on Windows or Mac (beta invite)** | [Get StreamClip (install guide)](BETA_DOWNLOAD.md) |
| **Running through the full beta test plan** | [Quickstart](BETA_TESTER_QUICKSTART.md) → [Beta test plan](BETA_TESTER_PLAN.md) |
| **Helping build the macOS `.dmg`** | [macOS installer — builders](MACOS_INSTALLER.md) |
| **An operator running the Docker stack** | [Distribution runbook](distribution-runbook.md) · [Performance budgets](PERFORMANCE.md) |
| **An engineer exploring the system** | [Technical design](TECHNICAL_DESIGN.md) · [Creator platform map](CREATOR_PLATFORM.md) |
| **Checking launch readiness** | [Beta go-live checklist](BETA_GO_LIVE.md) |

---

## What StreamClip does

1. **Ingest** — paste any public video URL (Twitch, YouTube, Kick, `.mp4`)
2. **Transcribe** — Whisper runs locally to extract speech and timing
3. **Detect highlights** — YOLO + virality scoring picks the best moments
4. **Render clips** — FFmpeg + NVENC (NVIDIA) or libx264 (CPU / Mac) encodes vertical shorts
5. **Review and publish** — approve clips in the UI, publish to YouTube Shorts or TikTok

Everything stays on your machine unless you publish.

---

## Local docs preview

```bash
pip install -r docs/requirements.txt
python -m mkdocs serve -a 127.0.0.1:8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001).

## Build (strict)

```bash
mkdocs build --strict
```

Output lands in `site/` (gitignored).
