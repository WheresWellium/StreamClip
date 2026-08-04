# Create-option full pipeline timing — v1.0.0-beta.24

**Matrix:** 9 content profiles × 5 aspect ratios × clip counts {1,5,10,20} = **180 cells**  
**Harness:** `scripts/matrix_create_pipeline_timing.py` (+ optional SDK `scripts/sdk_run_matrix_pipeline_timing.py`)  
**API:** local sidecar create → poll done (upload fixture `tmp/fixtures/smoke_video.mp4`)  
**Commit (evidence capture):** 3764984  
**Run window (UTC):** 2026-08-03T23:27:09Z → 2026-08-04T00:14:15Z

## Result

| Metric | Value |
|--------|-------|
| done | 180 |
| failed | 0 |
| missing | 0 |
| green | **true** |
| wall_s min | 5.05 |
| wall_s mean | 15.78 |
| wall_s max | 60.35 |

Notes: short smoke fixture; later cells benefit from warm models/cache. **Green = create→done with `clip_count >= 1`**, not `clip_count >= target_clips`. Re-summarize (2026-08-04): `pipeline_green=true`, `clips_short_of_target=135/180` (75%) — expected on this fixture. Use `--require-target-clips` only with a longer source. Raw JSONL is gitignored under `tmp/matrix-pipeline-timing/`.

## By content profile

| profile | n | min | mean | max |
|---------|---|-----|------|-----|
| education | 20 | 5.06 | 15.11 | 20.15 |
| esports | 20 | 15.09 | 17.12 | 20.15 |
| gaming | 20 | 15.08 | 19.14 | 60.35 |
| general | 20 | 5.05 | 15.11 | 20.17 |
| irl | 20 | 5.05 | 15.11 | 20.15 |
| music | 20 | 5.07 | 15.11 | 20.15 |
| podcast | 20 | 5.05 | 15.11 | 20.15 |
| sports | 20 | 5.07 | 15.11 | 20.14 |
| vlog | 20 | 5.05 | 15.10 | 20.15 |

## By aspect ratio

| aspect | n | min | mean | max |
|--------|---|-----|------|-----|
| 16:9 | 36 | 5.05 | 8.42 | 20.16 |
| 1:1 | 36 | 15.08 | 15.11 | 15.14 |
| 2:3 | 36 | 15.09 | 19.01 | 20.17 |
| 4:5 | 36 | 15.07 | 15.11 | 15.17 |
| 9:16 | 36 | 20.09 | 21.25 | 60.35 |

## By target_clips

| target_clips | n | min | mean | max |
|--------------|---|-----|------|-----|
| 1 | 45 | 5.05 | 16.45 | 60.35 |
| 5 | 45 | 5.05 | 15.56 | 20.20 |
| 10 | 45 | 5.05 | 15.56 | 20.15 |
| 20 | 45 | 5.06 | 15.56 | 20.32 |

## Re-run

```powershell
# direct
python scripts/matrix_create_pipeline_timing.py --api-base http://127.0.0.1:8765
# via Cursor SDK (needs CURSOR_API_KEY)
python scripts/sdk_run_matrix_pipeline_timing.py
```
