# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (beta.19 verified YT+Twitch)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | beta.19 shipped | — | packaging + Twitch format + YOLO tracking |

## Verified on packaged sidecar (beta.19)

- YouTube short + **medium** Whisper → `done` (audio energy on; no tracking fallback)  
- Twitch clip → `done` (format selector fixed for acodec=unknown)  
- Virality skips cleanly when Ollama down  

## Fixed since beta.16 gap list

soundfile DLL bundle, ultralytics/mediapipe/matplotlib collect, ffmpeg→wav audio decode, Ollama probe, Twitch format selector, YOLO weights in cache dir, MediaPipe failure no longer kills YOLO  

## Still blocked externally (not in this ship)

- EV code signing / SmartScreen  
- Hyper-V clean Windows VM  
- Mac Latest (interim beta.6)  
- F13 crash collector + cohort first-clip metrics  
- Full LLM virality without local Ollama / API key  

## Download

Latest → **1.0.0-beta.19**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe  
