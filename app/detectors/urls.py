"""URL/hostname safety detector."""

from __future__ import annotations

import unicodedata
from urllib.parse import urlparse

from app.detectors.base import DetectionResult

_BRANDS = {
    "google.com",
    "paypal.com",
    "amazon.com",
    "apple.com",
    "microsoft.com",
    "facebook.com",
    "github.com",
    "openai.com",
    "anthropic.com",
    "stripe.com",
    "novisentinel.com",
}
_BLOCKLIST: set[str] = set()


class UrlsDetector:
    detector_name = "urls"

    def __init__(self) -> None:
        from urlextract import URLExtract

        self._extractor = URLExtract()

    @property
    def ready(self) -> bool:
        return True

    def warm_up(self) -> None:
        return

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        urls = self._extractor.find_urls(text)
        out: list[DetectionResult] = []

        for url in urls:
            verdict = _classify_url(url)
            if verdict:
                start = text.find(url)
                out.append(
                    DetectionResult(
                        detector="urls",
                        type=f"urls.{verdict}",
                        text=url,
                        redacted="[REDACTED:URL]",
                        start=start if start >= 0 else 0,
                        end=(start + len(url)) if start >= 0 else len(url),
                        confidence=0.85,
                        severity="high",
                    )
                )

        return out


def _classify_url(url: str) -> str | None:
    p = urlparse(url if "://" in url else f"https://{url}")
    host = p.hostname or ""
    if not host:
        return None
    if host in _BLOCKLIST:
        return "blocklist"
    if _is_ip_only(host):
        return "ip_only"
    if _is_idn_homograph(host):
        return "idn_homograph"
    if _is_brand_typosquat(host):
        return "typosquat"
    return None


def _is_ip_only(host: str) -> bool:
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() for p in parts)


def _is_idn_homograph(host: str) -> bool:
    for ch in host:
        if not ch.isascii():
            cat = unicodedata.category(ch)
            if cat.startswith("L"):
                return True
    return False


def _is_brand_typosquat(host: str) -> bool:
    from difflib import SequenceMatcher

    for brand in _BRANDS:
        ratio = SequenceMatcher(None, host, brand).ratio()
        if 0.85 < ratio < 1.0:
            return True
    return False
