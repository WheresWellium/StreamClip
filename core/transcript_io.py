"""
StreamClip — Transcript JSON persistence

Lightweight load/save for persisted transcripts. Kept separate from
core.transcribe so API-side consumers can read transcript.json without
importing faster-whisper.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.config import Settings
from core.models import Transcript, TranscriptSegment, Word
from core.storage import Storage, job_key


def save_transcript(transcript: Transcript, path: Path) -> None:
    data = {
        "language": transcript.language,
        "duration": transcript.duration,
        "source_path": str(transcript.source_path),
        "segments": [
            {
                "id": s.id,
                "text": s.text,
                "start": s.start,
                "end": s.end,
                "speaker": s.speaker,
                "words": [
                    {"text": w.text, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in s.words
                ],
            }
            for s in transcript.segments
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_transcript(path: Path) -> Transcript:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    segments = [
        TranscriptSegment(
            id=s["id"],
            text=s["text"],
            start=s["start"],
            end=s["end"],
            speaker=s.get("speaker"),
            words=tuple(
                Word(
                    text=w["text"],
                    start=w["start"],
                    end=w["end"],
                    probability=w["probability"],
                )
                for w in s.get("words", [])
            ),
        )
        for s in data["segments"]
    ]
    return Transcript(
        segments=segments,
        language=data["language"],
        duration=data["duration"],
        source_path=Path(data["source_path"]),
    )


def load_persisted_job_transcript(
    job_id: str,
    cfg: Settings,
    storage: Storage,
) -> Transcript:
    """
    Load a job's persisted transcript from workspace or object storage.

    Raises FileNotFoundError when the transcript has not been produced yet;
    never falls back to transcription (safe for API-side use).
    """
    workspace = cfg.workspace_dir / "jobs" / job_id
    local_json = workspace / "transcript.json"
    key = job_key(job_id, "transcript", "transcript.json")

    if not local_json.exists() and storage.exists(key):
        storage.download(key, local_json)

    if not local_json.exists():
        raise FileNotFoundError(f"No persisted transcript for job {job_id}")
    return load_transcript(local_json)
