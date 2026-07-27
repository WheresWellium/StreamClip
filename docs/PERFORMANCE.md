# StreamClip — Performance Doctrine

Pipeline wall-clock throughput is the primary product constraint. For **desktop boot** phase budgets (splash → sidecar → first paint), see [`DESKTOP_STARTUP.md`](DESKTOP_STARTUP.md).

**Status:** Active (2026-06-29)

Pure performance is the **primary design constraint** for StreamClip. Features that slow the pipeline without a measurable quality gain are deferred. Every PR touching `core/` or workers should cite which hot path it affects and how it was validated.

## North-star metrics

| Metric | Target (GPU worker) | Target (CPU-only) | Instrument |
|--------|---------------------|-------------------|------------|
| End-to-end job (5 clips, 1h VOD) | < 15 min | < 60 min | Job `created_at` → `done` |
| `process_clip` p95 | < 90 s | < 10 min | `streamclip_clip_render_seconds` |
| Full-source transcribe | 1× pass only | medium model | Stage timer / logs |
| Discovery (highlights) | < 3 min / hour of video | skip optical flow on short tier | `streamclip_pipeline_stage_seconds{stage="highlights"}` |
| Virality scoring | < 30 s total (5 clips) | parallel LLM calls | `stage="virality"` |
| API create-job latency | < 200 ms p95 | — | `streamclip_request_duration_seconds` |

## Hot-path map (ordered by cost)

```
ingest (network) → transcribe (GPU) → highlights (CPU/CV) → virality (LLM) → process_clip × N (GPU)
```

| Stage | Dominant cost | Knobs |
|-------|---------------|-------|
| Ingest | Network, yt-dlp | URL disk cache; tier max heights; don't proxy through API |
| Transcribe | Whisper GPU/CPU | `whisper.model_size`, `device`, `compute_type`, `vad_filter` |
| Highlights | Optical flow (Farneback) | `ingest.short_skip_optical_flow`; `weight_optical_flow: 0` |
| Virality | Sequential LLM | Batch/parallel prompts; shorter model; timeout |
| process_clip | YOLO + NVENC + clip re-transcribe | `export.codec=h264_nvenc`; `refine_clip_transcript` tradeoff |

**Largest wins today:** GPU worker + NVENC, skip optical flow on short content, medium Whisper on CPU, parallel virality scoring.

## Architecture rules (non-negotiable)

1. **Long work is queued** — never in FastAPI request handlers.
2. **GPU queue isolation** — `gpu` concurrency=1; LLM and HTTP on `default`.
3. **Idempotent renders** — `process_clip` skips when `status=done` and storage key exists.
4. **Single full transcribe** — per-clip `transcribe_clip` only when `refine_clip_transcript: true`.
5. **Discovery cap** — score at most `target_clips × 6` candidates before NMS.

## Coding checklist (reinforcement loop)

Use on every pipeline or worker change:

1. **Profile first** — add or read stage histogram before optimizing.
2. **Prefer skip over speed-up** — cheaper to not run Farneback than to tune it.
3. **Prefer config over code** — expensive paths behind `config.yaml` flags.
4. **Prefer batch over loop** — DB commits, LLM calls, storage uploads.
5. **Prefer native over Python** — ffmpeg filters, numpy vectorization, faster-whisper CTranslate2.
6. **Document tradeoffs** — if accuracy costs time (e.g. clip re-transcribe), state it in PR and legends.

## Profiling commands

```powershell
# Per-stage Prometheus (worker must have enable_metrics: true)
curl http://localhost:8000/metrics | Select-String streamclip_pipeline_stage

# Celery task timing (Flower, dev profile)
docker compose --profile dev up flower

# ffmpeg encode benchmark (local)
ffmpeg -y -f lavfi -i testsrc2=duration=10:size=1080x1920:rate=60 -c:v h264_nvenc -cq 17 -f null -
```

## CPU-only quick profile

```yaml
whisper:
  model_size: medium
  device: cpu
  compute_type: int8
highlight:
  weight_optical_flow: 0.0
  weight_audio_energy: 0.35
  weight_spectral_novelty: 0.20
  weight_chat_spikes: 0.10
  weight_llm_virality: 0.35   # post-hoc only; must sum to 1.0
ingest:
  short_skip_optical_flow: true
  medium_skip_optical_flow: true
export:
  codec: libx264
  preset: veryfast
```

## Roadmap (performance)

| Item | Impact | Status |
|------|--------|--------|
| Stage histograms per pipeline task | Observability | Shipped |
| Parallel virality LLM calls | −20–40 s / job | Shipped (`score_clips_virality_parallel`) |
| Reuse yt-dlp subs for discovery text | Skip partial Whisper | Research |
| Clip render chord concurrency | N× GPU if multi-GPU | Open |
| Web bundle code-splitting | Faster first paint | Open |

## Related docs

- [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) — architecture & SLO table
- `docs/GAP_ANALYSIS.md` (internal repo register, not on the public docs site) — perf gaps tracked as T* items
- `.cursor/rules/performance-first.mdc` — agent coding rule
