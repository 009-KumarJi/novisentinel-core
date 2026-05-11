"""
Logs and stats API tests — real require_master_key dependency runs for coverage.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import logs
from app.db.models import ScanLog
from app.dependencies import get_db, get_redis

_MASTER = "dev-master-key"


def _make_test_app(db_factory):
    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    test_app = FastAPI(lifespan=noop_lifespan)
    test_app.include_router(logs.router)
    test_app.dependency_overrides[get_redis] = lambda: AsyncMock()
    test_app.dependency_overrides[get_db] = db_factory
    return test_app


def _fake_scan_log():
    row = MagicMock(spec=ScanLog)
    row.scan_id = uuid.uuid4()
    row.context = "input"
    row.safe = True
    row.risk_level = "none"
    row.action = "allow"
    row.pii_count = 0
    row.injection_count = 0
    row.secrets_count = 0
    row.toxicity_count = 0
    row.total_detections = 0
    row.scan_duration_ms = 5
    row.created_at = datetime.now(UTC)
    return row


@pytest.mark.asyncio
async def test_get_logs_returns_empty():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    async with AsyncClient(transport=ASGITransport(app=_make_test_app(fake_db)), base_url="http://test") as c:
        resp = await c.get("/v1/logs", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_logs_with_rows():
    fake_log = _fake_scan_log()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_log]

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    async with AsyncClient(transport=ASGITransport(app=_make_test_app(fake_db)), base_url="http://test") as c:
        resp = await c.get("/v1/logs", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action"] == "allow"
    assert data[0]["safe"] is True


@pytest.mark.asyncio
async def test_get_logs_with_all_filters():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    async with AsyncClient(transport=ASGITransport(app=_make_test_app(fake_db)), base_url="http://test") as c:
        resp = await c.get(
            "/v1/logs",
            headers={"X-Master-Key": _MASTER},
            params={
                "risk_level": "high",
                "action": "block",
                "context": "input",
                "since": "2024-01-01T00:00:00",
                "limit": 10,
            },
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_stats_returns_summary():
    totals_row = MagicMock()
    totals_row.total = 100
    totals_row.flagged = 20
    totals_row.blocked = 10
    totals_row.redacted = 5
    totals_row.avg_ms = 12.5

    totals_result = MagicMock()
    totals_result.one.return_value = totals_row

    risk_result = MagicMock()
    risk_result.all.return_value = [("none", 80), ("high", 15), ("critical", 5)]

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[totals_result, risk_result])
        yield db

    async with AsyncClient(transport=ASGITransport(app=_make_test_app(fake_db)), base_url="http://test") as c:
        resp = await c.get("/v1/stats", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_scans"] == 100
    assert data["flagged_scans"] == 20
    assert data["flag_rate"] == 0.2
    assert data["blocked"] == 10
    assert data["avg_scan_ms"] == 12.5
    assert data["by_risk_level"]["critical"] == 5


@pytest.mark.asyncio
async def test_get_stats_zero_total():
    totals_row = MagicMock()
    totals_row.total = 0
    totals_row.flagged = None
    totals_row.blocked = None
    totals_row.redacted = None
    totals_row.avg_ms = None

    totals_result = MagicMock()
    totals_result.one.return_value = totals_row

    risk_result = MagicMock()
    risk_result.all.return_value = []

    async def fake_db():
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[totals_result, risk_result])
        yield db

    async with AsyncClient(transport=ASGITransport(app=_make_test_app(fake_db)), base_url="http://test") as c:
        resp = await c.get("/v1/stats", headers={"X-Master-Key": _MASTER})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_scans"] == 0
    assert data["flag_rate"] == 0.0
    assert data["by_risk_level"] == {}
