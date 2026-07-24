"""Job title suggestions API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import TitleSuggestionsResponse
from backend.db.session import get_db
from backend.middleware.rate_limit import rate_limit_request
from backend.middleware.scope import RequestScope, get_request_scope
from backend.services.job_service import JobService
from core.config import get_settings
from core.storage import make_storage
from core.title_suggestions import DEFAULT_TONE

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _get_service(db: AsyncSession) -> JobService:
    cfg = get_settings()
    return JobService(db, cfg, make_storage(cfg))


@router.get(
    "/{job_id}/title-suggestions",
    dependencies=[Depends(rate_limit_request)],
    response_model=TitleSuggestionsResponse,
)
async def get_title_suggestions(
    job_id: str,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tone: str = Query(DEFAULT_TONE, description="Title tone: gaming, tutorial, tip, explainer, promo"),
) -> TitleSuggestionsResponse:
    """Return ranked LLM title suggestions for a job."""
    svc = _get_service(db)
    return await svc.get_title_suggestions(job_id, scope=scope, tone=tone)
