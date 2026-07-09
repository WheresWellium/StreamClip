"""HTTP tests for /api/settings/* and /api/templates/*."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.settings as settings_api
import backend.api.templates as templates_api
from backend.db.models import UserTier
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id

USER = "user-settings-1"


class FakeSession:
    def __init__(self, user) -> None:
        self.user = user
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


@pytest.fixture
async def authed_client(app, client, monkeypatch):
    user = SimpleNamespace(
        id=USER,
        tier=UserTier.PRO,
        webhook_url=None,
        webhook_secret=None,
        style_weights={},
    )
    session = FakeSession(user)

    async def fake_db():
        yield session

    class FakeUsers:
        def __init__(self, db) -> None:
            self.db = db

        async def get(self, user_id):
            return user if user_id == USER else None

        async def update_webhook(self, user_id, *, webhook_url, webhook_secret):
            user.webhook_url = webhook_url
            user.webhook_secret = webhook_secret

        async def update_style_weights(self, user_id, weights):
            user.style_weights = weights

    class FakeClips:
        def __init__(self, db) -> None:
            pass

        async def get(self, clip_id, *, with_overlays=True):
            return SimpleNamespace(
                id=clip_id,
                job_id="job-1",
                audio_score=0.5,
                spectral_score=0.5,
                flow_score=0.5,
                chat_score=0.0,
                llm_score=50.0,
            )

    class FakeJobs:
        def __init__(self, db) -> None:
            pass

        async def get_for_scope(
            self,
            job_id,
            *,
            owner_id,
            device_id=None,
            device_scoped=True,
        ):
            if job_id == "job-1" and owner_id == USER:
                return SimpleNamespace(id=job_id)
            return None

    class FakeFeedback:
        def __init__(self, db) -> None:
            pass

        async def upsert(self, clip_id, user_id, rating):
            return None

    monkeypatch.setattr(settings_api, "UserRepository", FakeUsers)
    monkeypatch.setattr(settings_api, "ClipRepository", FakeClips)
    monkeypatch.setattr(settings_api, "JobRepository", FakeJobs)
    monkeypatch.setattr(settings_api, "ClipFeedbackRepository", FakeFeedback)
    monkeypatch.setattr(
        settings_api,
        "apply_clip_style_feedback",
        AsyncMock(),
    )

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: USER
    app.dependency_overrides[get_current_user_id] = lambda: USER
    yield SimpleNamespace(client=client, session=session, user=user, app=app)
    for dep in (get_db, require_user_id, get_current_user_id):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_get_and_update_webhook(authed_client):
    get = await authed_client.client.get("/api/settings/webhook")
    assert get.status_code == 200
    assert get.json()["configured"] is False

    put = await authed_client.client.put(
        "/api/settings/webhook",
        json={"webhook_url": "https://hooks.example.com/sc", "webhook_secret": "sec"},
    )
    assert put.status_code == 200
    assert put.json()["configured"] is True
    assert authed_client.session.committed


@pytest.mark.asyncio
async def test_submit_clip_feedback(authed_client):
    resp = await authed_client.client.post(
        "/api/settings/clips/clip-1/feedback",
        json={"rating": 5},
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 5


@pytest.mark.asyncio
async def test_submit_clip_feedback_denied_when_job_out_of_scope(authed_client, monkeypatch):
    class DenyJobs:
        def __init__(self, db) -> None:
            pass

        async def get_for_scope(self, job_id, *, owner_id, device_id=None, device_scoped=True):
            return None

    monkeypatch.setattr(settings_api, "JobRepository", DenyJobs)
    resp = await authed_client.client.post(
        "/api/settings/clips/clip-1/feedback",
        json={"rating": 5},
    )
    assert resp.status_code == 404


@pytest.fixture
async def templates_client(app, client, monkeypatch):
    rows: dict[str, SimpleNamespace] = {}
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    class FakeTemplateRepo:
        def __init__(self, db) -> None:
            pass

        async def list_for_user(self, user_id):
            return list(rows.values())

        async def create(self, user_id, name, config_json):
            row = SimpleNamespace(id="tpl-1", name=name, config_json=config_json)
            rows["tpl-1"] = row
            return row

        async def delete(self, template_id, user_id):
            rows.pop(template_id, None)
            return True

    monkeypatch.setattr(templates_api, "JobTemplateRepository", FakeTemplateRepo)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: USER
    yield client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user_id, None)


@pytest.mark.asyncio
async def test_templates_crud(templates_client):
    listed = await templates_client.get("/api/templates")
    assert listed.status_code == 200
    assert listed.json() == []

    created = await templates_client.post(
        "/api/templates",
        json={"name": "Gaming defaults", "config_json": {"target_clips": 3}},
    )
    assert created.status_code == 201
    tpl_id = created.json()["id"]

    listed2 = await templates_client.get("/api/templates")
    assert len(listed2.json()) == 1

    deleted = await templates_client.delete(f"/api/templates/{tpl_id}")
    assert deleted.status_code == 204
