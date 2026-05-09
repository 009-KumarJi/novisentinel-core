from pydantic import BaseModel


class Detection(BaseModel):
    detector: str
    type: str
    text: str
    redacted: str
    start: int
    end: int
    confidence: float
    severity: str


class ScanResult(BaseModel):
    scan_id: str
    safe: bool
    risk_level: str
    action: str
    detections: list[Detection]
    redacted_text: str
    original_length: int
    scan_duration_ms: int
