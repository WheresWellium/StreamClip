# Troubleshooting (operator notes)

> **Creators:** use the public page — [Download & how to use](../index.md) (henna home). This file is **not published**.

Fix the problem, then go back to **[creating a clip](../BETA_TESTER_QUICKSTART.md)**.

Full beta limits: [Known issues](../BETA_KNOWN_ISSUES.md)

---

## Start in the app

1. **Settings → Get started** — aim for **Ready**.
2. **Help** in the header (same guides, in-window).
3. **Report a bug** / **Beta feedback** if you’re stuck.

**Windows `.exe` / Mac `.dmg`:** you usually do **not** need Docker.  
**Call to action if the app is missing:** [Install qClip](../BETA_DOWNLOAD.md)

---

## Common fixes

| Symptom | Fix |
|---------|-----|
| SmartScreen / “Windows protected your PC” | **More info → Run anyway** |
| Mac “app can’t be opened” / Gatekeeper | Right-click → **Open**, or Privacy & Security → **Open Anyway** |
| License key rejected (desktop) | Paste full `SCPRO-…` with dashes; on upgrade, re-paste once |
| License key rejected (Docker) | Run `import_invite_license.py` once — [Install → Docker fallback](../BETA_DOWNLOAD.md#macos-docker-fallback) |
| Stuck on first launch | Wait for ~1.5 GB model download; keep app open |
| “Link jobs” error | [Install beta.8](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe); on old beta.5 click **Skip** |
| Clips very slow / expected GPU? | Mac desktop and Docker are CPU-only today — try a ~15 min source. Windows `.exe` uses GPU when available; check **Settings → Get started** |
| Job stuck processing (Docker) | `docker compose logs worker --tail 100`; restart worker; shorter URL |
| localhost:3000 won’t load (Docker) | Wait 60s; `docker compose ps`; `docker compose up -d` |
| YouTube OAuth redirect error | Desktop URI must use `http://127.0.0.1:8765/.../youtube_shorts/callback` |
| Publish fails | Clip must be **Approved**; reconnect YouTube; check Distribution queue error |
| TikTok “inbox only” (publish) | Not a bug — finish in the TikTok app |
| TikTok URL job fails (IP block) | TikTok blocked the download from this network. **Upload the file**, use YouTube/Twitch/Kick/direct HTTPS, or retry from another network/VPN. |

---

## Docker diagnostics (Mac / operators)

```bash
docker compose ps
curl -s http://localhost:8000/api/health
docker compose logs api worker --tail 50
```

Windows Docker: `.\scripts\verify_stack.ps1` after the stack is up.

---

## Still stuck?

Include: OS, GPU or “CPU only”, `job_id`, what you expected vs what happened.

**Call to action:** [GitHub beta bug template](https://github.com/WheresWellium/StreamClip/issues/new?template=beta-bug.yml), or reply to your invite email.

Then return to: [First clip](../BETA_TESTER_QUICKSTART.md) · [FAQ](../BETA_FAQ.md)
