# Full Playwright e2e — v1.0.0-beta.24

**Runner:** `scripts/run_e2e_full.ps1` (+ optional SDK `scripts/sdk_run_e2e.py`)  
**Date (UTC):** 2026-08-04  
**API:** desktop sidecar `http://127.0.0.1:8765` (`E2E_API_BASE`)  
**Web:** Next.js `:3000` (started by runner)

## Result — GREEN

| Suite | Command | Result |
|-------|---------|--------|
| Mock UI journey | `npm run test:e2e:ui-journey` | **23 passed** (~1.5m) |
| Live happy-path | `E2E_RUN=1` `e2e/happy-path.spec.ts` | **12 passed** (~9.6s) |

Covers create → live job URL (U78), failure/onboarding paths, API create/list/distribution smoke against the live sidecar.

**Not covered (still deferred):** live browser file-upload → full GPU pipeline → playable clip in UI. That remains intentional deferral (GAP U27 / T83) — mock journey + API smoke are the ship-adjacent e2e bar.

## Re-run

```powershell
.\scripts\run_e2e_full.ps1 -ApiBase http://127.0.0.1:8765
# Docker compose API instead:
.\scripts\run_e2e_full.ps1 -ApiBase http://localhost:8000
# via Cursor SDK (needs CURSOR_API_KEY)
python scripts/sdk_run_e2e.py
```
