"""URL/hostname safety detector."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from urllib.parse import urlparse

from app.detectors.base import DetectionResult

# Names whose homograph variants are worth detecting. Curated rather than
# unbounded — SequenceMatcher across an open list is quadratic and noisy.
_BRANDS = (
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
)
_BLOCKLIST: set[str] = set()

# Cyrillic and Greek look-alikes commonly used in homograph attacks.
# Mixed-script labels in URL hosts are a strong phishing signal; pure
# foreign-script hosts (münchen.de, bücher.de) are not flagged.
_HOMOGRAPH_SCRIPTS = ("CYRILLIC", "GREEK", "ARMENIAN")


class UrlsDetector:
    name = "urls"

    def __init__(self) -> None:
        self._extractor = None

    @property
    def ready(self) -> bool:
        return True

    def warm_up(self) -> None:
        # Lazy — actual loader runs on first scan.
        return

    def _get_extractor(self):
        if self._extractor is None:
            from urlextract import URLExtract

            self._extractor = URLExtract()
        return self._extractor

    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        try:
            urls = self._get_extractor().find_urls(text)
        except Exception:
            return []
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
    host = (p.hostname or "").lower()
    if not host:
        return None
    if host in _BLOCKLIST:
        return "blocklist"
    if _is_ip_only(host):
        return "ip_only"
    if _is_mixed_script_homograph(host):
        return "idn_homograph"
    if _is_brand_typosquat(host):
        return "typosquat"
    return None


def _is_ip_only(host: str) -> bool:
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return True
    # IPv6 literal in brackets is already stripped by urlparse.hostname,
    # so a colon-bearing hostname is an IPv6 address.
    return ":" in host


def _is_mixed_script_homograph(host: str) -> bool:
    """Flag hosts that mix Latin with Cyrillic/Greek/Armenian within one label.

    Pure non-Latin hosts (münchen.de, 例え.jp) are not flagged. Only mixed-script
    labels — the actual phishing pattern — are.
    """
    for label in host.split("."):
        scripts: set[str] = set()
        for ch in label:
            if ch.isascii() and ch.isalpha():
                scripts.add("LATIN")
                continue
            if not ch.isalpha():
                continue
            try:
                name = unicodedata.name(ch, "")
            except ValueError:
                continue
            for script in _HOMOGRAPH_SCRIPTS:
                if name.startswith(script):
                    scripts.add(script)
                    break
        if "LATIN" in scripts and len(scripts) > 1:
            return True
    return False


# Bounded Levenshtein with early exit beats SequenceMatcher for short strings
# and avoids the O(n*m) cost of running ratio() against every brand on every
# URL scan.
def _is_brand_typosquat(host: str) -> bool:
    bare = re.sub(r"^www\.", "", host)
    for brand in _BRANDS:
        if bare == brand:
            return False
        # Cheap filters: length must be close.
        if abs(len(bare) - len(brand)) > 2:
            continue
        if _bounded_levenshtein(bare, brand, max_dist=2) <= 2:
            return True
    return False


@lru_cache(maxsize=4096)
def _bounded_levenshtein(a: str, b: str, max_dist: int) -> int:
    """Return edit distance or max_dist+1 if it exceeds the bound."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > max_dist:
        return max_dist + 1
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * lb
        row_min = cur[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            row_min = min(row_min, cur[j])
        if row_min > max_dist:
            return max_dist + 1
        prev = cur
    return prev[lb]
