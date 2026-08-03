# Desktop cohort exit — evidence pack (the beta)

**Purpose:** operator-fillable record for the **desktop closed beta** — the real beta, because the product is the installer (TDD Rev 5, ADR-001). Supersedes the Docker-centric [BETA_COHORT_EXIT.md](BETA_COHORT_EXIT.md) for launch validation; the Docker exit language now applies only to the future Pro/managed-cloud SKU.
**Status:** Tooling ready — **no results invented**. Every evidence cell starts blank or `☐`.
**Companions:** [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md) · [DESKTOP_UPGRADE_MATRIX.md](DESKTOP_UPGRADE_MATRIX.md) · [DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) · [BETA_ON_CALL.md](BETA_ON_CALL.md) · [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md)

**Do not** invent on-call names, tester outcomes, or crash-free numbers. Replace every `OPERATOR FILL` / `<…>` token before treating exit as closed.

> ✅ **F13 closed 2026-08-03** (MASTER §4.22): Help → Report a bug / beta feedback reach the operator via henna support-ingest email. GitHub beta-bug template remains a backup. See [DESKTOP_FAILURE_TAXONOMY.md](DESKTOP_FAILURE_TAXONOMY.md) F13.

---

## 0. Why this replaces the Docker cohort pack

The original Phase 0 cohort validated `docker compose up` + `verify_stack.ps1`. That is not what a creator installs. This pack validates the **actual `.exe`**: download → run → first clip, on a machine that never had qClip. If a gate here only tests Docker, it does not count toward desktop launch.

| Old (Docker Phase 0) | New (desktop beta) |
|----------------------|--------------------|
| `git clone` + `docker compose up` | Download signed installer, double-click |
| T0-1 = `verify_stack.ps1` exit 0 | T0-1 = installer → first clip on clean VM ([CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md)) |
| `/api/health/stack` deep probe | Tray "engine running" + in-app Get started |
| Docker CLEAN_VM sign-off | Clean-desktop-VM sign-off |

---

## 1. On-call roster — OPERATOR FILL

Solo operator? Same person in every row is valid. Source template: [BETA_ON_CALL.md](BETA_ON_CALL.md) §1.

| Role | Name | Contact | Filled at (ISO) |
|------|------|---------|-----------------|
| Beta lead | `OPERATOR FILL` | `OPERATOR FILL` | |
| Eng on-call (primary) | `OPERATOR FILL` | `OPERATOR FILL` | |
| Eng on-call (backup) | `OPERATOR FILL` | `OPERATOR FILL` | |
| Trust/signing (EV cert, SmartScreen) | `OPERATOR FILL` | `OPERATOR FILL` | |
| Docs (known-issues) | `OPERATOR FILL` | `OPERATOR FILL` | |

---

## 2. Desktop T0 flows (required for exit: T0-1..T0-4)

Pass criteria — desktop edition:

| Flow | Pass criteria |
|------|---------------|
| T0-1 | **Install → first clip** on a clean machine (no prior `%LOCALAPPDATA%\StreamClip`): installer runs, no white screen, models warm, short source → job `done` with ≥1 playable clip. Evidence: [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md) sign-off |
| T0-2 | Second, longer job reaches `done`; clip downloads to disk |
| T0-3 | Edit a clip (trim/title/caption) → re-render → approve |
| T0-4 | License activate (paste key → Pro) with no 500; restart app → data + license persist |
| T0-5 _(optional)_ | YouTube OAuth connect + publish (or clear error) |
| T0-6 _(optional)_ | Upgrade from previous beta preserves data ([DESKTOP_UPGRADE_MATRIX.md](DESKTOP_UPGRADE_MATRIX.md)) |

### 2.1 Per-tester matrix

Anonymized ids. Leave unused rows blank — do not invent testers.

| Tester id | OS + GPU? | Install→first clip (min) | T0-1 | T0-2 | T0-3 | T0-4 | T0-5 | T0-6 | Crashes (n) | Evidence (job id / log / notes) | Recorded by |
|-----------|-----------|--------------------------|------|------|------|------|------|------|-------------|----------------------------------|-------------|
| D-1 | | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | | `OPERATOR FILL` |
| D-2 | | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | | `OPERATOR FILL` |
| D-3 | | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | | `OPERATOR FILL` |
| D-4 | | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | | `OPERATOR FILL` |
| D-5 | | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | | `OPERATOR FILL` |

Result cells: replace `☐` with `pass` / `fail` / `blocked` / `pending`.

### 2.2 Rollup (desktop exit — MASTER §8.16d)

| Metric | Target | Actual | Met? |
|--------|--------|--------|------|
| Testers completing **T0-1..T0-4** | ≥4/5 | ____ / ____ | ☐ |
| **Install → first clip median** | < 45 min | ____ min | ☐ |
| **Crash-free sessions (7d)** | > 98% | ____ % | ☐ |
| Open 🔴 blockers older than 7 days | 0 | ____ | ☐ |

---

## 3. Launch windows (H+0 .. H+72)

| Window | Required action | Owner | Done | Evidence | Operator |
|--------|-----------------|-------|------|----------|----------|
| **H+0** | Send installer link; monitor in-app bug reports + GitHub template | Beta lead + Eng | ☐ | | `OPERATOR FILL` |
| **H+2** | ≥3 testers reached first clip (T0-1) | Eng | ☐ | Tester count: ____ | `OPERATOR FILL` |
| **H+24** | Triage P0/P1; publish known-issues addendum if needed | Eng + Docs | ☐ | | `OPERATOR FILL` |
| **H+72** | Go/no-go to expand cohort | Beta lead | ☐ | Decision: go/no-go/defer | `OPERATOR FILL` |

---

## 4. Signed build verification (trust gate)

The build the cohort installs **must be signed** (or the SmartScreen workaround must be explicitly accepted in the invite). See [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md).

| Step | Done | Evidence |
|------|------|----------|
| EV cert acquired + installed | ☐ | `OPERATOR FILL` |
| `publish_desktop_release.ps1 -RequireSigned` succeeded | ☐ | Release tag / `latest.yml`: |
| Installer shows publisher (not "Unknown") on a clean VM | ☐ | Screenshot path: |
| _(if unsigned)_ Invite explicitly states "More info → Run anyway" | ☐ | Invite copy link: |

---

## 5. Desktop exit gates (all must be evidenced)

| # | Gate | Source | Status | Evidence |
|---|------|--------|--------|----------|
| 1 | ≥4/5 testers complete T0-1..T0-4 | §2.2 | ☐ | §2.1 |
| 2 | Install → first clip median < 45 min | §2.2 | ☐ | §2.1 |
| 3 | Crash-free sessions > 98% over 7 days | §2.2 | ☐ | bug reports / logs |
| 4 | No open 🔴 blockers > 7 days | on-call | ☐ | issue URLs |
| 5 | Clean-desktop-VM sign-off current for the shipped build | [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md) | ☐ | doc sign-off + SHA |
| 6 | Signed build (or accepted unsigned workaround) | §4 | ☐ | §4 |
| 7 | On-call roster filled (no live TBD) | §1 | ☐ | §1 |
| 8 | H+72 go/no-go recorded | §3 | ☐ | §3 |

---

## 6. Sign-off

| Field | Value |
|-------|-------|
| Cohort wave / invite date | |
| Installer build / tag | |
| Repo commit SHA at exit review | |
| Desktop beta exit decision | ☐ closed · ☐ blocked · ☐ deferred |
| Beta lead | `OPERATOR FILL` |
| Date (ISO) | |

---

*Desktop-first re-center 2026-07-31. Fill cells; do not invent outcomes.*
