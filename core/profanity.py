"""
StreamClip — Profanity filter

Word-level censoring for burned-in captions and clip metadata (title/hook).
Operates on already-collected caption words so timing stays aligned — no
extra transcription or render passes (performance-first).

Modes:
  mask  — keep first letter, replace the rest with asterisks ("f***")
  bleep — replace the whole token with bullets ("•••")
  omit  — drop the word from the caption group entirely
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import structlog

from core.models import Word

log = structlog.get_logger(__name__)

PROFANITY_MODES = ("mask", "bleep", "omit")

_BLEEP_TOKEN = "•••"

# Strip leading/trailing punctuation when matching tokens against the list.
_EDGE_PUNCT = re.compile(r"^\W+|\W+$", re.UNICODE)

# Basic leetspeak / symbol substitutions so "sh1t" or "f@ck" still match.
_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "@": "a", "$": "s", "!": "i",
})

# Bundled fallback so the filter still works if the wordlist file is missing.
_BUILTIN_WORDS = frozenset({
    "fuck", "fucking", "fucked", "fucker", "motherfucker",
    "shit", "shitty", "bullshit",
    "bitch", "bitches",
    "asshole", "arsehole",
    "cunt", "dick", "cock", "pussy",
    "bastard", "slut", "whore",
    "nigger", "nigga", "faggot", "retard", "retarded",
    "goddamn", "damn",
})


def default_wordlist_path() -> Path:
    """Bundled English wordlist shipped with the repo."""
    return Path(__file__).resolve().parent.parent / "config" / "profanity_en.txt"


@lru_cache(maxsize=4)
def _load_wordlist_cached(path_str: str) -> frozenset[str]:
    path = Path(path_str)
    try:
        words = {
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        if words:
            return frozenset(words)
    except OSError as exc:
        log.warning("profanity_wordlist_unreadable", path=path_str, error=str(exc))
    return _BUILTIN_WORDS


def load_profanity_words(path: Path | None = None) -> frozenset[str]:
    """Load the profanity wordlist (cached per path); falls back to builtin."""
    return _load_wordlist_cached(str(path or default_wordlist_path()))


def _normalize_variants(token: str) -> tuple[str, str]:
    """
    Two normalizations: edge symbols can be punctuation ("Fuck!") or
    leetspeak ("$hit"), so strip-then-translate and translate-then-strip
    are both checked.
    """
    low = token.lower()
    strip_first = _EDGE_PUNCT.sub("", low).translate(_LEET_MAP)
    translate_first = _EDGE_PUNCT.sub("", low.translate(_LEET_MAP))
    return strip_first, translate_first


def is_profane(token: str, words: frozenset[str] | None = None) -> bool:
    """True when the token (punctuation/leet-normalized) is on the list."""
    if not token:
        return False
    vocab = words if words is not None else load_profanity_words()
    return any(v in vocab for v in _normalize_variants(token))


def censor_token(token: str, mode: str = "mask") -> str | None:
    """
    Censor a single token. Returns the replacement text, or ``None`` when
    the word should be omitted entirely (mode="omit").
    """
    if mode == "omit":
        return None
    if mode == "bleep":
        return _BLEEP_TOKEN
    # mask: preserve leading/trailing punctuation and the first letter
    core = _EDGE_PUNCT.sub("", token)
    if not core:
        return token
    prefix_len = token.find(core[0])
    prefix = token[:prefix_len] if prefix_len > 0 else ""
    suffix = token[prefix_len + len(core):]
    return f"{prefix}{core[0]}{'*' * max(1, len(core) - 1)}{suffix}"


def censor_words(
    caption_words: list[Word],
    mode: str = "mask",
    *,
    wordlist_path: Path | None = None,
) -> list[Word]:
    """
    Apply the profanity filter to caption words, preserving timing.

    mask/bleep replace text in place; omit drops the word (its screen time
    is absorbed by the surrounding group).
    """
    vocab = load_profanity_words(wordlist_path)
    result: list[Word] = []
    censored = 0
    for w in caption_words:
        if not is_profane(w.text, vocab):
            result.append(w)
            continue
        replacement = censor_token(w.text, mode)
        censored += 1
        if replacement is None:
            continue
        result.append(
            Word(text=replacement, start=w.start, end=w.end, probability=w.probability)
        )
    if censored:
        log.info("profanity_censored", count=censored, mode=mode)
    return result


def censor_text(
    text: str,
    mode: str = "mask",
    *,
    wordlist_path: Path | None = None,
) -> str:
    """Censor free text (titles, hooks, overlay text) token-by-token."""
    if not text:
        return text
    vocab = load_profanity_words(wordlist_path)
    out: list[str] = []
    for token in text.split():
        if is_profane(token, vocab):
            replacement = censor_token(token, mode)
            if replacement is None:
                continue
            out.append(replacement)
        else:
            out.append(token)
    return " ".join(out)
