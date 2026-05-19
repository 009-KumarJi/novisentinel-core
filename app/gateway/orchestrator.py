from __future__ import annotations

import logging
import time

from app.gateway.router import get_provider
from app.gateway.schemas import ChatCompletionRequest, ChatCompletionResponse

logger = logging.getLogger(__name__)


def _resolve_upstream_key(provider_name: str) -> str:
    from app.config import settings

    key_map: dict[str, str] = {
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "google": settings.google_api_key,
    }
    return key_map.get(provider_name, "")


async def call_provider_only(
    request: ChatCompletionRequest,
    upstream_api_key: str = "",
) -> ChatCompletionResponse:
    """Forward request to the upstream provider.

    The proxy layer (`app.api.proxy`) is responsible for scanning, redaction,
    and restoration; this entrypoint deliberately bypasses the scanner to
    avoid double-blocking the placeholders the proxy already inserted.
    """
    from app.gateway.errors import GatewayError, normalize_error
    from app.gateway.reliability import resilient_call

    provider, provider_name = get_provider(request.model)
    key = upstream_api_key or _resolve_upstream_key(provider_name)

    t0 = time.monotonic()
    try:
        response = await resilient_call(
            lambda: provider.complete(request, key),
            provider_name,
        )
    except GatewayError:
        raise
    except Exception as exc:
        raise normalize_error(exc, provider_name) from exc

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    logger.info("proxy.completion provider=%s model=%s latency_ms=%d", provider_name, request.model, elapsed_ms)
    return response
