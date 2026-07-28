# Phase 0 cohort exit — evidence pack

**Purpose:** Operator-fillable record for GAP **O4** / **O5** and MASTER **§8.16** (H+2 / H+24 / H+72 / T0).  
**Status:** Tooling ready (`scripts/capture_phase0_evidence.ps1`) — **no results invented**. Every evidence cell starts blank or `☐`.  
**Companions:** [`BETA_GO_LIVE.md`](BETA_GO_LIVE.md) §7–§8 · [`BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) §4.3 / §4.5 · [`BETA_ON_CALL.md`](BETA_ON_CALL.md) · [`BETA_OPS_PHASE0.md`](BETA_OPS_PHASE0.md) §6 · [`docs/evidence/README.md`](evidence/README.md)  
**Do not** invent on-call names or mark incomplete ops items done. Replace every `OPERATOR FILL` / `<…>` token before treating exit as closed.

---

## 0. How to complete this pack

1. Fill **§1 On-call** from the live rotation (tokens in [`BETA_ON_CALL.md`](BETA_ON_CALL.md) §1 —
   search for `<` to find remaining placeholders). Solo operator? Same person in every row is valid.
2. **Capture machine evidence** at each window (fail-soft; never invent outcomes):

   ```powershell
   .\scripts\capture_phase0_evidence.ps1 -Label T0     # invite day / baseline
   .\scripts\capture_phase0_evidence.ps1 -Label H2
   .\scripts\capture_phase0_evidence.ps1 -Label H24
   .\scripts\capture_phase0_evidence.ps1 -Label H48
   .\scripts\capture_phase0_evidence.ps1 -Label H72    # go/no-go
   ```

   Each run writes `docs/evidence/phase0-<label>-<timestamp>.md`. Paste that path into the
   matching **Evidence** cell below, then fill the **OPERATOR FILL** block inside the file.
3. After invites (H+0), complete **§2** windows in order: H+2 → H+24 → H+72.
4. Collect tester outcomes into **§3** (T0-1…T0-4 required; T0-5/T0-6 optional).
5. Run / record **§4** Lemon Squeezy staging verification (one real staging checkout → activate → Pro).
6. Tick **§5** exit gates only when evidence exists in this file (or linked evidence path).
7. Sign **§6**. Update `BETA_GO_LIVE.md` §7 status cells and MASTER §8.16 only after this pack is filled — do not backfill fake ticks.

**Pass shorthand:** `pass` / `fail` / `blocked` / `n/a` / `pending`.  
**Evidence:** paste `docs/evidence/…` path, job id, issue URL, commit SHA, or `verify_stack` log path — not “looks fine”.

See also [`docs/evidence/README.md`](evidence/README.md).

---

## 1. On-call roster (GAP O5) — OPERATOR FILL

| Role | Name | Contact | Filled at (ISO) |
|------|------|---------|-----------------|
| Beta lead | `OPERATOR FILL` | `OPERATOR FILL` | |
| Eng on-call (primary) | `OPERATOR FILL` | `OPERATOR FILL` | |
| Eng on-call (backup) | `OPERATOR FILL` | `OPERATOR FILL` | |
| Ops (keys / GHCR / OAuth) | `OPERATOR FILL` | `OPERATOR FILL` | |
| Docs (known-issues) | `OPERATOR FILL` | `OPERATOR FILL` | |

Source template: [`BETA_ON_CALL.md`](BETA_ON_CALL.md) §1. Keep secrets out of git if preferred; then note “private roster” in Evidence and leave Name as `OPERATOR FILL (private)`.

---

## 2. Launch-window checklist (BETA_GO_LIVE §7)

| Window | Required action | Owner (role) | Done | Evidence (link / note / path) | Operator |
|--------|-----------------|--------------|------|-------------------------------|----------|
| **H+0** | Invites sent; monitor in-app bugs + GitHub beta-bug template | Beta lead + Eng | ☐ _(go-live may already show invites sent — confirm here)_ | | `OPERATOR FILL` |
| **H+2** | ≥3 testers passed **T0-1** (`verify_stack.ps1` exit 0 + `/api/health/stack` OK) | Eng | ☐ | Tester ids / count: ____ | `OPERATOR FILL` |
| **H+8** _(on-call)_ | Triage open P0/P1; post status if any P0 open >4h | Eng primary | ☐ | | `OPERATOR FILL` |
| **H+24** | Full P0/P1 triage; publish known-issues addendum if needed | Eng + Docs | ☐ | Issues triaged: ____ · Known-issues PR/commit: ____ | `OPERATOR FILL` |
| **H+48** _(on-call)_ | Backup check-in; clear or document remaining P1s | Eng backup | ☐ | | `OPERATOR FILL` |
| **H+72** | Go/no-go to expand cohort (`BETA_TESTER_PLAN` §4.5 / MASTER §8.16) | Beta lead | ☐ | Decision: `go` / `no-go` / `defer` — ____ | `OPERATOR FILL` |

### H+2 detail

| Field | Value |
|-------|-------|
| Window closed at (ISO) | |
| Testers with T0-1 pass (need ≥3) | `OPERATOR FILL` count: ____ |
| Failures / blockers | |
| Evidence | |

### H+24 detail

| Field | Value |
|-------|-------|
| Window closed at (ISO) | |
| Open 🔴 P0 count | |
| Open 🟡 P1 count | |
| Known-issues addendum published? | ☐ yes · ☐ no · ☐ n/a |
| Evidence (issue list / commit) | |

### H+72 detail

| Field | Value |
|-------|-------|
| Window closed at (ISO) | |
| Go/no-go | ☐ go · ☐ no-go · ☐ defer |
| Rationale (1–3 sentences) | |
| Unresolved 🔴 >7d? | ☐ none · ☐ yes (list below) |
| Signed by (Beta lead) | `OPERATOR FILL` |

---

## 3. Tester T0 results (required for exit: T0-1…T0-4)

Pass criteria from [`BETA_TESTER_PLAN.md`](BETA_TESTER_PLAN.md) §4.3:

| Flow | Pass criteria |
|------|---------------|
| T0-1 | `verify_stack.ps1` exit 0; `/api/health/stack` OK |
| T0-2 | Job reaches `done`; ≥1 clip with preview |
| T0-3 | Patch boundaries/title; approve clip |
| T0-4 | YouTube OAuth saved; publish `published` or clear error |
| T0-5 _(optional)_ | Vault save; quota respected |
| T0-6 _(optional)_ | `SCPRO-…` → Pro on distribution gates |

### 3.1 Per-tester matrix

Use anonymized ids (`T0-A`…) or email handles. Leave unused rows blank — do not invent testers.

| Tester id | Platform (Win/mac + GPU?) | T0-1 | T0-2 | T0-3 | T0-4 | T0-5 | T0-6 | Evidence (job id / issue / notes) | Recorded by |
|-----------|---------------------------|------|------|------|------|------|------|-----------------------------------|-------------|
| T0-1 | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | `OPERATOR FILL` |
| T0-2 | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | `OPERATOR FILL` |
| T0-3 | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | `OPERATOR FILL` |
| T0-4 | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | `OPERATOR FILL` |
| T0-5 _(optional)_ | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | | `OPERATOR FILL` |

Result cells: replace `☐` with `pass` / `fail` / `blocked` / `pending` when known.

### 3.2 Rollup (MASTER §8.16 / plan §4.5)

| Metric | Target | Actual | Met? |
|--------|--------|--------|------|
| Testers completing **T0-1…T0-4** | ≥4/5 | ____ / ____ | ☐ |
| Testers with **T0-1** pass (H+2 gate) | ≥3 | ____ | ☐ |
| Open 🔴 blockers older than 7 days | 0 | ____ | ☐ |

---

## 4. Lemon Squeezy staging verification (exit gate)

One staging/test purchase → key delivered → activate → Pro tier. Checklist detail: [`BETA_OPS_PHASE0.md`](BETA_OPS_PHASE0.md) §6. Do **not** tick until run.

| Step | Done | Evidence |
|------|------|----------|
| `.\scripts\verify_ls_beta_config.ps1` OK | ☐ | Output path / date: |
| Staging/test checkout completed (non-prod buyer email) | ☐ | LS order id: |
| Webhook HTTP 2xx (`license_key_created` or `order_created` fallback) | ☐ | Delivery id / log: |
| Key present in `install_licenses` (or equivalent) | ☐ | order_id / email (redact if needed): |
| Activate in app → Pro / distribution gates unlocked | ☐ | machine id hash / screenshot path: |
| Operator sign-off | ☐ | Name: `OPERATOR FILL` · Date: |

---

## 5. Phase 0 exit gates (all must be evidenced)

| # | Gate | Source | Status | Evidence |
|---|------|--------|--------|----------|
| 1 | ≥4/5 testers complete T0-1…T0-4 | Plan §4.5 / MASTER §8.16 | ☐ outstanding | §3.2 |
| 2 | No open 🔴 blockers > 7 days | Plan §4.5 / on-call | ☐ | Issue URLs: |
| 3 | Line coverage ≥95% (`verify_coverage.ps1`) | Go-live §8 / invite gate | ☐ _(reconfirm if stale)_ | Date + %: |
| 4 | Clean-VM / stack sign-off current for wave | Go-live §8 | ☐ | Link `CLEAN_VM_VERIFY.md` / SHA: |
| 5 | Staging LS purchase → activate → Pro | Go-live §8 / plan §4.5 | ☐ | §4 |
| 6 | On-call roster filled (no live TBD for primary/backup) | GAP O5 / on-call §1 | ☐ | §1 |
| 7 | H+72 go/no-go recorded | Go-live §7 | ☐ | §2 H+72 |

**Phase 1 reminder (not Phase 0 exit):** 110% coverage row (MASTER §3.10 / §8.1) remains a Phase 1 blocker even after this pack closes Phase 0.

---

## 6. Sign-off

| Field | Value |
|-------|-------|
| Cohort wave / invite date | |
| Repo commit SHA at exit review | |
| Phase 0 exit decision | ☐ closed · ☐ blocked · ☐ deferred |
| Beta lead | `OPERATOR FILL` |
| Eng on-call | `OPERATOR FILL` |
| Date (ISO) | |

---

*Scaffold + evidence tooling 2026-07-28 — GAP O4/O5. Fill cells; do not invent outcomes.*
