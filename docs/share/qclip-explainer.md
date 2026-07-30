# qClip — How it works

**Paste a link → wait → get ranked, captioned clips ready to post.**  
No subscription. No watermark. You keep the files.

qClip turns long streams and VODs into short, phone-ready clips. It finds the good moments, crops them for TikTok / Shorts / Reels, adds captions, and ranks what to post first — on your own computer.

---

## Mind map

```
                         qClip
            ┌─────────────┼─────────────┐
            │             │             │
     What you get   How you use it   Under the hood
            │             │             │
            └────── AI helpers ─────────┘
```

**What you get**
- Short clips from long videos
- Vertical / square crops
- Animated captions
- Meme overlays + sound effects
- A ranked “post these first” list

**How you use it**
1. Paste a Twitch / YouTube URL (or upload a file)
2. Watch live progress
3. Review clips in the library
4. Approve / publish

**Under the hood**
- Website: Next.js
- API: FastAPI (Python)
- Job queue: Celery + Redis
- Database: PostgreSQL
- File storage: MinIO
- Local chat AI: Ollama + llama3.2

**AI helpers**
- Whisper → speech to text
- YOLO → keep subject framed
- Llama → rank clip potential
- MiniLM → match memes to jokes
- ffmpeg → cut & export MP4

---

## The journey (7 steps)

1. **Start a job** — Paste a URL or upload. The site starts background work and shows progress.
2. **Ingest** — Save the source video once into storage.
3. **Transcribe** — Whisper listens once and writes timed text.
4. **Find highlights** — Spot wow moments from audio, speech, motion, and chat; drop duplicates.
5. **Rank clips** — A local language model scores what feels worth posting.
6. **Make each clip** — Crop for phones, add captions / memes, export MP4.
7. **Review** — Keep the winners and publish when ready.

---

## Tech stack (simple)

| Piece | Tech | Plain English |
|-------|------|----------------|
| Website | Next.js | Buttons, pages, live progress |
| Server API | FastAPI | Takes requests, starts jobs |
| Work line | Celery + Redis | “Do this next” queue that can retry |
| Memory | PostgreSQL | Remembers jobs and clip metadata |
| Video locker | MinIO | Stores big media files |
| Local chat AI | Ollama + llama3.2 | Ranks clips without a paid API bill |

---

## AI models & tools

| Model / tool | What it does |
|--------------|--------------|
| faster-whisper | Turns talking into timed text for captions |
| YOLOv11 + ByteTrack | Finds the subject and keeps them centered |
| llama3.2 (Ollama) | Compares clips and ranks posting potential |
| MiniLM embedder | Matches a clip’s joke to the right meme |
| librosa + ffmpeg | Times SFX; cuts and encodes the final video (NVENC on NVIDIA for speed) |

---

## Why it’s designed this way

- **Background jobs** — Long videos take minutes; that work can’t live inside one button click.
- **GPU vs normal queue** — Heavy vision/encode work doesn’t wait behind slow chat or downloads.
- **One full transcript** — Listen once, reuse everywhere.
- **Self-hosted** — Your machine, your files, no watermark, no metered cloud clip tax.

---

*Shareable explainer · also available as `qclip-explainer.pdf` / `qclip-explainer.html`*
