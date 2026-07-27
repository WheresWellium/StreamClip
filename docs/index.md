# qClip docs

**StreamClip** turns long videos into short vertical clips on **your own computer**. Nothing is uploaded to our servers unless you choose to publish to YouTube or TikTok.

---

!!! tip "Beta testers — start here"
    **You do not need a GitHub account.**

    1. **[Get StreamClip](BETA_DOWNLOAD.md)** — pick Windows or Mac and follow the steps
    2. **[Quickstart](BETA_TESTER_QUICKSTART.md)** — from install to your first clip (~15 minutes)
    3. Paste your **license key** in **Settings → License** (from your invite email)

    **Stuck?** Open **Help** in the app (guides stay in-window) or use **Report a bug** in the header. Reply to your invite email if you need a human.

---

## Pick your guide

| If you want to… | Open this |
|-----------------|-----------|
| **Install and run the beta** | [Get StreamClip](BETA_DOWNLOAD.md) |
| **Step-by-step: first clip** | [Beta quickstart](BETA_TESTER_QUICKSTART.md) |
| **Follow the full test checklist** | [Beta test plan](BETA_TESTER_PLAN.md) |
| **Fix a problem** | [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md) · [Known issues](BETA_KNOWN_ISSUES.md) |
| **Build the macOS installer** (helpers only) | [macOS installer — builders](MACOS_INSTALLER.md) |

!!! note "Operator / engineering docs"
    Architecture, performance, and runbooks stay in the repo for contributors but are **not** linked in the public docs nav or the shipped app. Partners who need HTTP API reference should ask your operator privately.

---

## What StreamClip does (simple version)

1. **You paste a link** — Twitch, YouTube, Kick, or a public `.mp4`
2. **It listens and reads** — speech is turned into text on your machine
3. **It finds the best moments** — software picks highlight sections
4. **It makes short clips** — vertical videos ready for Shorts / TikTok
5. **You review and publish** — approve clips, then post if you want

Your raw video files stay on your computer.

---

## Words you might see

| Word | Plain meaning |
|------|----------------|
| **Docker** | A free app that runs StreamClip in the background (like a mini server on your PC) |
| **License key** | A code from your invite email (`SCPRO-…`) that unlocks all features |
| **Job** | One video you asked StreamClip to process |
| **Clip** | One short video cut from that job |
| **Vault** | Your saved favorite clips |
| **GPU** | Your graphics card — makes processing much faster when acceleration is on |
| **Help center** | In-app guides at **Help** — same topics as this site, embedded in StreamClip |

---

## Preview these docs on your computer

```bash
pip install -r docs/requirements.txt
python -m mkdocs serve -a 127.0.0.1:8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001).
