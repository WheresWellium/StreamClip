# StreamClip — Beta Known Issues

**Audience:** Phase 0–2 beta testers · **Owner:** core team  
**Update:** when shipping a beta wave or closing a blocker

---

## Platform limits (by design for beta)

| Area | Behavior |
|------|----------|
| TikTok | **Inbox upload only** until app audit grants `video.publish` scope; finish posting in TikTok app |
| Instagram | **Not supported** — no Reels adapter in beta |
| Cloud multi-tenant | **Not supported** — `backend/cloud/tenant.py` is unwired |
| Commerce | Lemon Squeezy one-time keys; automated key email may be missing on some `order_created` paths (see MASTER_TODO §2.3) |

## Performance expectations (informal SLIs)

From `docs/PERFORMANCE.md` with **+25% beta tolerance**:

| Scenario | GPU target | CPU target |
|----------|------------|------------|
| 1 h VOD → 5 clips | < 25 min | < ~110 min |
| API create-job (localhost) | < 500 ms | < 500 ms |

CPU-only or no NVENC paths are **slow but supported** — use `libx264` export codec.

## Docker self-host (Phase 0–1)

- Requires **Docker Desktop** on Windows; WSL2 backend recommended
- Default worker listens on **both** `default` and `gpu` queues — not full GPU isolation (see MASTER_TODO §6.8)
- Ollama optional; virality degrades to score 0 if LLM unreachable

## Desktop `.exe` (Phase 2)

- **Unsigned builds** trigger Windows SmartScreen — click “More info → Run anyway” until code signing (MASTER_TODO §4.10)
- First run may download **multi-GB models** (Whisper, YOLO) — allow time and disk space
- Auto-update is a **stub** — manual reinstall until §4.10
- **Scheduled publishes fire only while the app is running** — in-process mode has no external Beat service; an internal scheduler polls due posts every 60 s and catches up overdue ones on next launch (`queue.inprocess_beat`)

## Reporting bugs

Include: OS version, GPU model, `job_id`, relevant log snippet, steps to reproduce.  
Post in the beta feedback channel named in your invite (Discord / GitHub Discussions).

See `docs/BETA_TESTER_PLAN.md` for acceptance flows T0 / T1 / T2.
