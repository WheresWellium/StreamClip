# Troubleshooting

Fix the problem, then go back to **[creating a clip](../BETA_TESTER_QUICKSTART.md)**.

Full beta limits: [Known issues](../BETA_KNOWN_ISSUES.md)

---

## Start in the app

1. **Settings → Get started** — aim for **Ready**.
2. **Help** in the header (same guides, in-window).
3. **Report a bug** / **Beta feedback** if you’re stuck.

**Windows `.exe`:** you usually do **not** need Docker.  
**Call to action if the app is missing:** [Install qClip](../BETA_DOWNLOAD.md#one-click-installers)

---

## Common fixes

| Symptom | Fix |
|---------|-----|
| SmartScreen / “Windows protected your PC” | **More info → Run anyway** |
| License key rejected (desktop) | Paste full `SCPRO-…` with dashes; on upgrade, re-paste once |
| License key rejected (Docker) | Run `import_invite_license.py` once — [Install → macOS](../BETA_DOWNLOAD.md#macos-docker-no-public-dmg-yet) |
| Stuck on first launch | Wait for ~1.5 GB model download; keep app open |
| “Link jobs” error | [Install beta.6](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe); on old beta.5 click **Skip** |
| Clips very slow | Expected on CPU — try a ~15 min source |
| Job stuck processing (Docker) | `docker compose logs worker --tail 100`; restart worker; shorter URL |
| localhost:3000 won’t load (Docker) | Wait 60s; `docker compose ps`; `docker compose up -d` |
| YouTube OAuth redirect error | Desktop URI must use `http://127.0.0.1:8765/.../youtube_shorts/callback` |
| Publish fails | Clip must be **Approved**; reconnect YouTube; check Distribution queue error |
| TikTok “inbox only” | Not a bug — finish in the TikTok app |

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

**Call to action:** in-app **Report a bug**, or reply to your invite email.

Then return to: [First clip](../BETA_TESTER_QUICKSTART.md) · [FAQ](../BETA_FAQ.md)
