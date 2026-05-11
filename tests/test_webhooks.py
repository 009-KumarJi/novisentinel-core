"""
Webhook API tests — dependency-overridden, no real DB required.
"""

import hashlib
import hmac
import socket
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import webhooks
from app.core.scanner import ScanResult
from app.db.models import ApiKey, WebhookConfig
from app.dependencies import get_current_key, get_db, get_redis


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
    assert resp.status_code in (401, 403)


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
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert sig == expected


# ---------------------------------------------------------------------------
# validate_webhook_url unit tests
# ---------------------------------------------------------------------------


def test_validate_webhook_url_rejects_http_scheme():
    from app.core.webhook import validate_webhook_url

    with pytest.raises(ValueError, match="must use one of"):
        validate_webhook_url("http://example.com/hook")


def test_validate_webhook_url_rejects_missing_hostname():
    from app.core.webhook import validate_webhook_url

    with pytest.raises(ValueError, match="missing a hostname"):
        validate_webhook_url("https:///no-host")


def test_validate_webhook_url_accepts_public_https():
    from app.core.webhook import validate_webhook_url

    with patch(
        "app.core.webhook.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    ):
        validate_webhook_url("https://example.com/hook")  # must not raise


def test_validate_webhook_url_rejects_private_ip():
    from app.core.webhook import validate_webhook_url

    with (
        patch(
            "app.core.webhook.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))],
        ),
        pytest.raises(ValueError, match="blocked address"),
    ):
        validate_webhook_url("https://internal.corp/hook")


def test_validate_webhook_url_rejects_loopback():
    from app.core.webhook import validate_webhook_url

    with (
        patch(
            "app.core.webhook.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))],
        ),
        pytest.raises(ValueError, match="blocked address"),
    ):
        validate_webhook_url("https://localhost/hook")


def test_validate_webhook_url_rejects_unresolvable_host():
    from app.core.webhook import validate_webhook_url

    with (
        patch("app.core.webhook.socket.getaddrinfo", side_effect=socket.gaierror("no such host")),
        pytest.raises(ValueError, match="does not resolve"),
    ):
        validate_webhook_url("https://totally.nonexistent.invalid/hook")


# ---------------------------------------------------------------------------
# _fire() unit tests
# ---------------------------------------------------------------------------


def _make_scan_result(**kwargs):
    defaults = dict(
        scan_id=str(uuid.uuid4()),
        safe=False,
        risk_level="critical",
        action="block",
        detections=[],
        redacted_text="bad",
        original_length=3,
        scan_duration_ms=5,
        injection_count=1,
    )
    defaults.update(kwargs)
    return ScanResult(**defaults)


@pytest.mark.asyncio
async def test_fire_returns_early_when_no_webhooks():
    from app.core.webhook import _fire

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(return_value=empty_result)

    await _fire(db, uuid.uuid4(), _make_scan_result(), "input")
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_fire_skips_webhook_with_mismatched_action():
    from app.core.webhook import _fire

    wh = MagicMock(spec=WebhookConfig)
    wh.trigger_actions = ["warn"]  # result.action is "block" — mismatch
    wh.trigger_risk_levels = ["critical"]
    wh.secret = "s3cr3t"
    wh.url = "https://example.com/hook"

    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [wh]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=rows_result)

    with patch("app.core.webhook.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        await _fire(db, uuid.uuid4(), _make_scan_result(action="block"), "input")
        mock_http.post.assert_not_called()


@pytest.mark.asyncio
async def test_fire_posts_to_matching_webhook():
    from app.core.webhook import _fire

    wh = MagicMock(spec=WebhookConfig)
    wh.trigger_actions = ["block"]
    wh.trigger_risk_levels = ["critical"]
    wh.secret = "s3cr3t"
    wh.url = "https://example.com/hook"

    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [wh]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=rows_result)

    with patch("app.core.webhook.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        await _fire(db, uuid.uuid4(), _make_scan_result(), "input")
        mock_http.post.assert_called_once()
        call_kwargs = mock_http.post.call_args
        assert call_kwargs[0][0] == "https://example.com/hook"
        headers = call_kwargs[1]["headers"]
        assert headers["X-NoviSentinel-Signature"].startswith("sha256=")
