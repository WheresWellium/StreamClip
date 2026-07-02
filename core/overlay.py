"""
StreamClip — Overlay Engine
Injects meme GIFs, sticker PNGs, and sound effects (SFX) into clips
using semantic similarity rather than brittle keyword matching.

Instead of checking `if "clutch" in text`, we embed both the clip hook
and every asset's description using a sentence-transformer model, then
match by cosine similarity.  This means:
  "I literally cannot believe that happened" → holy_shit.gif ✓
  "What are the chances of that"             → disbelief.gif ✓
  "We actually won"                          → lets_go.gif   ✓

Assets live in assets/ with a companion JSON manifest that describes
each asset in natural language for the embedding model.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import structlog

from core.config import Settings, OverlayConfig
from core.export_video import audio_encode_args, output_fps_args, video_encode_args
from core.models import ClipCandidate, OverlayAsset

log = structlog.get_logger(__name__)


# ─── Asset manifest ───────────────────────────────────────────────────────────

@dataclass
class AssetRecord:
    path: Path
    asset_type: str           # "gif" | "png" | "mp4"
    description: str          # natural language used for embedding
    sfx_path: Path | None     # companion sound effect
    default_duration: float   # how long to show (seconds)
    tags: list[str]           # backup keyword tags


def load_manifest(assets_dir: Path) -> list[AssetRecord]:
    """
    Load assets/manifest.json and return a list of AssetRecord.
    Auto-generates a stub manifest if none exists yet.
    """
    manifest_path = assets_dir / "manifest.json"
    if not manifest_path.exists():
        _write_stub_manifest(assets_dir, manifest_path)

    with open(manifest_path) as fh:
        raw: list[dict] = json.load(fh)

    records = []
    for item in raw:
        asset_path = assets_dir / item["path"]
        if not asset_path.exists():
            log.warning("asset_missing", path=str(asset_path))
            continue
        sfx = assets_dir / item["sfx"] if item.get("sfx") else None
        records.append(AssetRecord(
            path=asset_path,
            asset_type=item.get("type", asset_path.suffix.lstrip(".")),
            description=item["description"],
            sfx_path=sfx if sfx and sfx.exists() else None,
            default_duration=float(item.get("duration", 2.5)),
            tags=item.get("tags", []),
        ))
    log.info("assets_loaded", count=len(records))
    return records


def records_from_db_assets(
    assets: list,
    storage,
    cache_dir: Path,
) -> list[AssetRecord]:
    """Materialise DB `Asset` rows (backend.db.models) into AssetRecords.

    Files are downloaded from object storage once per job workspace and
    cached by asset id, so repeated clip renders don't re-fetch. Assets that
    fail to download are skipped — overlays degrade, the render never fails.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    records: list[AssetRecord] = []
    for asset in assets:
        try:
            suffix = Path(asset.storage_key).suffix or f".{asset.asset_type}"
            local = cache_dir / f"{asset.id}{suffix}"
            if not local.exists():
                storage.download(asset.storage_key, local)

            sfx_local: Path | None = None
            if asset.sfx_storage_key:
                sfx_local = cache_dir / f"{asset.id}_sfx{Path(asset.sfx_storage_key).suffix}"
                if not sfx_local.exists():
                    storage.download(asset.sfx_storage_key, sfx_local)

            records.append(AssetRecord(
                path=local,
                asset_type=asset.asset_type,
                description=asset.description,
                sfx_path=sfx_local,
                default_duration=float(asset.default_duration_secs or 2.5),
                tags=list(asset.tags or []),
            ))
        except Exception as exc:
            log.warning("db_asset_skip", asset_id=asset.id, error=str(exc))
    if records:
        log.info("db_assets_loaded", count=len(records))
    return records


def _write_stub_manifest(assets_dir: Path, out: Path) -> None:
    """Create a starter manifest with common gaming assets."""
    stub = [
        {
            "path": "gifs/hype.gif",
            "type": "gif",
            "description": "absolute hype, let's go, incredible win, amazing play, fire moment, clutch victory",
            "sfx": "sfx/airhorn.mp3",
            "duration": 2.5,
            "tags": ["hype", "win", "clutch", "fire"],
        },
        {
            "path": "gifs/holy_shit.gif",
            "type": "gif",
            "description": "disbelief, unbelievable, cannot believe, shocked, mind blown, what just happened",
            "sfx": "sfx/vine_boom.mp3",
            "duration": 2.0,
            "tags": ["holy", "shocked", "disbelief"],
        },
        {
            "path": "gifs/fail.gif",
            "type": "gif",
            "description": "epic fail, I died, we lost, terrible mistake, that was awful, RIP",
            "sfx": "sfx/sad_trombone.mp3",
            "duration": 2.0,
            "tags": ["fail", "dead", "rip", "loss"],
        },
        {
            "path": "gifs/rage.gif",
            "type": "gif",
            "description": "rage, anger, furious, tilted, malding, so frustrated, this game is broken",
            "sfx": None,
            "duration": 2.5,
            "tags": ["rage", "angry", "tilted"],
        },
        {
            "path": "gifs/lul.gif",
            "type": "gif",
            "description": "laughing, that's hilarious, so funny, comedy, unexpected, absurd",
            "sfx": "sfx/laugh.mp3",
            "duration": 2.0,
            "tags": ["funny", "laugh", "lul"],
        },
        {
            "path": "stickers/skull.png",
            "type": "png",
            "description": "died, eliminated, got killed, took damage, lost a life",
            "sfx": "sfx/vine_boom.mp3",
            "duration": 1.5,
            "tags": ["death", "eliminated"],
        },
        {
            "path": "stickers/fire.png",
            "type": "png",
            "description": "on fire, insane streak, hot, dominating, unstoppable",
            "sfx": None,
            "duration": 2.0,
            "tags": ["fire", "streak", "insane"],
        },
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        json.dump(stub, fh, indent=2)
    log.info("stub_manifest_written", path=str(out))


# ─── Semantic matcher ─────────────────────────────────────────────────────────

class _SemanticMatcher:
    """
    Embeds asset descriptions and query text using a sentence-transformers
    model.  Fully local — no API calls.
    Model is downloaded once (~90MB for all-MiniLM-L6-v2).
    """

    MODEL_NAME = "all-MiniLM-L6-v2"   # fast, accurate, 384-dim embeddings

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer
        log.info("loading_embedding_model", model=self.MODEL_NAME)
        self._model = SentenceTransformer(self.MODEL_NAME)
        self._asset_embeddings: np.ndarray | None = None
        self._assets: list[AssetRecord] = []

    def index_assets(self, assets: list[AssetRecord]) -> None:
        self._assets = assets
        descriptions = [a.description for a in assets]
        self._asset_embeddings = self._model.encode(
            descriptions, convert_to_numpy=True, normalize_embeddings=True
        )
        log.info("assets_indexed", count=len(assets))

    def query(self, text: str, top_k: int = 3) -> list[tuple[AssetRecord, float]]:
        """Return up to top_k assets with their cosine-similarity scores."""
        if self._asset_embeddings is None or not self._assets:
            return []

        q_emb = self._model.encode(
            [text], convert_to_numpy=True, normalize_embeddings=True
        )
        # Cosine similarity (embeddings are already L2-normalised)
        sims = (self._asset_embeddings @ q_emb.T).flatten()

        top_idx = np.argsort(sims)[::-1][:top_k]
        return [(self._assets[i], float(sims[i])) for i in top_idx]


# ─── Peak-frame finder ────────────────────────────────────────────────────────

def _find_audio_peak(clip_path: Path, window_start: float = 0.0) -> float:
    """
    Use librosa to find the frame with the highest audio energy in the clip.
    Returns a timestamp in seconds (relative to clip start).
    Falls back to window_start + 0.5s if librosa is unavailable.
    """
    try:
        import librosa
        y, sr = librosa.load(str(clip_path), sr=22050, mono=True, offset=window_start)
        if len(y) == 0:
            return window_start + 0.5
        rms = librosa.feature.rms(y=y)[0]
        peak_frame = int(np.argmax(rms))
        hop = 512
        peak_time = window_start + librosa.frames_to_time(peak_frame, sr=sr, hop_length=hop)
        return float(peak_time)
    except Exception:
        return window_start + 0.5


# ─── FFmpeg overlay compositor ────────────────────────────────────────────────

def _build_overlay_filtergraph(
    assets: list[tuple[OverlayAsset, int]],   # (asset, input_idx)
    pos_map: dict[str, str],
) -> str:
    """
    Build an FFmpeg filter_complex string for chaining multiple GIF/PNG overlays.

    Each overlay is:
      [N:v] scale → looped gif or static png → overlaid at position
      enabled only between trigger_time and trigger_time + duration
    """
    chain = "[0:v]"
    steps: list[str] = []
    pad_idx = 0

    for asset, input_idx in assets:
        scaled = f"scaled{pad_idx}"
        result = f"res{pad_idx}"
        pos = pos_map.get(asset.position, "W-w-40:40")
        t0 = asset.trigger_time
        t1 = t0 + asset.duration

        if asset.asset_type == "gif":
            scale_step = (
                f"[{input_idx}:v]"
                f"scale=iw*0.28:-1,"
                f"loop=-1:1:0,"
                f"setpts=PTS-STARTPTS+{t0}/TB"
                f"[{scaled}]"
            )
        else:
            # PNG sticker — no loop needed
            scale_step = (
                f"[{input_idx}:v]"
                f"scale=iw*0.22:-1"
                f"[{scaled}]"
            )

        steps.append(scale_step)
        overlay_step = (
            f"{chain}[{scaled}]"
            f"overlay={pos}:enable='between(t,{t0:.3f},{t1:.3f})'"
            f"[{result}]"
        )
        steps.append(overlay_step)
        chain = f"[{result}]"
        pad_idx += 1

    # Drop the trailing brackets from chain for the final output map
    return ";".join(steps), chain.strip("[]")


def _add_sfx(
    input_video: Path,
    sfx_path: Path,
    trigger_time: float,
    volume_db: float,
    output_path: Path,
) -> None:
    """Mux a sound effect into the video at a specific timestamp."""
    # adelay puts the SFX at trigger_time ms into the audio timeline
    delay_ms = int(trigger_time * 1000)
    filter_complex = (
        f"[1:a]volume={volume_db}dB,adelay={delay_ms}|{delay_ms}[sfx];"
        f"[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=1[aout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-i", str(sfx_path),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "256k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


# ─── Public API ───────────────────────────────────────────────────────────────

_matcher: _SemanticMatcher | None = None
_matcher_signature: tuple[str, ...] | None = None


def _get_matcher(assets: list[AssetRecord]) -> _SemanticMatcher:
    """Model load is cached forever; the asset index is rebuilt only when the
    asset set changes (e.g. a job owner has different vault assets)."""
    global _matcher, _matcher_signature
    signature = tuple(sorted(str(a.path) for a in assets))
    if _matcher is None:
        _matcher = _SemanticMatcher()
    if signature != _matcher_signature:
        _matcher.index_assets(assets)
        _matcher_signature = signature
    return _matcher


def apply_overlays(
    clip_path: Path,
    output_path: Path,
    candidate: ClipCandidate,
    cfg: Settings,
    extra_assets: list[AssetRecord] | None = None,
) -> tuple[Path, list[OverlayAsset]]:
    """
    Select and composite meme overlays + SFX onto the clip.

    Uses sentence-transformer cosine similarity to match the clip's hook
    text against asset descriptions.  Only injects if similarity exceeds
    cfg.overlay.semantic_threshold.

    Args:
        clip_path:    The captioned 9:16 clip.
        output_path:  Where to write the final overlaid clip.
        candidate:    ClipCandidate with hook text and meme_keywords.
        cfg:          Global settings.
        extra_assets: DB-backed user assets (see records_from_db_assets),
                      merged with the filesystem manifest.

    Returns:
        (path_to_output, list_of_applied_overlays)
    """
    ocfg: OverlayConfig = cfg.overlay
    if not ocfg.enabled:
        import shutil
        shutil.copy2(clip_path, output_path)
        return output_path, []

    assets_dir = ocfg.assets_dir

    # ── Load assets (filesystem manifest + user vault) ─────────────────────
    asset_records = load_manifest(assets_dir) + list(extra_assets or [])
    if not asset_records:
        log.warning("no_assets_found", dir=str(assets_dir))
        import shutil
        shutil.copy2(clip_path, output_path)
        return output_path, []

    matcher = _get_matcher(asset_records)

    # ── Build query from LLM hook + keywords ──────────────────────────────
    keyword_str = " ".join(candidate.meme_keywords)
    query = f"{candidate.llm_hook} {keyword_str} {candidate.emotion.value}"

    matches = matcher.query(query, top_k=ocfg.max_overlays_per_clip + 2)
    log.debug("overlay_candidates", query=query, matches=[
        f"{a.path.name}:{sim:.3f}" for a, sim in matches
    ])

    # ── Filter by threshold ───────────────────────────────────────────────
    selected: list[tuple[AssetRecord, float]] = [
        (a, sim) for a, sim in matches if sim >= ocfg.semantic_threshold
    ][:ocfg.max_overlays_per_clip]

    if not selected:
        log.info("no_overlays_above_threshold", threshold=ocfg.semantic_threshold)
        import shutil
        shutil.copy2(clip_path, output_path)
        return output_path, []

    # ── Decide trigger times (spread through clip) ────────────────────────
    clip_duration = _probe_duration(clip_path)
    applied: list[OverlayAsset] = []
    spacing = clip_duration / (len(selected) + 1)

    for i, (record, sim) in enumerate(selected):
        base_time = spacing * (i + 1)
        if ocfg.appear_at_peak:
            # Find the audio energy peak near this base time
            trigger = _find_audio_peak(
                clip_path,
                window_start=max(0.0, base_time - 1.5),
            )
            trigger = max(0.2, min(trigger, clip_duration - record.default_duration - 0.2))
        else:
            trigger = base_time

        applied.append(OverlayAsset(
            asset_path=record.path,
            asset_type=record.asset_type,
            sfx_path=record.sfx_path,
            trigger_time=trigger,
            duration=record.default_duration,
            position=ocfg.position,
            similarity_score=sim,
            matched_keyword=", ".join(record.tags[:3]),
        ))

    # ── Composite video overlays ──────────────────────────────────────────
    pos_map = {
        "top_right":    "W-w-40:40",
        "top_left":     "40:40",
        "bottom_right": "W-w-40:H-h-40",
        "bottom_left":  "40:H-h-40",
        "center":       "(W-w)/2:(H-h)/2",
    }

    inputs: list[str] = ["-i", str(clip_path)]
    for oa in applied:
        inputs += ["-ignore_loop", "0", "-i", str(oa.asset_path)]

    indexed = [(oa, idx + 1) for idx, oa in enumerate(applied)]
    filter_complex, last_label = _build_overlay_filtergraph(indexed, pos_map)

    sfx_assets = [oa for oa in applied if oa.sfx_path]

    # If we have SFX, we need an intermediate file first
    if sfx_assets:
        intermediate = output_path.with_stem(output_path.stem + "_nosfx")
    else:
        intermediate = output_path

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-map", "0:a?",
        *video_encode_args(cfg.export, crf=16),
        *audio_encode_args(cfg.export),
        *output_fps_args(cfg.export),
        str(intermediate),
    ]
    log.debug("overlay_ffmpeg", inputs=len(inputs))
    subprocess.run(cmd, check=True, capture_output=True)

    # ── Layer SFX ─────────────────────────────────────────────────────────
    current = intermediate
    for oa in sfx_assets:
        tmp = current.with_stem(current.stem + "_sfx")
        _add_sfx(current, oa.sfx_path, oa.trigger_time, ocfg.sfx_volume_db, tmp)
        if current != intermediate:
            current.unlink(missing_ok=True)
        current = tmp

    if current != output_path:
        import shutil
        shutil.move(str(current), str(output_path))
    if intermediate.exists() and intermediate != output_path:
        intermediate.unlink(missing_ok=True)

    log.info(
        "overlays_applied",
        count=len(applied),
        assets=[oa.asset_path.name for oa in applied],
        output=str(output_path),
    )
    return output_path, applied


def _probe_duration(clip_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(clip_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json
    return float(json.loads(result.stdout)["format"]["duration"])
