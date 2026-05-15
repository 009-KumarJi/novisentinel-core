import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.scanner import warm_up_detectors

    warm_up_detectors()
    yield


app = FastAPI(
    title="NoviSentinel",
    description="Privacy proxy for AI coding agents — keeps your secrets off the LLM.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import proxy, scan  # noqa: E402

app.include_router(scan.router, tags=["Scan"])
app.include_router(proxy.router, tags=["Proxy"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
