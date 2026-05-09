import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WebhookConfig
from app.db.session import AsyncSessionLocal
from app.core.scanner import ScanResult

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(5.0)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_webhook_url(url: str) -> None:
    # DNS rebinding is still possible (resolve-at-validation vs resolve-at-delivery).
    # A complete fix would pin the resolved IP. Documented limitation — out of scope.
    from app.config import settings
    parsed = urlparse(url)
    allowed_schemes = {"https"} if not settings.allow_insecure_webhooks else {"http", "https"}
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"Webhook URL must use one of: {', '.join(sorted(allowed_schemes))}")
    if not parsed.hostname:
        raise ValueError("Webhook URL is missing a hostname")
    if settings.allow_insecure_webhooks:
        return
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Webhook URL hostname does not resolve: {exc}")
    for _family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if any(ip in net for net in _BLOCKED_NETWORKS):
            raise ValueError(f"Webhook URL resolves to blocked address: {ip}")


def _sign(secret: str, payload: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def fire_webhooks(
    api_key_id,
    result: ScanResult,
    context: str | None,
) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await _fire(db, api_key_id, result, context)
    except Exception as exc:
        logger.warning("Webhook dispatch error: %s", exc)


async def _fire(
    db: AsyncSession,
    api_key_id,
    result: ScanResult,
    context: str | None,
) -> None:
    rows = await db.execute(
        select(WebhookConfig).where(
            WebhookConfig.api_key_id == api_key_id,
            WebhookConfig.is_active.is_(True),
        )
    )
    webhooks = rows.scalars().all()
    if not webhooks:
        return

    payload_dict = {
        "event": f"detection.{result.action}",
        "scan_id": result.scan_id,
        "risk_level": result.risk_level,
        "action": result.action,
        "context": context,
        "pii_count": result.pii_count,
        "injection_count": result.injection_count,
        "secrets_count": result.secrets_count,
        "toxicity_count": result.toxicity_count,
        "detections": [
            {
                "detector": d.detector,
                "type": d.type,
                "severity": d.severity,
                "confidence": d.confidence,
            }
            for d in result.detections
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode()

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
        for wh in webhooks:
            if result.action not in (wh.trigger_actions or []):
                continue
            if result.risk_level not in (wh.trigger_risk_levels or []):
                continue
            sig = _sign(wh.secret, payload_bytes)
            try:
                await client.post(
                    wh.url,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-NoviSentinel-Signature": sig,
                    },
                )
            except Exception as exc:
                logger.warning("Webhook delivery failed for %s: %s", wh.url, exc)
