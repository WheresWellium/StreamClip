"""
StreamClip — Creator option catalogs (single source of truth).

Rich metadata for /api/meta and validation. Processing weights live in
content_profiles.py; reframe parameters in reframe.py; ASS styles in captions.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Default export target (overridable per job / per clip via aspect_ratio).
OUTPUT_ASPECT_RATIO = "9:16"
OUTPUT_RESOLUTION = "1080×1920"
OUTPUT_PLATFORMS = ("TikTok", "YouTube Shorts", "Instagram Reels", "Snap Spotlight")


# ─── Export aspect ratios ─────────────────────────────────────────────────────
# The curated, highest-quality social export set (Premiere-style dropdown).

@dataclass(frozen=True)
class AspectRatioOption:
    id: str                    # canonical "W:H" id, e.g. "9:16"
    label: str
    width: int                 # output pixel dimensions at highest social quality
    height: int
    description: str
    platforms: tuple[str, ...]

    def to_meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "width": self.width,
            "height": self.height,
            "output_resolution": f"{self.width}×{self.height}",
            "aspect_ratio": self.id,
            "description": self.description,
            "platforms": list(self.platforms),
        }


ASPECT_RATIO_OPTIONS: tuple[AspectRatioOption, ...] = (
    AspectRatioOption(
        id="9:16",
        label="Vertical 9:16",
        width=1080, height=1920,
        description="Full-screen vertical — the short-form default.",
        platforms=("TikTok", "YouTube Shorts", "Instagram Reels", "Snap Spotlight"),
    ),
    AspectRatioOption(
        id="1:1",
        label="Square 1:1",
        width=1080, height=1080,
        description="Square feed post — maximum feed real estate on X and LinkedIn.",
        platforms=("Instagram Feed", "X / Twitter", "LinkedIn", "Facebook"),
    ),
    AspectRatioOption(
        id="4:5",
        label="Portrait 4:5",
        width=1080, height=1350,
        description="Tall feed post — the largest format Instagram allows in-feed.",
        platforms=("Instagram Feed", "Facebook Feed"),
    ),
    AspectRatioOption(
        id="16:9",
        label="Landscape 16:9",
        width=1920, height=1080,
        description="Widescreen — standard for YouTube and landscape embeds.",
        platforms=("YouTube", "X / Twitter", "LinkedIn", "Facebook"),
    ),
    AspectRatioOption(
        id="2:3",
        label="Portrait 2:3",
        width=1080, height=1620,
        description="Tall pin format — Pinterest's recommended video ratio.",
        platforms=("Pinterest",),
    ),
)

ASPECT_RATIO_IDS: tuple[str, ...] = tuple(o.id for o in ASPECT_RATIO_OPTIONS)
DEFAULT_ASPECT_RATIO = "9:16"

_ASPECT_RATIO_BY_ID: dict[str, AspectRatioOption] = {o.id: o for o in ASPECT_RATIO_OPTIONS}


def list_aspect_ratios() -> list[dict[str, Any]]:
    return [o.to_meta() for o in ASPECT_RATIO_OPTIONS]


def is_valid_aspect_ratio(value: str) -> bool:
    return value in _ASPECT_RATIO_BY_ID


def aspect_ratio_dimensions(value: str) -> tuple[int, int]:
    """Return (width, height) for a catalog aspect ratio id, defaulting to 9:16."""
    option = _ASPECT_RATIO_BY_ID.get(value, _ASPECT_RATIO_BY_ID[DEFAULT_ASPECT_RATIO])
    return option.width, option.height


@dataclass(frozen=True)
class CreatorOption:
    id: str
    label: str
    description: str
    best_for: str
    aspect_ratio: str = OUTPUT_ASPECT_RATIO
    output_resolution: str = OUTPUT_RESOLUTION
    platforms: tuple[str, ...] = OUTPUT_PLATFORMS
    preview_hint: str = ""
    category: str = ""
    tags: tuple[str, ...] = ()
    # Content profiles only: presets auto-applied when the profile is chosen,
    # so the "best for" promise carries through cropping and captions.
    recommended_reframe: str = ""
    recommended_captions: str = ""

    def to_meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "best_for": self.best_for,
            "aspect_ratio": self.aspect_ratio,
            "output_resolution": self.output_resolution,
            "platforms": list(self.platforms),
            "preview_hint": self.preview_hint,
            "category": self.category,
            "tags": list(self.tags),
            "recommended_reframe": self.recommended_reframe,
            "recommended_captions": self.recommended_captions,
        }


CONTENT_PROFILE_OPTIONS: tuple[CreatorOption, ...] = (
    CreatorOption(
        id="gaming",
        label="Gaming / Twitch",
        description="Fast action, motion-heavy gameplay moments — plus chat-spike detection on Twitch VODs.",
        best_for="FPS, MOBA, battle royale, variety streams",
        category="live",
        tags=("twitch", "gameplay", "highlights"),
        recommended_reframe="fps_game",
        recommended_captions="gaming_impact",
    ),
    CreatorOption(
        id="esports",
        label="Esports / Casted",
        description="Caster hype layered with on-screen team fights — chat spikes weighted on Twitch VODs.",
        best_for="Tournament VODs, co-streams, analyst desk clips",
        category="live",
        tags=("esports", "casters", "competitive"),
        recommended_reframe="fps_game",
        recommended_captions="shorts_bold",
    ),
    CreatorOption(
        id="irl",
        label="IRL / Just Chatting",
        description="Talking head, reactions, and conversational peaks.",
        best_for="IRL streams, Q&A, reaction content",
        category="live",
        tags=("irl", "reactions", "facecam"),
        recommended_reframe="irl",
        recommended_captions="tiktok_pop",
    ),
    CreatorOption(
        id="vlog",
        label="Vlog / Lifestyle",
        description="Day-in-the-life, travel, and creator-led storytelling.",
        best_for="YouTube vlogs, B-roll montages, lifestyle uploads",
        category="long-form",
        tags=("vlog", "lifestyle", "creator"),
        recommended_reframe="cinematic_wide",
        recommended_captions="shorts_bold",
    ),
    CreatorOption(
        id="podcast",
        label="Podcast / Interview",
        description="Dialogue-driven highlights with minimal motion weighting.",
        best_for="Podcasts, interviews, panel shows, webinars",
        category="long-form",
        tags=("podcast", "dialogue", "talking"),
        recommended_reframe="podcast",
        recommended_captions="podcast_clean",
    ),
    CreatorOption(
        id="education",
        label="Education / Course",
        description="Explainers, tutorials, and insight-dense teaching moments.",
        best_for="Courses, how-tos, tech reviews, lecture clips",
        category="long-form",
        tags=("education", "tutorial", "explainer"),
        recommended_reframe="presentation",
        recommended_captions="minimal_white",
    ),
    CreatorOption(
        id="sports",
        label="Sports / Athletics",
        description="Play-by-play energy, crowd reactions, and athletic motion.",
        best_for="Game film, highlights reels, gym and field sports",
        category="long-form",
        tags=("sports", "athletics", "highlights"),
        recommended_reframe="sports_action",
        recommended_captions="shorts_bold",
    ),
    CreatorOption(
        id="music",
        label="Music / Performance",
        description="Beat drops, vocal peaks, and performance energy.",
        best_for="Concerts, DJ sets, music videos, cover performances",
        category="long-form",
        tags=("music", "performance", "audio"),
        recommended_reframe="music_performance",
        recommended_captions="karaoke_highlight",
    ),
    CreatorOption(
        id="general",
        label="General / Mixed",
        description="Balanced defaults when content spans multiple styles.",
        best_for="Mixed uploads, first-time jobs, unknown source",
        category="general",
        tags=("default", "mixed"),
        recommended_reframe="auto",
        recommended_captions="shorts_bold",
    ),
)

REFRAME_PRESET_OPTIONS: tuple[CreatorOption, ...] = (
    CreatorOption(
        id="fps_game",
        label="FPS / Shooter",
        description="Tracks player POV with HUD-safe crop — health, ammo, and kill feed preserved.",
        best_for="Valorant, CS2, Apex, Call of Duty",
        preview_hint="Fast pans · bottom HUD reserve",
        category="gaming",
        tags=("fps", "shooter", "hud"),
    ),
    CreatorOption(
        id="moba",
        label="MOBA / Strategy",
        description="Slower framing with minimap and ability-bar safe zones.",
        best_for="League, Dota 2, RTS, grand strategy",
        preview_hint="Stable camera · minimap aware",
        category="gaming",
        tags=("moba", "strategy"),
    ),
    CreatorOption(
        id="battle_royale",
        label="Battle Royale",
        description="Aggressive player tracking for wide-map movement and fights.",
        best_for="Fortnite, PUBG, Warzone",
        preview_hint="Fast follow · wide scene",
        category="gaming",
        tags=("br", "survival"),
    ),
    CreatorOption(
        id="sports_action",
        label="Sports / Action",
        description="Follows athletes and ball movement with athletic pacing.",
        best_for="Field sports, combat sports, workout footage",
        preview_hint="Motion tracking · full-body",
        category="sports",
        tags=("sports", "action"),
    ),
    CreatorOption(
        id="irl",
        label="IRL / Talking Head",
        description="Tight face crop with minimal camera drift.",
        best_for="Just chatting, reactions, street interviews",
        preview_hint="Face-centered · stable",
        category="talking",
        tags=("irl", "facecam"),
    ),
    CreatorOption(
        id="podcast",
        label="Podcast / Dialogue",
        description="Stable speaker framing for seated or studio setups.",
        best_for="Podcast video, interviews, remote panels",
        preview_hint="Speaker lock · low motion",
        category="talking",
        tags=("podcast", "studio"),
    ),
    CreatorOption(
        id="presentation",
        label="Presentation / Slides",
        description="Center-weighted crop for screen shares and slide decks.",
        best_for="Webinars, lectures, product demos, slide recordings",
        preview_hint="Center crop · slide-safe",
        category="education",
        tags=("slides", "webinar", "screen"),
    ),
    CreatorOption(
        id="cinematic_wide",
        label="Cinematic / B-roll",
        description="Gentle pans for scenic, travel, and cinematic wide shots.",
        best_for="Travel vlogs, nature, film-style B-roll",
        preview_hint="Slow pan · scenic",
        category="cinematic",
        tags=("b-roll", "travel", "cinematic"),
    ),
    CreatorOption(
        id="music_performance",
        label="Music / Performance",
        description="Stage-centered framing for performers, DJs, and instrument focus.",
        best_for="Concerts, DJ sets, music videos, cover performances",
        preview_hint="Performer lock · stage center",
        category="music",
        tags=("music", "stage", "performance"),
    ),
    CreatorOption(
        id="auto",
        label="Auto-detect",
        description="Picks FPS-style for hype/clutch moments, talking-head otherwise.",
        best_for="Unsure which preset fits — good default",
        preview_hint="Emotion-aware · automatic",
        category="smart",
        tags=("auto", "default"),
    ),
)

CAPTION_STYLE_OPTIONS: tuple[CreatorOption, ...] = (
    CreatorOption(
        id="gaming_impact",
        label="Gaming Impact",
        description="Bold Impact font, karaoke sync, and gaming keyword highlights.",
        best_for="Gameplay clips, clutch moments, stream highlights",
        preview_hint="IMPACT · yellow highlights · bottom",
        category="gaming",
        tags=("karaoke", "gaming"),
    ),
    CreatorOption(
        id="shorts_bold",
        label="Shorts Bold",
        description="Extra-large punchy text — high-retention Shorts and Reels style.",
        best_for="Viral hooks, MrBeast-style retention edits",
        preview_hint="Huge bold · high contrast · pop-in",
        category="shorts",
        tags=("viral", "bold", "shorts"),
    ),
    CreatorOption(
        id="tiktok_pop",
        label="TikTok Pop",
        description="Rounded bold font with per-word colour and bounce animation.",
        best_for="TikTok trends, meme edits, fast-paced cuts",
        preview_hint="Rounded · colour pop · bounce",
        category="shorts",
        tags=("tiktok", "trend"),
    ),
    CreatorOption(
        id="karaoke_highlight",
        label="Karaoke Highlight",
        description="Word-by-word fill highlight — viewers read along in sync.",
        best_for="Lyrics, punchlines, quotable moments",
        preview_hint="Word highlight · sync fill",
        category="shorts",
        tags=("karaoke", "sync"),
    ),
    CreatorOption(
        id="minimal_white",
        label="Minimal White",
        description="Clean white Helvetica subtitles with thin outline.",
        best_for="Professional clips, subtle captions, brand-safe",
        preview_hint="Helvetica · white · minimal",
        category="clean",
        tags=("minimal", "professional"),
    ),
    CreatorOption(
        id="podcast_clean",
        label="Podcast Clean",
        description="Readable lower-third dialogue captions for long speech.",
        best_for="Podcasts, interviews, talking-head excerpts",
        preview_hint="Lower third · readable · neutral",
        category="talking",
        tags=("podcast", "dialogue"),
    ),
    CreatorOption(
        id="accessibility_clean",
        label="Accessibility",
        description="High-contrast, larger type with safe margins for readability.",
        best_for="WCAG-friendly captions, older audiences, noisy audio",
        preview_hint="Large · high contrast · safe zone",
        category="accessibility",
        tags=("a11y", "readable"),
    ),
    CreatorOption(
        id="none",
        label="No Captions",
        description="Skip burned-in captions — use platform auto-captions or edit later.",
        best_for="Music videos, pre-subtitled sources, manual captioning",
        preview_hint="No burn-in · video only",
        category="none",
        tags=("off", "no-captions"),
    ),
)

CONTENT_PROFILE_IDS: tuple[str, ...] = tuple(o.id for o in CONTENT_PROFILE_OPTIONS)
REFRAME_PRESET_IDS: tuple[str, ...] = tuple(o.id for o in REFRAME_PRESET_OPTIONS)
CAPTION_STYLE_IDS: tuple[str, ...] = tuple(o.id for o in CAPTION_STYLE_OPTIONS)


def list_content_profiles() -> list[dict[str, Any]]:
    return [o.to_meta() for o in CONTENT_PROFILE_OPTIONS]


def list_reframe_presets() -> list[dict[str, Any]]:
    return [o.to_meta() for o in REFRAME_PRESET_OPTIONS]


def list_caption_styles() -> list[dict[str, Any]]:
    return [o.to_meta() for o in CAPTION_STYLE_OPTIONS]


def is_valid_content_profile(value: str) -> bool:
    return value in CONTENT_PROFILE_IDS


def is_valid_reframe_preset(value: str) -> bool:
    return value in REFRAME_PRESET_IDS


def is_valid_caption_style(value: str) -> bool:
    return value in CAPTION_STYLE_IDS
