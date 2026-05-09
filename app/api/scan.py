import asyncio
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_key, get_db
from app.db.models import ApiKey, ScanLog
from app.core.scanner import scan
from app.core.auth import hash_text
from app.core.webhook import fire_webhooks

router = APIRouter()


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
async def scan_text(
    body: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_current_key),
):
    config = body.config.model_dump(exclude_none=True)
    result = await scan(body.text, body.context, config)

    # Log scan metadata (never the raw text)
    log = ScanLog(
        id=uuid.uuid4(),
        scan_id=uuid.UUID(result.scan_id),
        api_key_id=api_key.id,
        context=body.context,
        text_hash=hash_text(body.text),
        safe=result.safe,
        risk_level=result.risk_level,
        action=result.action,
        pii_count=result.pii_count,
        injection_count=result.injection_count,
        secrets_count=result.secrets_count,
        toxicity_count=result.toxicity_count,
        total_detections=len(result.detections),
        scan_duration_ms=result.scan_duration_ms,
    )
    db.add(log)
    await db.commit()

    if not result.safe:
        background_tasks.add_task(fire_webhooks, api_key.id, result, body.context)

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


class BatchScanRequest(BaseModel):
    texts: list[ScanRequest] = Field(..., max_length=20)


@router.post("/v1/scan/batch", response_model=list[ScanResponse])
async def scan_batch(
    body: BatchScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_current_key),
):
    configs = [item.config.model_dump(exclude_none=True) for item in body.texts]
    results = await asyncio.gather(*(
        scan(item.text, item.context, cfg)
        for item, cfg in zip(body.texts, configs)
    ))

    for item, result in zip(body.texts, results):
        log = ScanLog(
            id=uuid.uuid4(),
            scan_id=uuid.UUID(result.scan_id),
            api_key_id=api_key.id,
            context=item.context,
            text_hash=hash_text(item.text),
            safe=result.safe,
            risk_level=result.risk_level,
            action=result.action,
            pii_count=result.pii_count,
            injection_count=result.injection_count,
            secrets_count=result.secrets_count,
            toxicity_count=result.toxicity_count,
            total_detections=len(result.detections),
            scan_duration_ms=result.scan_duration_ms,
        )
        db.add(log)
        if not result.safe:
            background_tasks.add_task(fire_webhooks, api_key.id, result, item.context)

    await db.commit()
    return [
        ScanResponse(
            scan_id=r.scan_id,
            safe=r.safe,
            risk_level=r.risk_level,
            action=r.action,
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
                for d in r.detections
            ],
            redacted_text=r.redacted_text,
            original_length=r.original_length,
            scan_duration_ms=r.scan_duration_ms,
        )
        for r in results
    ]
