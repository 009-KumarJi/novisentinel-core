import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.webhook import validate_webhook_url
from app.db.models import ApiKey, WebhookConfig
from app.dependencies import get_current_key, get_db

router = APIRouter()


class WebhookCreate(BaseModel):
    url: HttpUrl
    trigger_actions: list[str] = Field(default=["block"])
    trigger_risk_levels: list[str] = Field(default=["critical", "high"])


class WebhookResponse(BaseModel):
    id: str
    url: str
    trigger_actions: list[str]
    trigger_risk_levels: list[str]
    is_active: bool
    signing_secret: str | None = None


@router.post("/v1/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_current_key),
):
    try:
        validate_webhook_url(str(body.url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    signing_secret = secrets.token_hex(32)
    wh = WebhookConfig(
        id=uuid.uuid4(),
        api_key_id=api_key.id,
        url=str(body.url),
        secret=signing_secret,
        trigger_actions=body.trigger_actions,
        trigger_risk_levels=body.trigger_risk_levels,
        is_active=True,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return WebhookResponse(
        id=str(wh.id),
        url=wh.url,
        trigger_actions=wh.trigger_actions,
        trigger_risk_levels=wh.trigger_risk_levels,
        is_active=wh.is_active,
        signing_secret=signing_secret,  # only returned on creation
    )


@router.get("/v1/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_current_key),
):
    rows = await db.execute(select(WebhookConfig).where(WebhookConfig.api_key_id == api_key.id))
    return [
        WebhookResponse(
            id=str(wh.id),
            url=wh.url,
            trigger_actions=wh.trigger_actions,
            trigger_risk_levels=wh.trigger_risk_levels,
            is_active=wh.is_active,
        )
        for wh in rows.scalars().all()
    ]


@router.delete("/v1/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_current_key),
):
    result = await db.execute(
        delete(WebhookConfig).where(
            WebhookConfig.id == webhook_id,
            WebhookConfig.api_key_id == api_key.id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.commit()
