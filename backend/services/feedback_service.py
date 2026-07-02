"""Clip feedback → per-user style weight learning.

Shared by explicit ratings (settings API) and implicit signals
(clip approval/rejection), so both feed the same learning loop.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import JobRepository, UserRepository
from core.style_learning import apply_feedback_to_user_weights

# Approving a clip is a strong positive signal; rejecting a strong negative.
APPROVAL_IMPLICIT_RATING: dict[str, int] = {
    "approved": 5,
    "rejected": 1,
}


async def apply_clip_style_feedback(
    db: AsyncSession,
    *,
    clip,
    user_id: str,
    rating: int,
) -> None:
    """Nudge the user's per-profile signal weights from a clip rating."""
    users = UserRepository(db)
    user = await users.get(user_id)
    if user is None:
        return

    job = await JobRepository(db).get(clip.job_id)
    profile = (
        (job.config_snapshot or {}).get("content_profile", "general")
        if job else "general"
    )
    weights = apply_feedback_to_user_weights(
        user.style_weights,
        profile=str(profile),
        rating=rating,
        clip_scores={
            "audio": clip.audio_score,
            "spectral": clip.spectral_score,
            "flow": clip.flow_score,
            "chat": clip.chat_score,
            "llm": clip.llm_score,
        },
    )
    await users.update_style_weights(user_id, weights)
