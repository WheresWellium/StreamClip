# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-09 (cohort keys regen + henna doc plain-language pass)

## Active chats

| Branch | Task | Lock id | Notes |
|--------|------|---------|-------|
| `master` (local dirty) | Beta docs + cohort keys | — | |

## Current focus

**This turn:**
- Re-issued 5 admin keys (`beta-phase0-regen-001..005`) → `dist/phase0-invite-pack/`
- Plain-language pass: `index.md`, `BETA_DOWNLOAD.md`, `BETA_TESTER_QUICKSTART.md`, `TUTORIAL_FIRST_JOB.md`
- Fixed `prepare_invite_pack.ps1` null name lookup

## Cohort (private — keys in `tmp/beta-keys.csv`, do not commit)

| Name | Email |
|------|-------|
| Wellium | wellium@pogistudios.com |
| John Cantwell | johncantwell@odysseylogistics.com |
| Brandon | greesbr@gmail.com |
| Matt | matt@maius.com |
| AJ | anthony.j.orsted@gmail.com |

## Next

1. Send invite bodies from `dist/phase0-invite-pack/emails/*.txt`
2. `mkdocs build --strict` + deploy henna (Vercel)
3. H+0 monitor support reports after sends

## Key paths

- Keys log: `tmp/beta-keys.csv` (gitignored)
- Invite pack: `dist/phase0-invite-pack/`
- Public docs: https://streamclip-henna.vercel.app/
