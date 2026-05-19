from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.scanner import scan
from app.security import require_gateway_auth

router = APIRouter(dependencies=[Depends(require_gateway_auth)])


class ScanConfig(BaseModel):
    pii_entities: list[str] | None = None
    injection_threshold: float | None = None


class ScanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    context: str | None = Field(default=None, pattern="^(input|output)$")
    config: ScanConfig = ScanConfig()


class ScanResponse(BaseModel):
    scan_id: str
    safe: bool
    risk_level: str
    action: str
    detections: list[dict]
    redacted_text: str
    original_length: int
    scan_duration_ms: int


@router.post("/v1/scan", response_model=ScanResponse)
async def scan_text(body: ScanRequest):
    config = body.config.model_dump(exclude_none=True)
    result = await scan(body.text, body.context, config)
    return ScanResponse(
        scan_id=result.scan_id,
        safe=result.safe,
        risk_level=result.risk_level,
        action=result.action,
        detections=[
            {
                "detector": d.detector,
                "type": d.type,
                "text": d.text,
                "redacted": d.redacted,
                "start": d.start,
                "end": d.end,
                "confidence": d.confidence,
                "severity": d.severity,
            }
            for d in result.detections
        ],
        redacted_text=result.redacted_text,
        original_length=result.original_length,
        scan_duration_ms=result.scan_duration_ms,
    )
