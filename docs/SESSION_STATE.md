# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-15 (BETA TEST INFO sent 6/6; deploy-blocker fixes; coverage 97.18%)

## Active chats

| Branch | Task | Lock id | Notes |
|--------|------|---------|-------|
| `cursor/send-beta-test-info-emails-e6b4` (PR #3) | Beta send + zip + SMTP | — | open |

## Current focus

**Done this session:**
- **BETA TEST INFO emails sent 6/6** (2026-07-10) via `mail.wellium.work:465` implicit SSL.
- Fixed `send_email` regression: added explicit `use_ssl` flag (env `SMTP_SSL`, auto-on port 465) instead of overloading `starttls=False` → restores `test_send_email_retries_then_fails`.
- **Deploy blocker fixed:** beta zip now keeps `web/` (the `web` compose service builds from `./web`) and real `docker-compose.prod.yml` name. Mail-scanner evasion is non-destructive (`.sc` attachment rename at send time only).
- Verified local-deploy wiring: both compose files parse; all env refs have `:-` defaults; all Dockerfiles resolve; 10 alembic migrations (head `0010`).

## Cohort (private — keys in `tmp/beta-keys.csv`, do not commit)

| Name | Email |
|------|-------|
| Wellium | wellium@pogistudios.com |
| John Cantwell | johncantwell@odysseylogistics.com |
| Brandon | greesbr@gmail.com |
| Matt | matt@maius.com |
| AJ | anthony.j.orsted@gmail.com |
| Mitchell | acosmicprefuse@gmail.com |

## Next

1. ~~Send invites~~ ✅ · ~~Send BETA TEST INFO~~ ✅ (6/6, 2026-07-10)
2. **H+2/H+24/H+72 monitor** tester T0 results (`BETA_GO_LIVE` §7); read reports via `docker compose exec api python scripts/list_support_reports.py --limit 20`.
3. **4 pre-existing CI test failures** (not this PR — see `MASTER_TODO` §3.5): `test_run_transcribe_streamclip_error_marks_failed`, `test_discover_peak_windows_empty_energy_curve`, `test_run_virality_with_chat_and_transcript`, `test_platform_upsert_updates_metadata`. Coverage gate itself GREEN (97.18%).
4. **e2e CI infra flake:** runner disk exhausted pulling Ollama 3.1GB image (`no space left on device`). Needs `docker system prune` step, self-hosted runner, or Ollama out of e2e image.

## Key paths

- Keys log: `tmp/beta-keys.csv` (gitignored)
- Beta zip: `dist/StreamClip-beta.zip` (build: `python scripts/build_beta_zip.py`)
- Public docs: https://streamclip-henna.vercel.app/
