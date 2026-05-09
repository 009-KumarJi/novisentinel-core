import hashlib
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import keys, logs, scan, webhooks
from app.config import settings
from app.core.auth import _master_key_uuid
from app.core.scanner import warm_up_detectors
from app.db.models import ApiKey, Base
from app.db.session import AsyncSessionLocal, engine

redis_client: aioredis.Redis = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client

    if settings.environment != "dev" and settings.master_api_key == "dev-master-key":
        raise RuntimeError(
            "MASTER_API_KEY must be set when ENVIRONMENT != dev. "
            "The default 'dev-master-key' is publicly documented."
        )

    async with engine.begin() as conn:
        # Dev-only schema bootstrap. Production deployments need a real migration tool.
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        master_id = _master_key_uuid(settings.master_api_key)
        existing = await session.execute(select(ApiKey).where(ApiKey.id == master_id))
        if existing.scalar_one_or_none() is None:
            session.add(
                ApiKey(
                    id=master_id,
                    key_prefix="master__",
                    key_hash=hashlib.sha256(settings.master_api_key.encode()).hexdigest(),
                    name="__master__",
                    owner="__system__",
                    is_active=True,
                )
            )
            await session.commit()

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    # Pre-load Presidio + injection ML model so first request isn't slow
    warm_up_detectors()

    yield

    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="NoviSentinel",
    description="AI Safety & PII Firewall — scan LLM inputs and outputs for PII and prompt injection",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router, tags=["Scan"])
app.include_router(keys.router, tags=["API Keys"])
app.include_router(logs.router, tags=["Logs & Stats"])
app.include_router(webhooks.router, tags=["Webhooks"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
