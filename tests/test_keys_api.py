"""
API key management tests — real require_master_key dependency runs for coverage.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import keys
from app.config import settings
from app.db.models import ApiKey
from app.dependencies import get_db, get_redis


def _make_test_app(db_factory=None):
    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    test_app = FastAPI(lifespan=noop_lifespan)
    test_app.include_router(keys.router)
    test_app.dependency_overrides[get_redis] = lambda: AsyncMock()

    if db_factory is not None:
        test_app.dependency_overrides[get_db] = db_factory

    return test_app


def _plain_db():
    async def fake_db():
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    return fake_db


_MASTER = settings.master_api_key


@pytest.mark.asyncio
async def test_create_key_returns_key_and_prefix():
    test_app = _make_test_app(_plain_db())

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.post(
            "/v1/keys",
            headers={"X-Master-Key": _MASTER},
            json={"name": "my key", "owner": "alice"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"].startswith("nvs_")
    assert len(data["prefix"]) == 8
    assert "key_id" in data
    assert "Store this key securely" in data["message"]


@pytest.mark.asyncio
async def test_list_keys_returns_all():
    fake_key = MagicMock(spec=ApiKey)
    fake_key.id = uuid.uuid4()
    fake_key.key_prefix = "nvs_abcd"
    fake_key.name = "my key"
    fake_key.owner = "alice"
    fake_key.is_active = True
    fake_key.created_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_key]

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    test_app = _make_test_app(fake_db)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/v1/keys", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["owner"] == "alice"
    assert data[0]["is_active"] is True


@pytest.mark.asyncio
async def test_revoke_key_success():
    fake_key = MagicMock(spec=ApiKey)
    fake_key.id = uuid.uuid4()
    fake_key.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_key

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()
        yield db

    test_app = _make_test_app(fake_db)
    key_id = uuid.uuid4()

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.delete(f"/v1/keys/{key_id}", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Key revoked"
    assert fake_key.is_active is False


@pytest.mark.asyncio
async def test_revoke_key_not_found():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    test_app = _make_test_app(fake_db)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.delete(f"/v1/keys/{uuid.uuid4()}", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_keys_endpoint_rejects_wrong_master_key():
    test_app = _make_test_app(_plain_db())

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/v1/keys", headers={"X-Master-Key": "wrong-key"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Master API key required"
