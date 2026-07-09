# StreamClip agent memory

Durable facts and preferences live here so long chats can summarize safely.
Update via `agents-memory-updater` or when the user corrects standing behavior.

## Learned User Preferences

- Prefer exact file paths and line numbers when citing code.
- Minimize context bloat: trim user rules, disable unused MCP/plugins, use subagents for exploration.
- Do not commit unless explicitly asked; use `gh` for GitHub PR/check work.
- After shipping user-facing web/auth changes to `master`, always build and publish a new Windows desktop installer (`scripts/publish_desktop_release.ps1`) and bump `docs/BETA_DOWNLOAD.md`.
- Coverage gate is authoritative via `scripts/verify_coverage.ps1` (Docker, `-m "not desktop"`).
- Phase 0 beta invites require both `verify_coverage.ps1` (≥95%) and `verify_stack.ps1` passing.

## Learned Workspace Facts

- **Canonical repo root is `D:\Projects\streamclip` only** (migrated off `C:\Users\locat\Projects\streamclip`). Never open, edit, or resolve paths against the old C: tree — it is a hollow stale skeleton (no `.git`). Cursor project id: `d-Projects-streamclip`. Balance report: `tmp/drive-migration-balance.txt`.
- StreamClip is GPU-bound; hot path is ingest → transcribe → highlights → virality → clip render (`docs/PERFORMANCE.md`).
- Canonical coverage scope: `backend` + `core`; desktop tests excluded with `@pytest.mark.desktop`.
- `docs/MASTER_TODO.md` §3.10 defines coverage truth; §3.5 gate is **GREEN at 95.01%** (2026-07-07). Phase 0 invites now block only on §3.8 (clean-VM `verify_stack.ps1`).
- Never wrap `verify_coverage.ps1`/`verify_stack.ps1` with `2>&1 | Tee-Object` in PowerShell — throws a spurious `NativeCommandError` on normal `docker compose build` stderr output.
- Rolling session truth for active work: `docs/SESSION_STATE.md` (read after summarization).
- Parallel chats: one branch per task; acquire `docs/.agent-lock.json` before protected paths (`docs/AGENT_COORDINATION.md`).
- Agent transcripts: `~/.cursor/projects/d-Projects-streamclip/agent-transcripts/<chat-id>/*.jsonl` (grep, do not read linearly). Legacy folder `c-Users-locat-Projects-streamclip` is historical only.
