"""Custom HTTP detector runner.

Calls each configured detector endpoint in parallel with a 1-second timeout.
Failures are treated as clean (fail-open) so a misbehaving endpoint never
silently blocks all traffic.

Configure via CUSTOM_DETECTOR_ENDPOINTS env var (comma-separated URLs), or
CUSTOM_DETECTOR_SECRETS (comma-separated secrets matching each URL by index).

Endpoint contract:
  POST <url>
  Headers: X-Detector-Secret: <secret>  (optional)
  Body: {"text": "<input text>"}
  Response: {"label": "BLOCK"|"ALLOW", "score": 0.0-1.0, "explanation": "..."}
"""

from __future__ import annotations

import asyncio
import logging

from app.detectors.base import DetectionResult

logger = logging.getLogger(__name__)

_TIMEOUT_S = 1.0


async def scan_custom_detectors(text: str) -> list[DetectionResult]:
    """Call all configured custom detector endpoints in parallel."""
    from app.config import settings

    endpoints = [u.strip() for u in settings.custom_detector_endpoints.split(",") if u.strip()]
    secrets = [s.strip() for s in settings.custom_detector_secrets.split(",")]

    if not endpoints:
        return []

    tasks = [_call_one(text, url, secrets[i] if i < len(secrets) else "") for i, url in enumerate(endpoints)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: list[DetectionResult] = []
    for url, res in zip(endpoints, results, strict=False):
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

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.post(url, json={"text": text}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise exc

    score = float(data.get("score", 0.0))
    label = str(data.get("label", "ALLOW")).upper()
    name = url.split("/")[-1] or "custom"

    if label != "BLOCK" and score < 0.5:
        return None

    return DetectionResult(
        detector=f"custom:{name}",
        type=label,
        text=text[:200],
        redacted=f"[CUSTOM:{name.upper()}]",
        start=0,
        end=len(text),
        confidence=score,
        severity="high" if score >= 0.8 else "medium",
    )
