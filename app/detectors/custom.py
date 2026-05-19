"""Custom HTTP detector runner.

Calls each configured detector endpoint in parallel with a 1-second timeout.
Failures are treated as clean (fail-open) so a misbehaving endpoint never
silently blocks all traffic.

Configure via CUSTOM_DETECTOR_ENDPOINTS env var (comma-separated URLs), or
CUSTOM_DETECTOR_SECRETS (comma-separated secrets matching each URL by index).

Security:
  - URLs must be https://.
  - Hosts must resolve to public (non-RFC1918, non-loopback) addresses
    unless CUSTOM_DETECTOR_ALLOW_INTERNAL=true (explicit operator opt-in).
  - Redirects are not followed (no 302→IMDS bypass).

Endpoint contract:
  POST <url>
  Headers: X-Detector-Secret: <secret>  (optional)
  Body: {"text": "<input text>"}
  Response: {"label": "BLOCK"|"ALLOW", "score": 0.0-1.0, "explanation": "..."}
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from functools import lru_cache
from urllib.parse import urlparse

from app.detectors.base import DetectionResult

logger = logging.getLogger(__name__)

_TIMEOUT_S = 1.0


@lru_cache(maxsize=256)
def _resolved_addresses(host: str) -> tuple[str, ...]:
    """getaddrinfo with caching. Cache is local to this process."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return ()
    return tuple({i[4][0] for i in infos})


def _is_safe_host(host: str, allow_internal: bool) -> bool:
    if not host:
        return False
    if allow_internal:
        return True
    addrs = _resolved_addresses(host)
    if not addrs:
        return False
    for addr in addrs:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        # Block loopback, link-local (incl. IMDS 169.254/16), private,
        # multicast, reserved, unspecified.
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_private
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def _validate_endpoint(url: str, allow_internal: bool) -> str | None:
    p = urlparse(url)
    if p.scheme != "https":
        return f"scheme must be https (got {p.scheme!r})"
    if not p.hostname:
        return "missing hostname"
    if not _is_safe_host(p.hostname, allow_internal):
        return f"host {p.hostname!r} resolves to a non-public address"
    return None


async def scan_custom_detectors(text: str) -> list[DetectionResult]:
    """Call all configured custom detector endpoints in parallel."""
    from app.config import settings

    endpoints = [u.strip() for u in settings.custom_detector_endpoints.split(",") if u.strip()]
    secrets = [s.strip() for s in settings.custom_detector_secrets.split(",")]

    if not endpoints:
        return []

    safe_endpoints: list[tuple[int, str]] = []
    for i, url in enumerate(endpoints):
        err = _validate_endpoint(url, settings.custom_detector_allow_internal)
        if err:
            logger.warning("custom_detector.rejected url=%s reason=%s", url, err)
            continue
        safe_endpoints.append((i, url))

    if not safe_endpoints:
        return []

    tasks = [_call_one(text, url, secrets[i] if i < len(secrets) else "") for i, url in safe_endpoints]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: list[DetectionResult] = []
    for (_, url), res in zip(safe_endpoints, results, strict=False):
        if isinstance(res, Exception):
            logger.warning("custom_detector.error url=%s error=%s", url, res)
            continue
        if res is not None:
            out.append(res)
    return out


async def _call_one(text: str, url: str, secret: str) -> DetectionResult | None:
    import httpx

    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Detector-Secret"] = secret

    async with httpx.AsyncClient(timeout=_TIMEOUT_S, follow_redirects=False) as client:
        resp = await client.post(url, json={"text": text}, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    score = float(data.get("score", 0.0))
    label = str(data.get("label", "ALLOW")).upper()
    name = url.split("/")[-1] or "custom"

    if label != "BLOCK" and score < 0.5:
        return None

    return DetectionResult(
        detector="custom",
        type=label,
        text=text[:200],
        redacted=f"[CUSTOM:{name.upper()}]",
        start=0,
        end=len(text),
        confidence=score,
        severity="high" if score >= 0.8 else "medium",
    )
