"""
Webhook API tests — dependency-overridden, no real DB required.
"""
import hashlib
import hmac
import json
import uuid
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.db.models import ApiKey, WebhookConfig
from app.dependencies import get_db, get_redis, get_current_key
from app.api import webhooks


def _make_test_app(api_key=None):
    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    test_app = FastAPI(lifespan=noop_lifespan)
    test_app.include_router(webhooks.router)

    async def fake_db():
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    test_app.dependency_overrides[get_db] = fake_db
    test_app.dependency_overrides[get_redis] = lambda: AsyncMock()
    if api_key is not None:
        test_app.dependency_overrides[get_current_key] = lambda: api_key

    return test_app


def _fake_key():
    key = MagicMock(spec=ApiKey)
    key.id = uuid.uuid4()
    key.owner = "test"
    return key


@pytest.mark.asyncio
async def test_create_webhook_requires_auth():
    test_app = _make_test_app()
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.post("/v1/webhooks", json={"url": "https://example.com/hook"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_webhook_returns_secret():
    test_app = _make_test_app(api_key=_fake_key())

    fake_wh = MagicMock(spec=WebhookConfig)
    fake_wh.id = uuid.uuid4()
    fake_wh.url = "https://example.com/hook"
    fake_wh.trigger_actions = ["block"]
    fake_wh.trigger_risk_levels = ["critical", "high"]
    fake_wh.is_active = True

    async def patched_refresh(obj):
        obj.id = fake_wh.id
        obj.url = fake_wh.url
        obj.trigger_actions = fake_wh.trigger_actions
        obj.trigger_risk_levels = fake_wh.trigger_risk_levels
        obj.is_active = fake_wh.is_active

    async def fake_db():
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=patched_refresh)
        yield db

    test_app.dependency_overrides[get_db] = fake_db

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.post(
            "/v1/webhooks",
            headers={"Authorization": "Bearer test-key"},
            json={"url": "https://example.com/hook"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert "signing_secret" in data
    assert len(data["signing_secret"]) == 64  # 32 bytes hex


@pytest.mark.asyncio
async def test_delete_webhook_not_found():
    test_app = _make_test_app(api_key=_fake_key())

    from sqlalchemy.engine import CursorResult
    mock_result = MagicMock()
    mock_result.rowcount = 0

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()
        yield db

    test_app.dependency_overrides[get_db] = fake_db

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.delete(
            f"/v1/webhooks/{uuid.uuid4()}",
            headers={"Authorization": "Bearer test-key"},
        )
    assert resp.status_code == 404


def test_hmac_signature_correct():
    """Verify the signing logic produces a valid HMAC-SHA256 signature."""
    from app.core.webhook import _sign
    secret = "testsecret"
    payload = b'{"event":"detection.block"}'
    sig = _sign(secret, payload)
    assert sig.startswith("sha256=")
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    assert sig == expected
