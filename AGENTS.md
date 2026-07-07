# StreamClip agent memory

Durable facts and preferences live here so long chats can summarize safely.
Update via `agents-memory-updater` or when the user corrects standing behavior.

## Learned User Preferences

- Prefer exact file paths and line numbers when citing code.
- Minimize context bloat: trim user rules, disable unused MCP/plugins, use subagents for exploration.
- Do not commit unless explicitly asked; use `gh` for GitHub PR/check work.
- Coverage gate is authoritative via `scripts/verify_coverage.ps1` (Docker, `-m "not desktop"`).
- Phase 0 beta invites require both `verify_coverage.ps1` (≥95%) and `verify_stack.ps1` passing.

## Learned Workspace Facts

- StreamClip is GPU-bound; hot path is ingest → transcribe → highlights → virality → clip render (`docs/PERFORMANCE.md`).
- Canonical coverage scope: `backend` + `core`; desktop tests excluded with `@pytest.mark.desktop`.
- `docs/MASTER_TODO.md` §3.10 defines coverage truth; §3.5 gate is **GREEN at 95.01%** (2026-07-07). Phase 0 invites now block only on §3.8 (clean-VM `verify_stack.ps1`).
- Never wrap `verify_coverage.ps1`/`verify_stack.ps1` with `2>&1 | Tee-Object` in PowerShell — throws a spurious `NativeCommandError` on normal `docker compose build` stderr output.
- Rolling session truth for active work: `docs/SESSION_STATE.md` (read after summarization).
- Agent transcripts: `~/.cursor/projects/c-Users-locat-Projects-streamclip/agent-transcripts/<chat-id>/*.jsonl` (grep, do not read linearly).
