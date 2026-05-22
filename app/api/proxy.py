"""Transparent proxy endpoints — redact secrets before forwarding to AI providers,
restore placeholders in the response so callers never notice.

Drop-in replacements:
  OPENAI_BASE_URL=http://localhost:8000      ->  POST /v1/chat/completions
  ANTHROPIC_BASE_URL=http://localhost:8000   ->  POST /v1/messages
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse

from app.core.anonymizer import AnonymizationMap
from app.gateway.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from app.security import require_gateway_auth

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_gateway_auth)])


# ── helpers ───────────────────────────────────────────────────────────────────


def _bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    return authorization.removeprefix("Bearer ").strip()


def _select_upstream_key(
    bearer: str,
    byok_header: str | None,
    provider_name: str,
) -> str:
    """Env wins by default; bearer only honored when X-Use-BYOK is truthy."""
    from fastapi import HTTPException

    from app.gateway.orchestrator import _resolve_upstream_key

    byok = (byok_header or "").strip().lower() in ("1", "true", "yes")
    if byok:
        if not bearer:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": "X-Use-BYOK requires Authorization or x-api-key",
                        "type": "invalid_request",
                    }
                },
            )
        return bearer
    return _resolve_upstream_key(provider_name)


def _sse(data: str) -> bytes:
    return f"data: {data}\n\n".encode()


def _sse_event(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def _anthropic_error_body(message: str) -> dict:
    return {"type": "error", "error": {"type": "invalid_request_error", "message": message}}


def _to_internal(body: dict) -> ChatCompletionRequest:
    """Convert Anthropic request shape -> internal OpenAI ChatCompletionRequest."""
    messages: list[dict] = []
    if "system" in body:
        messages.append({"role": "system", "content": body["system"]})
    messages.extend(body.get("messages", []))
    return ChatCompletionRequest(
        model=body.get("model", "claude-3-5-sonnet-20241022"),
        messages=[ChatMessage(**m) for m in messages],
        max_tokens=body.get("max_tokens"),
        temperature=body.get("temperature"),
        top_p=body.get("top_p"),
        stream=body.get("stream", False),
        stop=body.get("stop_sequences"),
    )


def _to_anthropic_response(response: ChatCompletionResponse, original_model: str) -> dict:
    """Convert internal ChatCompletionResponse -> Anthropic response shape."""
    content: list[dict] = []
    stop_reason = "end_turn"
    for choice in response.choices:
        if choice.message and choice.message.content:
            content.append({"type": "text", "text": str(choice.message.content)})
        if choice.finish_reason == "length":
            stop_reason = "max_tokens"
        elif choice.finish_reason == "tool_calls":
            stop_reason = "tool_use"
    result: dict = {
        "id": response.id or f"msg_{int(time.time())}",
        "type": "message",
        "role": "assistant",
        "model": original_model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
    }
    if response.usage:
        result["usage"] = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
    return result


async def _scan_and_redact(
    request: ChatCompletionRequest,
) -> tuple[ChatCompletionRequest, AnonymizationMap, str | None]:
    """Scan each message. Block on injection/critical risk; redact PII/secrets otherwise.

    Returns (possibly_modified_request, anon_map, block_reason_or_None).
    """
    from app.core.scanner import scan

    anon_map = AnonymizationMap()
    new_messages: list[ChatMessage] = list(request.messages)

    threat_detectors = {"injection", "toxicity", "code_injection"}
    redactable_detectors = {"pii", "secrets", "urls", "custom"}

    for i, msg in enumerate(request.messages):
        if not isinstance(msg.content, str) or not msg.content:
            continue
        result = await scan(msg.content, "input", {})

        threats = [
            d for d in result.detections if d.detector in threat_detectors and d.severity in ("critical", "high")
        ]
        if threats:
            threat_types = [f"{d.detector}:{d.type}" for d in threats]
            logger.info("[scan]    BLOCKED — threat detected: %s", ", ".join(threat_types))
            return request, anon_map, f"Blocked: {result.risk_level} risk detected in message"

        redactable = [d for d in result.detections if d.detector in redactable_detectors]
        if redactable:
            types = [d.type for d in redactable]
            logger.info("[scan]    detected %d privacy item(s): %s", len(redactable), ", ".join(types))
            redacted_text = anon_map.redact(msg.content, redactable)
            new_messages[i] = msg.model_copy(update={"content": redacted_text})
            logger.info("[upstream sees] %s", redacted_text)

    if anon_map.is_empty:
        logger.info("[scan]    clean — no redaction needed")
    else:
        logger.info("[redact]  forwarding upstream with %d placeholder(s)", len(anon_map.mapping))

    return request.model_copy(update={"messages": new_messages}), anon_map, None


def _restore_response(response: ChatCompletionResponse, anon_map: AnonymizationMap) -> ChatCompletionResponse:
    if anon_map.is_empty:
        return response
    new_choices = []
    for choice in response.choices:
        if choice.message and isinstance(choice.message.content, str):
            restored = anon_map.restore(choice.message.content)
            new_choices.append(
                choice.model_copy(update={"message": choice.message.model_copy(update={"content": restored})})
            )
        else:
            new_choices.append(choice)
    logger.info("[restore] swapped %d placeholder(s) back into response", len(anon_map.mapping))
    return response.model_copy(update={"choices": new_choices})


# ── streaming generators ──────────────────────────────────────────────────────


async def _openai_stream_gen(
    request: ChatCompletionRequest,
    api_key: str,
    anon_map: AnonymizationMap,
) -> AsyncIterator[bytes]:
    """Stream OpenAI-compatible deltas to the caller.

    Output is scanned every _SCAN_CHARS / _SCAN_MS while accumulating, but
    chunks are held in a buffer until the most-recent scan returns: if the
    scan says BLOCK, we emit an error event without having leaked the
    buffered text. The provider stream is closed via `aclose()` on the way
    out so we don't leak the upstream HTTP connection.
    """
    from app.core.scanner import scan as scan_text
    from app.gateway.reliability import get_circuit_breaker
    from app.gateway.router import get_provider

    provider, provider_name = get_provider(request.model)
    cb = get_circuit_breaker(provider_name)
    cb.check()

    tail = ""
    accumulated = ""
    last_scan_len = 0
    last_scan_time = time.monotonic()
    pending_scan: asyncio.Task | None = None
    pending_buffer: list[bytes] = []

    stream = provider.stream(request, api_key)
    try:
        async for chunk in stream:
            if not anon_map.is_empty:
                new_choices = []
                for choice in chunk.choices:
                    if choice.delta.content:
                        safe, tail = anon_map.restore_chunk(choice.delta.content, tail)
                        new_choices.append(
                            choice.model_copy(
                                update={"delta": choice.delta.model_copy(update={"content": safe or None})}
                            )
                        )
                    else:
                        new_choices.append(choice)
                chunk = chunk.model_copy(update={"choices": new_choices})

            for choice in chunk.choices:
                if choice.delta.content:
                    accumulated += choice.delta.content

            chunk_bytes = _sse(json.dumps(chunk.model_dump(exclude_none=True)))

            if pending_scan is not None:
                # Hold the chunk until the prior scan completes — never leak
                # past a block decision.
                pending_buffer.append(chunk_bytes)
                if pending_scan.done():
                    block_msg = pending_scan.result()
                    pending_scan = None
                    if block_msg:
                        yield _error_chunk(block_msg)
                        yield _sse("[DONE]")
                        return
                    for buffered in pending_buffer:
                        yield buffered
                    pending_buffer.clear()
            else:
                yield chunk_bytes

            chars_since = len(accumulated) - last_scan_len
            ms_since = (time.monotonic() - last_scan_time) * 1000
            if pending_scan is None and (chars_since >= _SCAN_CHARS or ms_since >= _SCAN_MS):
                snap = accumulated
                last_scan_len = len(accumulated)
                last_scan_time = time.monotonic()
                pending_scan = asyncio.create_task(_scan_output(snap, scan_text))

        if pending_scan is not None:
            block_msg = await pending_scan
            if block_msg:
                yield _error_chunk(block_msg)
                yield _sse("[DONE]")
                return
            for buffered in pending_buffer:
                yield buffered

        cb.record_success()
    except Exception:
        cb.record_failure()
        raise
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            with contextlib.suppress(Exception):
                await aclose()

    if tail:
        restored = anon_map.restore(tail)
        if restored:
            flush = {
                "id": f"novisentinel-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{"index": 0, "delta": {"content": restored}, "finish_reason": None}],
            }
            yield _sse(json.dumps(flush))
    yield _sse("[DONE]")


_SCAN_CHARS = 200
_SCAN_MS = 100


def _error_chunk(message: str) -> bytes:
    payload = {
        "error": {
            "message": message,
            "type": "content_filter",
            "code": "content_policy_violation",
        }
    }
    return _sse(json.dumps(payload))


async def _scan_output(text: str, scan_fn) -> str | None:
    result = await scan_fn(text, "output", {})
    if result.action == "block":
        return f"Content blocked by NoviSentinel: {result.risk_level} risk detected"
    return None


async def _anthropic_stream_gen(
    request: ChatCompletionRequest,
    api_key: str,
    anon_map: AnonymizationMap,
    original_model: str,
) -> AsyncIterator[bytes]:
    from app.gateway.reliability import get_circuit_breaker
    from app.gateway.router import get_provider

    provider, provider_name = get_provider(request.model)
    cb = get_circuit_breaker(provider_name)
    cb.check()

    msg_id = f"msg_{int(time.time())}"
    yield _sse_event(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "model": original_model,
                "content": [],
                "stop_reason": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        },
    )
    yield _sse_event(
        "content_block_start",
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
    )
    yield b'event: ping\ndata: {"type":"ping"}\n\n'

    from app.core.scanner import scan as scan_text

    tail = ""
    stop_reason = "end_turn"
    accumulated = ""
    last_scan_len = 0
    last_scan_time = time.monotonic()
    pending_scan: asyncio.Task | None = None
    pending_events: list[bytes] = []

    stream = provider.stream(request, api_key)
    try:
        async for chunk in stream:
            for choice in chunk.choices:
                if choice.delta.content:
                    safe, tail = anon_map.restore_chunk(choice.delta.content, tail)
                    if safe:
                        accumulated += safe
                        evt = _sse_event(
                            "content_block_delta",
                            {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": safe},
                            },
                        )
                        if pending_scan is not None:
                            pending_events.append(evt)
                            if pending_scan.done():
                                block_msg = pending_scan.result()
                                pending_scan = None
                                if block_msg:
                                    yield _sse_event(
                                        "error",
                                        {"type": "error", "error": {"type": "content_filter", "message": block_msg}},
                                    )
                                    yield _sse_event("message_stop", {"type": "message_stop"})
                                    return
                                for buf in pending_events:
                                    yield buf
                                pending_events.clear()
                        else:
                            yield evt
                if choice.finish_reason == "length":
                    stop_reason = "max_tokens"

            chars_since = len(accumulated) - last_scan_len
            ms_since = (time.monotonic() - last_scan_time) * 1000
            if pending_scan is None and (chars_since >= _SCAN_CHARS or ms_since >= _SCAN_MS):
                snap = accumulated
                last_scan_len = len(accumulated)
                last_scan_time = time.monotonic()
                pending_scan = asyncio.create_task(_scan_output(snap, scan_text))

        if pending_scan is not None:
            block_msg = await pending_scan
            if block_msg:
                yield _sse_event(
                    "error",
                    {"type": "error", "error": {"type": "content_filter", "message": block_msg}},
                )
                yield _sse_event("message_stop", {"type": "message_stop"})
                return
            for buf in pending_events:
                yield buf

        cb.record_success()
    except Exception:
        cb.record_failure()
        raise
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            with contextlib.suppress(Exception):
                await aclose()

    if tail:
        restored = anon_map.restore(tail)
        if restored:
            yield _sse_event(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": restored},
                },
            )

    yield _sse_event("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield _sse_event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 0},
        },
    )
    yield _sse_event("message_stop", {"type": "message_stop"})


# ── endpoints ─────────────────────────────────────────────────────────────────


@router.post("/v1/chat/completions")
async def openai_proxy(
    request: ChatCompletionRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_use_byok: str | None = Header(default=None, alias="X-Use-BYOK"),
):
    from app.gateway.errors import GatewayError, normalize_error
    from app.gateway.orchestrator import call_provider_only
    from app.gateway.router import get_provider

    api_key = _bearer(authorization)
    _, provider_name = get_provider(request.model)
    resolved_key = _select_upstream_key(api_key, x_use_byok, provider_name)

    redacted_req, anon_map, block_reason = await _scan_and_redact(request)

    if block_reason:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail={"error": {"message": block_reason, "type": "content_filter"}},
        )

    if request.stream:
        return StreamingResponse(
            _openai_stream_gen(redacted_req, resolved_key, anon_map),
            media_type="text/event-stream",
        )

    try:
        response = await call_provider_only(redacted_req, resolved_key)
    except GatewayError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=exc.upstream_status or 502,
            detail={"error": {"message": exc.message, "type": exc.error_type}},
        ) from exc
    except Exception as exc:
        from fastapi import HTTPException

        err = normalize_error(exc, "unknown")
        raise HTTPException(
            status_code=err.upstream_status or 502,
            detail={"error": {"message": err.message, "type": err.error_type}},
        ) from exc

    return _restore_response(response, anon_map)


@router.post("/v1/messages")
async def anthropic_proxy(
    raw_request: Request,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_use_byok: str | None = Header(default=None, alias="X-Use-BYOK"),
):
    from app.gateway.errors import GatewayError, normalize_error
    from app.gateway.orchestrator import call_provider_only
    from app.gateway.router import get_provider

    body: dict = await raw_request.json()
    original_model: str = body.get("model", "claude-3-5-sonnet-20241022")
    bearer = x_api_key or _bearer(authorization) or ""

    internal_req = _to_internal(body)
    _, provider_name = get_provider(internal_req.model)
    resolved_key = _select_upstream_key(bearer, x_use_byok, provider_name)

    redacted_req, anon_map, block_reason = await _scan_and_redact(internal_req)

    if block_reason:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=_anthropic_error_body(block_reason))

    if body.get("stream"):
        return StreamingResponse(
            _anthropic_stream_gen(redacted_req, resolved_key, anon_map, original_model),
            media_type="text/event-stream",
        )

    try:
        response = await call_provider_only(redacted_req, resolved_key)
    except GatewayError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=exc.upstream_status or 502,
            detail=_anthropic_error_body(exc.message),
        ) from exc
    except Exception as exc:
        from fastapi import HTTPException

        err = normalize_error(exc, "anthropic")
        raise HTTPException(
            status_code=err.upstream_status or 502,
            detail=_anthropic_error_body(err.message),
        ) from exc

    return _to_anthropic_response(_restore_response(response, anon_map), original_model)
