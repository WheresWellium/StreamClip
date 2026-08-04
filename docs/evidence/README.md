# Phase 0 exit evidence

Machine-captured snapshots for the Phase 0 cohort exit pack
([`../BETA_COHORT_EXIT.md`](../BETA_COHORT_EXIT.md), GAP O4 / MASTER §8.16).

## How it works

Run once per window; each run writes a timestamped, self-contained markdown file here:

```powershell
.\scripts\capture_phase0_evidence.ps1 -Label T0     # invite day
.\scripts\capture_phase0_evidence.ps1 -Label H2
.\scripts\capture_phase0_evidence.ps1 -Label H24
.\scripts\capture_phase0_evidence.ps1 -Label H48
.\scripts\capture_phase0_evidence.ps1 -Label H72    # go/no-go
```

Each file contains:

1. **Automated section** — git SHA, compose service status, health probes
   (ports + HTTP + `/api/health/stack` JSON), job/bug-report counts, open
   GitHub `beta` issues. Unreachable services produce `SKIP` lines, never crashes.
2. **OPERATOR FILL block** — the human facts the machine cannot know
   (tester T0 outcomes, triage counts, go/no-go). Fill these by hand.

Then paste the file's relative path into the matching **Evidence** cell of
`BETA_COHORT_EXIT.md` §2/§3.

## Desktop ship evidence (adjacent)

| File | What |
|------|------|
| [`matrix-pipeline-timing-beta24.md`](matrix-pipeline-timing-beta24.md) | 180-cell create-option full pipeline wall-clock (green) |
| [`e2e-full-beta24.md`](e2e-full-beta24.md) | Playwright ui-journey (23) + live happy-path (12) green |
| [`clean-desktop-vm-beta24.md`](clean-desktop-vm-beta24.md) | Pre-ship automated PASS + O4d OPERATOR FILL |
| [`clean-desktop-vm-beta20.md`](clean-desktop-vm-beta20.md) | Prior beta.20 clean-VM stub |

Prep installer pack: `.\scripts\prepare_clean_desktop_vm.ps1`  
Full e2e: `.\scripts\run_e2e_full.ps1` / SDK: `python scripts/sdk_run_e2e.py` (needs `CURSOR_API_KEY`)  
SDK re-check after matrix: `python scripts/sdk_run_desktop_preship.py` (needs `CURSOR_API_KEY`)

## Rules

- Never edit the automated section after capture — re-run instead.
- Never invent `OPERATOR FILL` values (GAP O4 rule: no fabricated evidence).
- No secrets: the script captures no tokens, keys, or emails. Keep it that way
  when filling operator blocks (use anonymized tester ids `T0-A`…).
- Files named `*-SAMPLE.md` are tooling demos, **not** real cohort evidence.
