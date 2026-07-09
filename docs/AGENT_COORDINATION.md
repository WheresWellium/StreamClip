# Agent coordination (parallel Cursor chats)

When multiple agents work on StreamClip at once, conflicts come from **shared mutable files**, not from code compilation. This convention keeps chats from overwriting each other’s context.

**Related:** `docs/SESSION_STATE.md` (compaction anchor) · `AGENTS.md` (durable prefs) · `.cursor/rules/conversation-compaction.mdc`

---

## Canonical workspace (C→D migration)

**Only valid repo root:** `D:\Projects\streamclip`  
**Cursor project folder:** `~/.cursor/projects/d-Projects-streamclip/`

Do **not** open or write to:

| Path | Why |
|------|-----|
| `C:\Users\locat\Projects\streamclip` (or `*-STALE-*`) | Hollow leftover skeleton — no `.git`, incomplete tree |
| `C:\Users\locat\Projects\streamclip-full` | Alternate clone; use only if user explicitly opens it |
| `~/.cursor/projects/c-Users-locat-Projects-streamclip/` | Legacy Cursor metadata; transcripts may exist but are not the live workspace |

Runtime config uses **relative** paths (`workspace/`, `output/`, `.cache/`) resolved from cwd — always run from `D:\Projects\streamclip`. Audit: `tmp/drive-migration-balance.txt`.

---

## Rules (short)

1. **One branch per task** — never two agents committing to `master` with overlapping uncommitted work.
2. **Acquire locks** before editing protected paths (see below).
3. **One deploy owner** — only one chat runs `npx vercel --prod`, `gh release create`, or pushes doc deploys to production.
4. **Update SESSION_STATE** before compaction; include your row in **Active chats**.
5. **Release locks** when done or when `expires_at` passes (stale locks may be cleared by the next agent).
6. **Never use the C: StreamClip skeleton** — if a chat’s workspace root is under `C:\Users\locat\Projects\streamclip`, stop and reopen `D:\Projects\streamclip`.

---

## Branch naming

| Pattern | Use for | Example |
|---------|---------|---------|
| `feat/<short-slug>` | New feature or scaffold | `feat/macos-installer` |
| `fix/<short-slug>` | Bug fix | `fix/oauth-publish-upsert` |
| `ops/<short-slug>` | Beta, release, docs deploy | `ops/beta-2-publish` |
| `chore/<short-slug>` | Coverage, refactors, tooling | `chore/coverage-ratchet` |

**Slug:** lowercase, hyphens, ≤4 words, matches lock `id` when possible.

**Base branch:** `master` unless the user specifies otherwise. Rebase or merge only after locks on touched paths are released.

---

## Lock file

**Runtime path:** `docs/.agent-lock.json` (gitignored — local only)  
**Schema reference:** `docs/.agent-lock.example.json`

### Acquire (agent checklist)

1. Read `docs/.agent-lock.json` if it exists.
2. If another lock covers your `paths` or `exclusive_paths` and `expires_at` is in the future → **stop**; note the blocking chat in SESSION_STATE or ask the user.
3. Write or merge your lock entry; set `expires_at` to **now + 24h** (renew if still working).
4. Add a row to **Active chats** in `docs/SESSION_STATE.md`.

### Release

Remove your lock entry (or delete the file if empty). Clear your **Active chats** row.

### Protected paths (default `exclusive_paths`)

| Path | Why |
|------|-----|
| `docs/SESSION_STATE.md` | Compaction anchor — one writer at a time |
| `docs/MASTER_TODO.md` | Plan sync checklist |
| `AGENTS.md` | Durable memory |
| `alembic/versions/*` | Migration ordering |
| `config.yaml`, `config/desktop.yaml` | Auth / prod flags |
| `docker-compose*.yml` | Infra topology |
| `vercel.json`, `.vercelignore` | Docs deploy |
| `apps/desktop/package.json` + `docs/BETA_DOWNLOAD.md` | Installer version bumps |

**Shared mutable dirs** (coordinate; do not run `docker compose down -v` while another chat has jobs in `workspace/` or `output/`):

- `workspace/`, `output/`, `.cache/`

### Deploy owner

Only the chat holding `deploy_owner` in the lock file may:

- `npx vercel --prod`
- `gh release create` / `scripts/publish_desktop_release.ps1`
- Push to `master` **for the purpose of triggering production docs deploy**

Other chats merge via PR or hand off to deploy owner.

---

## SESSION_STATE template

Keep the file **≤60 lines**. Copy this skeleton; delete sections that are empty.

```markdown
# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** YYYY-MM-DD (short topic)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| feat/example | Example task | example | `backend/api/foo.py` |

## Current focus

(one paragraph — what this chat owns)

## Blockers

- bullet list

## Next steps (ordered)

1. First action
2. Second action

## Key paths

- `path/to/file` — why it matters

## Decisions (this chat)

- YYYY-MM-DD: decision and rationale (only if not in AGENTS.md)
```

**Active chats** is the cross-chat index. After summarization, read this table first to see what other agents own.

---

## Conflict resolution

| Situation | Action |
|-----------|--------|
| Stale lock (`expires_at` past) | Remove entry; leave a one-line note in SESSION_STATE |
| Two agents need same path | User picks owner; other chat waits or takes a disjoint path |
| Merge conflict on `master` | Stop; user merges; do not force-push |
| Unsure who owns deploy | Assume **no deploy** until user confirms |

---

## Quick start (new chat)

```text
1. git checkout -b feat/<slug>
2. Copy docs/.agent-lock.example.json → docs/.agent-lock.json
3. Fill lock id, branch, paths; set expires_at
4. Update docs/SESSION_STATE.md → Active chats + Current focus
5. Work only on locked paths / branch scope
6. Before end: release lock, update MASTER_TODO if checklist applies
```
