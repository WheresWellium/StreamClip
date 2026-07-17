# Tutorial — Troubleshooting

**Quick reference** for the most common Phase 0 beta failures. Always run [Install](TUTORIAL_INSTALL.md) verify before deep debugging.

Full platform limits: [Known issues](../BETA_KNOWN_ISSUES.md)

---

## Top failures

| # | Symptom | Likely cause | Fix |
|---|---------|--------------|-----|
| 1 | `Docker Desktop is not running` from `start_local.ps1` | Docker not started | Launch Docker Desktop; wait for **Running**; re-run script |
| 2 | `verify_stack.ps1` exits non-zero | Services not healthy, migration failed, port conflict | `docker compose ps`; `docker compose logs api worker --tail 80`; fix red service; re-run verify |
| 3 | localhost:3000 won't load | Stack still starting; web container down | Wait 60 s; `docker compose up -d`; check `web` container logs |
| 4 | Job stuck in **processing** >30 min | Worker crash, GPU OOM, yt-dlp blocked | `docker compose logs worker --tail 100`; retry shorter URL; restart worker |
| 5 | Clips extremely slow | CPU-only path; GPU not passed to Docker | Windows: enable GPU in Docker Desktop + `--profile gpu`; Mac: expected — use shorter source |
| 6 | `nvidia-smi` fails in worker | GPU not shared with containers | Docker Desktop → Resources → GPU; update NVIDIA drivers; restart Docker |
| 7 | SSE progress frozen | Browser tab backgrounded; api restart | Refresh page; check api logs; UI falls back to polling after ~20 s |
| 8 | License key rejected | Wrong format; typo | Paste full key including dashes (`SCPRO-…`); check device ID in Settings → License |
| 9 | YouTube OAuth redirect error | Redirect URI mismatch | Google Console URI must match `WEB_ORIGIN` + `/api/distribution/oauth/youtube/callback` |
| 10 | Publish fails immediately | Token expired; quota; clip not approved | Reconnect YouTube; approve clip; check Distribution → Queue error message |
| 11 | Vault save fails | Quota exceeded | Delete old vault clips; activate beta key for higher limit |
| 12 | TikTok "inbox only" | Beta scope limitation | **Not a bug** — finish post in TikTok app. See [Known issues](../BETA_KNOWN_ISSUES.md) |
| 13 | Ollama / virality score 0 | LLM unreachable | Optional for clips; start `ollama` service or ignore for T0-2 |
| 14 | Mac: `docker compose` not found | Docker CLI not in PATH | Reinstall Docker Desktop; open new Terminal window |
| 15 | Port 3000 / 8000 in use | Another app bound to port | Stop conflicting app or change compose port mapping |

---

## Diagnostic commands

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

Open the **Help menu (?)** → **Report a bug** — submissions persist locally even without SMTP.

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
| [Beta quickstart FAQ](../BETA_TESTER_QUICKSTART.md#frequently-asked-questions) | Accounts, updates, privacy |
| [GPU setup](TUTORIAL_GPU_SETUP.md) | Slow jobs on Windows |
| [Install](TUTORIAL_INSTALL.md) | First-time setup |

---

*Phase 0 beta · Questions? Reply to your invite email or use in-app feedback.*
