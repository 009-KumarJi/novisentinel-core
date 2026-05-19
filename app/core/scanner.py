import asyncio
import time
import uuid
from dataclasses import dataclass

from app.detectors.base import DetectionResult
from app.detectors.code_injection import CodeInjectionDetector
from app.detectors.custom import scan_custom_detectors
from app.detectors.injection import InjectionDetector
from app.detectors.pii import CRITICAL_ENTITIES, PIIDetector
from app.detectors.secrets import SecretsDetector
from app.detectors.toxicity import ToxicityDetector
from app.detectors.urls import UrlsDetector

_pii = PIIDetector()
_injection = InjectionDetector()
_secrets = SecretsDetector()
_toxicity = ToxicityDetector()
_code_injection = CodeInjectionDetector()
_urls = UrlsDetector()


@dataclass
class ScanResult:
    scan_id: str
    safe: bool
    risk_level: str  # none / low / medium / high / critical
    action: str  # allow / warn / redact / block
    detections: list[DetectionResult]
    redacted_text: str
    original_length: int
    scan_duration_ms: int
    pii_count: int = 0
    injection_count: int = 0
    secrets_count: int = 0
    toxicity_count: int = 0


def warm_up_detectors() -> None:
    _pii.warm_up()
    _injection.warm_up()
    _toxicity.warm_up()


async def scan(text: str, context: str | None, config: dict) -> ScanResult:
    start = time.monotonic()
    scan_id = str(uuid.uuid4())

    # Sync detectors (regex / Presidio) run on the calling thread.
    pii_results = _pii.scan(text, config)
    secrets_results = _secrets.scan(text, config)
    code_inj_results = _code_injection.scan(text, config)
    url_results = _urls.scan(text, config)

    # Async detectors (ML + remote HTTP) run concurrently.
    injection_results, toxicity_results, custom_results = await asyncio.gather(
        _injection.scan_async(text, config),
        _toxicity.scan_async(text, config),
        scan_custom_detectors(text),
    )

    all_detections = (
        pii_results
        + secrets_results
        + code_inj_results
        + url_results
        + injection_results
        + toxicity_results
        + custom_results
    )
    pii_count = len(pii_results)
    secrets_count = len(secrets_results)
    injection_count = len(injection_results)
    toxicity_count = len(toxicity_results)

    risk_level = _determine_risk(all_detections)
    action = _determine_action(all_detections, risk_level)
    redacted = _build_redacted_text(text, all_detections) if action in ("redact", "block") else text

    duration_ms = int((time.monotonic() - start) * 1000)

    return ScanResult(
        scan_id=scan_id,
        safe=len(all_detections) == 0,
        risk_level=risk_level,
        action=action,
        detections=all_detections,
        redacted_text=redacted,
        original_length=len(text),
        scan_duration_ms=duration_ms,
        pii_count=pii_count,
        injection_count=injection_count,
        secrets_count=secrets_count,
        toxicity_count=toxicity_count,
    )


def _determine_risk(detections: list[DetectionResult]) -> str:
    if not detections:
        return "none"

    severities = {d.severity for d in detections}

    if "critical" in severities:
        return "critical"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"

    return "low"


def _determine_action(detections: list[DetectionResult], risk_level: str) -> str:
    if not detections:
        return "allow"

    # Injection, secrets, code injection, or critical toxicity → always block
    if any(d.detector == "injection" for d in detections):
        return "block"
    if any(d.detector == "secrets" for d in detections):
        return "block"
    if any(d.detector == "code_injection" for d in detections):
        return "block"
    if any(d.detector == "toxicity" and d.severity == "critical" for d in detections):
        return "block"

    # Medium toxicity → warn
    if any(d.detector == "toxicity" for d in detections):
        return "warn"

    # Critical PII (SSN, credit card) → block
    if any(d.type in CRITICAL_ENTITIES for d in detections):
        return "block"

    # High/medium PII → redact
    if risk_level in ("high", "medium"):
        return "redact"

    # Low confidence → warn only
    return "warn"


def _build_redacted_text(text: str, detections: list[DetectionResult]) -> str:
    full_replace = next(
        (d for d in detections if d.detector in ("injection", "toxicity")),
        None,
    )
    if full_replace is not None:
        return full_replace.redacted

    redactable = [d for d in detections if d.detector in ("pii", "secrets", "urls", "custom", "code_injection")]

    # Longer-span matches win on overlap — keeps a full connection string from
    # being shadowed by a narrower password/host match contained within it.
    selected: list[DetectionResult] = []
    covered: set[int] = set()
    for d in sorted(redactable, key=lambda d: (-(d.end - d.start), d.start)):
        span = set(range(d.start, d.end))
        if span & covered:
            continue
        selected.append(d)
        covered |= span

    result = text
    for d in sorted(selected, key=lambda d: -d.start):
        result = result[: d.start] + d.redacted + result[d.end :]

    return result
