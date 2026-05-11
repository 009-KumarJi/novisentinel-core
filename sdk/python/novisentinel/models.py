from __future__ import annotations

from pydantic import BaseModel


class Detection(BaseModel):
    """A single finding produced by one detector."""

    detector: str
    type: str
    text: str
    redacted: str
    start: int
    end: int
    confidence: float
    severity: str


class ScanResult(BaseModel):
    """The full response from a scan call."""

    scan_id: str
    safe: bool
    risk_level: str
    action: str
    detections: list[Detection]
    redacted_text: str
    original_length: int
    scan_duration_ms: int

    # --- convenience properties ---

    @property
    def has_pii(self) -> bool:
        """True if any detection came from the PII detector."""
        return any(d.detector == "pii" for d in self.detections)

    @property
    def has_injection(self) -> bool:
        """True if any detection came from the prompt-injection detector."""
        return any(d.detector == "injection" for d in self.detections)

    @property
    def has_secrets(self) -> bool:
        """True if any detection came from the secrets detector."""
        return any(d.detector == "secrets" for d in self.detections)

    @property
    def has_toxicity(self) -> bool:
        """True if any detection came from the toxicity detector."""
        return any(d.detector == "toxicity" for d in self.detections)

    def detections_by_type(self, type: str) -> list[Detection]:
        """Return all detections whose ``type`` field matches *type*."""
        return [d for d in self.detections if d.type == type]
