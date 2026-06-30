"""Job service unit tests with mocked DB."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.job_service import JobService
from core.config import get_settings
from core.errors import InvalidSourceError
from core.storage import LocalStorage


@pytest.mark.asyncio
async def test_create_job_rejects_empty_source():
    db = AsyncMock()
    cfg = get_settings(reload=True)
    storage = MagicMock(spec=LocalStorage)
    svc = JobService(db, cfg, storage)
    from backend.api.schemas import CreateJobRequest

    with pytest.raises(InvalidSourceError):
        await svc.create_job(CreateJobRequest(), owner_id=None)
