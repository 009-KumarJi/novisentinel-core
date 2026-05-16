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


def _extract_message_text(request: ChatCompletionRequest) -> str:
    parts: list[str] = []
    for msg in request.messages:
        if isinstance(msg.content, str):
            parts.append(msg.content)
        elif isinstance(msg.content, list):
            for part in msg.content:
                if part.text:
                    parts.append(part.text)
    return " ".join(parts)


def _extract_response_text(response: ChatCompletionResponse) -> str:
    for choice in response.choices:
        if choice.message and isinstance(choice.message.content, str):
            return choice.message.content
    return ""


async def handle_completion(
    request: ChatCompletionRequest,
    upstream_api_key: str = "",
) -> ChatCompletionResponse:
    from app.core.scanner import scan
    from app.gateway.errors import GatewayError, normalize_error
    from app.gateway.reliability import resilient_call

    provider, provider_name = get_provider(request.model)
    key = upstream_api_key or _resolve_upstream_key(provider_name)

    input_text = _extract_message_text(request)
    if input_text:
        input_scan = await scan(input_text, "input", {})
        if input_scan.action == "block":
            raise GatewayError(
                "invalid_request",
                f"Input blocked by NoviSentinel: {input_scan.risk_level} risk detected",
                400,
                provider_name,
            )

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
    logger.info("gateway.completion provider=%s model=%s latency_ms=%d", provider_name, request.model, elapsed_ms)

    output_text = _extract_response_text(response)
    if output_text:
        output_scan = await scan(output_text, "output", {})
        if output_scan.action == "block":
            raise GatewayError(
                "invalid_request",
                f"Output blocked by NoviSentinel: {output_scan.risk_level} risk detected",
                400,
                provider_name,
            )

    return response


async def call_provider_only(
    request: ChatCompletionRequest,
    upstream_api_key: str = "",
) -> ChatCompletionResponse:
    """Bypass scanner — used by the proxy, which does its own scan/redact/restore."""
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
