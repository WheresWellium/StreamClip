"""User asset vault API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AssetOut, CreateAssetRequest
from backend.db.repositories import AssetRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.rate_limit import rate_limit_request
from core.errors import StreamClipError

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get(
    "",
    response_model=list[AssetOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_assets(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AssetOut]:
    repo = AssetRepository(db)
    assets = await repo.list_for_user(user_id)
    return [AssetOut.model_validate(a) for a in assets]


@router.post(
    "",
    response_model=AssetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def create_asset(
    body: CreateAssetRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetOut:
    repo = AssetRepository(db)
    owned = [a for a in await repo.list_for_user(user_id) if a.owner_id == user_id]
    if len(owned) >= 50:
        raise StreamClipError(
            "Asset limit reached (50)",
            user_message="Remove unused assets before uploading more.",
        )
    asset = await repo.create(
        name=body.name,
        asset_type=body.asset_type,
        storage_key=body.storage_key,
        sfx_storage_key=body.sfx_storage_key,
        description=body.description,
        tags=body.tags,
        default_duration_secs=body.default_duration_secs,
        owner_id=user_id,
        is_public=False,
    )
    await db.commit()
    return AssetOut.model_validate(asset)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_request)],
)
async def delete_asset(
    asset_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = AssetRepository(db)
    asset = await repo.get(asset_id)
    if asset is None or asset.owner_id != user_id:
        raise StreamClipError("Asset not found", user_message="Asset not found")
    await repo.delete(asset_id)
    await db.commit()
