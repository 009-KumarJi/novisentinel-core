import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.security import BodySizeLimitMiddleware

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.scanner import warm_up_detectors
    from app.gateway.providers.http import shutdown as shutdown_http

    warm_up_detectors()
    try:
        yield
    finally:
        await shutdown_http()


app = FastAPI(
    title="NoviSentinel",
    description="Privacy proxy for AI coding agents — keeps your secrets off the LLM.",
    version="1.0.0",
    lifespan=lifespan,
)

# Reject huge bodies before they reach the JSON parser.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)

# CORS — defaults to localhost-only. Wildcard requires explicit operator opt-in.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-api-key", "anthropic-version"],
    allow_credentials=False,
)

from app.api import proxy, scan  # noqa: E402

app.include_router(scan.router, tags=["Scan"])
app.include_router(proxy.router, tags=["Proxy"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
