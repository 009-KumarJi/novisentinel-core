from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.dependencies import require_master_key, get_db
from app.db.models import ScanLog

router = APIRouter()


@router.get("/v1/logs", dependencies=[Depends(require_master_key)])
async def get_logs(
    db: AsyncSession = Depends(get_db),
    risk_level: str | None = Query(default=None),
    action: str | None = Query(default=None),
    context: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO datetime"),
    limit: int = Query(default=100, le=1000),
):
    stmt = select(ScanLog).order_by(ScanLog.created_at.desc()).limit(limit)

    if risk_level:
        stmt = stmt.where(ScanLog.risk_level == risk_level)
    if action:
        stmt = stmt.where(ScanLog.action == action)
    if context:
        stmt = stmt.where(ScanLog.context == context)
    if since:
        dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
        stmt = stmt.where(ScanLog.created_at >= dt)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "scan_id": str(r.scan_id),
            "context": r.context,
            "safe": r.safe,
            "risk_level": r.risk_level,
            "action": r.action,
            "pii_count": r.pii_count,
            "injection_count": r.injection_count,
            "secrets_count": r.secrets_count,
            "toxicity_count": r.toxicity_count,
            "total_detections": r.total_detections,
            "scan_duration_ms": r.scan_duration_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/v1/stats", dependencies=[Depends(require_master_key)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    totals = await db.execute(
        select(
            func.count(ScanLog.scan_id).label("total"),
            func.sum(func.cast(~ScanLog.safe, Integer)).label("flagged"),
            func.sum(func.cast(ScanLog.action == "block", Integer)).label("blocked"),
            func.sum(func.cast(ScanLog.action == "redact", Integer)).label("redacted"),
            func.avg(ScanLog.scan_duration_ms).label("avg_ms"),
        )
    )
    row = totals.one()
    total = row.total or 0
    flagged = row.flagged or 0

    risk_rows = await db.execute(
        select(ScanLog.risk_level, func.count(ScanLog.scan_id))
        .group_by(ScanLog.risk_level)
    )
    by_risk = {level: count for level, count in risk_rows.all()}

    return {
        "total_scans": total,
        "flagged_scans": flagged,
        "flag_rate": round(flagged / total, 4) if total else 0.0,
        "blocked": row.blocked or 0,
        "redacted": row.redacted or 0,
        "avg_scan_ms": round(float(row.avg_ms or 0), 1),
        "by_risk_level": by_risk,
    }
