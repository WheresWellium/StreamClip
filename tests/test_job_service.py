"""Job service unit tests with mocked DB."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.api.schemas import CreateJobRequest
from backend.middleware.scope import RequestScope
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
    scope = RequestScope(user_id=None, device_id="test-device")

    with pytest.raises(InvalidSourceError):
        await svc.create_job(CreateJobRequest(), scope)
    # Invalid requests must not touch the DB (no device upsert before validation)
    db.flush.assert_not_awaited()
