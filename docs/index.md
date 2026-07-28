# qClip docs

**Turn long videos into short clips — on your computer, not in the cloud.**

---

!!! success "New beta tester? Start here"
    **You do not need Docker. You do not need GitHub.**

    1. **[Desktop install guide](DESKTOP_SOLO_USER_GUIDE.md)** — complete Windows & Mac walkthrough (recommended)
    2. **[Get your installer](BETA_DOWNLOAD.md)** — where the `.exe` / `.dmg` comes from
    3. Paste your **license key** in **Settings → License** (`SCPRO-…` from invite email)

    **Stuck?** **Help** inside the app, or **[Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md)** on this site.

---

## Pick your path

| I want to… | Open this |
|------------|-----------|
| **Install qClip and run my first clip** | [Desktop install guide](DESKTOP_SOLO_USER_GUIDE.md) |
| **Understand download options & SmartScreen / Gatekeeper** | [Get qClip](BETA_DOWNLOAD.md) |
| **Fast 15-minute overview** | [Beta quickstart](BETA_TESTER_QUICKSTART.md) |
| **Learn the job screen & progress stages** | [Your first clip](tutorials/TUTORIAL_FIRST_JOB.md) |
| **Fix something broken** | [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md) · [Known issues](BETA_KNOWN_ISSUES.md) |
| **Publish to YouTube Shorts** | [Publish tutorial](tutorials/TUTORIAL_PUBLISH_YOUTUBE.md) |
| **Build the Mac installer** (helpers only) | [macOS DMG builders](MACOS_INSTALLER.md) |

---

## What qClip does

1. **You paste a link** — Twitch, YouTube, Kick, or a public `.mp4`
2. **It listens** — speech becomes text on your machine
3. **It finds moments** — software scores highlight sections
4. **It renders clips** — vertical videos ready for Shorts / TikTok
5. **You review** — approve, then publish if you want

Raw video stays local unless you explicitly publish to a platform.

---

## Simple glossary

| Word | What it means |
|------|----------------|
| **Installer** | `qClip-Setup-win-x64.exe` (Windows) or `qClip-mac-arm64.dmg` (Mac) |
| **License key** | Code from invite email (`SCPRO-…`) — unlocks all beta features |
| **Job** | One video you asked qClip to process |
| **Clip** | One short video cut from that job |
| **Vault** | Your saved favorite clips |
| **Get started** | In-app health check — **Ready** = good to create jobs |
| **GPU** | Graphics card — makes Windows processing much faster |
| **Docker** | *Optional* operator tool — **not** required for the desktop app |

---

## Preview these docs locally

```bash
pip install -r docs/requirements.txt
python -m mkdocs serve -a 127.0.0.1:8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001).
