# Tutorial — Troubleshooting

**When something goes wrong — start simple, then dig deeper.**

Full platform limits: [Known issues](../BETA_KNOWN_ISSUES.md)

---

## Start here (everyone)

1. **Settings → Get started** — **Ready** means you can create jobs; **Needs attention** means fix setup first  
2. **Help → Troubleshooting** inside the app (same topics, in-window)  
3. **Report a bug** or **Beta feedback** in the header — include **job ID** and log zip  

| Platform | Log folder |
|----------|------------|
| **Windows desktop** | `%LOCALAPPDATA%\qClip\logs\` |
| **macOS desktop** | `~/Library/Application Support/qClip/logs/` |

Install walkthrough: [Get started](../GET_STARTED.md)

---

## Desktop app — top fixes

| Symptom | What it usually means | What to do |
|---------|----------------------|------------|
| SmartScreen blocks installer | Unsigned beta | **More info → Run anyway** — [Get started](../GET_STARTED.md#windows) |
| Mac “can’t be opened” | Gatekeeper | **Right-click qClip → Open** — [Get started](../GET_STARTED.md#macos-apple-silicon) |
| **Needs attention** in Get started | Setup incomplete | Open **Help → Troubleshooting**; confirm license and disk space |
| License key rejected | Typo or wrong key | Paste full `SCPRO-…` with dashes; **Settings → License → Show details** for support |
| Job stuck **processing** 30+ min | Slow path or blocked download | Try a **shorter** URL; check `sidecar.log` in log folder |
| Clips very slow | CPU-only / long source | Shorter video for beta; Windows + NVIDIA is fastest |
| Progress bar frozen | Tab backgrounded or engine restart | Refresh UI; reopen job; attach logs if persistent |
| YouTube OAuth error | Redirect URI mismatch | Desktop uses `http://127.0.0.1:8765/.../callback` — match Google Console |
| TikTok “inbox only” | Beta scope | **Not a bug** — finish in TikTok app · [Known issues](../BETA_KNOWN_ISSUES.md) |
| Virality score shows `0` | Local LLM offline | Clips still render — optional for beta |

---

## Docker operators only

If you chose **Docker self-host** instead of the desktop installer, use these when the in-app check fails:

=== "Windows"

    ```powershell
    # Stack status
    docker compose ps

    # Health endpoints
    curl http://localhost:8000/api/health
    curl http://localhost:8000/api/health/stack

    # Recent logs
    docker compose logs api worker --tail 50

    # GPU check
    docker compose exec worker nvidia-smi

    # Full verify
    .\scripts\verify_stack.ps1
    ```

=== "macOS"

    ```bash
    docker compose ps
    curl -s http://localhost:8000/api/health
    curl -s http://localhost:8000/api/health/stack
    docker compose logs api worker --tail 50
    open http://localhost:3000
    ```

---

## When to stop and ask for help

Stop local debugging and post in your **beta channel** when:

- `verify_stack.ps1` fails after two restarts
- Data loss (jobs disappeared after normal `docker compose down` without `-v`)
- Repeated worker crashes with stack traces
- OAuth works locally but fails after following [Publish tutorial](TUTORIAL_PUBLISH_YOUTUBE.md) exactly

Include in your report:

1. **Job ID** (if applicable)
2. OS + GPU model (or "CPU only")
3. Output of `docker compose logs api worker --tail 50`
4. What you expected vs. what happened

Use **Report a bug** in the app header — you'll see **Saved — we'll review it** when your note is stored locally.

---

## Reset options

| Goal | Command | Warning |
|------|---------|---------|
| Restart services | `docker compose restart` | Safe |
| Rebuild images | `docker compose up -d --build` | Safe |
| Wipe all data | `docker compose down -v` | **Deletes jobs, vault, accounts** |

---

## Related docs

| Doc | Use when |
|-----|----------|
| [Known issues](../BETA_KNOWN_ISSUES.md) | Platform limits, TikTok inbox, desktop SmartScreen |
| [Get started](../GET_STARTED.md#quick-answers) | License, Docker, privacy, updates |
| [GPU setup](TUTORIAL_GPU_SETUP.md) | Slow jobs on Windows |

---

*Phase 0 beta · Questions? Reply to your invite email or use in-app feedback.*
