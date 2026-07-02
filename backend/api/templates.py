"""Job template CRUD — saved creator presets."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import CreateJobTemplateRequest, JobTemplateOut
from backend.db.repositories import JobTemplateRepository
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.rate_limit import rate_limit_request
from core.errors import StreamClipError

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get(
    "",
    response_model=list[JobTemplateOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_templates(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[JobTemplateOut]:
    repo = JobTemplateRepository(db)
    templates = await repo.list_for_user(user_id)
    return [JobTemplateOut.model_validate(t) for t in templates]


@router.post(
    "",
    response_model=JobTemplateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def create_template(
    body: CreateJobTemplateRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobTemplateOut:
    repo = JobTemplateRepository(db)
    templates = await repo.list_for_user(user_id)
    if len(templates) >= 20:
        raise StreamClipError(
            "Template limit reached (20)",
            user_message="Delete an existing template before saving a new one.",
        )
    tpl = await repo.create(user_id, body.name, body.config_json)
    await db.commit()
    return JobTemplateOut.model_validate(tpl)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_request)],
)
async def delete_template(
    template_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = JobTemplateRepository(db)
    deleted = await repo.delete(template_id, user_id)
    if not deleted:
        raise StreamClipError("Template not found", user_message="Template not found")
    await db.commit()
