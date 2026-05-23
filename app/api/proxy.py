"""Transparent proxy endpoints — redact secrets before forwarding to AI providers,
restore placeholders in the response so callers never notice.

Drop-in replacements:
  OPENAI_BASE_URL=http://localhost:8000      ->  POST /v1/chat/completions
  ANTHROPIC_BASE_URL=http://localhost:8000   ->  POST /v1/messages
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
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


def _derive_session_id(x_session: str | None, messages: list[ChatMessage]) -> str | None:
    """Derive a stable session ID from the header or the conversation prefix hash."""
    if x_session:
        return f"client:{x_session.strip()}"
    prefix = messages[:-1]
    if not prefix:
        return None
    try:
        minimal = [
            {
                "role": m.role,
                "content": m.content
                if isinstance(m.content, str)
                else [p.model_dump() for p in m.content]
                if isinstance(m.content, list)
                else None,
            }
            for m in prefix
        ]
        payload = json.dumps(minimal, sort_keys=True, default=str)
    except Exception:
        return None
    return f"prefix:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


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
        for tc in (choice.message.tool_calls or []) if choice.message else []:
            try:
                parsed_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except (json.JSONDecodeError, ValueError):
                parsed_input = {"_raw": tc.function.arguments}
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.id or f"toolu_{int(time.time())}_{len(content)}",
                    "name": tc.function.name or "",
                    "input": parsed_input,
                }
            )
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


_CONTEXT_FOR_KIND = {
    "tool_result": "tool_output",
    "tool_call_args": "tool_call_args",
    "tool_use_input": "tool_call_args",
    "tool_def_description": "tool_def",
}


async def _scan_and_redact(
    request: ChatCompletionRequest,
    anon_map: AnonymizationMap | None = None,
) -> tuple[ChatCompletionRequest, AnonymizationMap, str | None]:
    """Scan all message surfaces. Block on injection/critical risk; redact PII/secrets otherwise.

    Returns (possibly_modified_request, anon_map, block_reason_or_None).
    """
    from app.config import settings
    from app.core.scan_surfaces import request_surfaces
    from app.core.scanner import scan

    if anon_map is None:
        anon_map = AnonymizationMap()

    working = request.model_copy(deep=True)
    new_messages: list[ChatMessage] = list(working.messages)

    threat_detectors = {"injection", "toxicity", "code_injection"}
    redactable_detectors = {"pii", "secrets", "urls", "custom"}

    for surface in request_surfaces(working, new_messages, scan_tool_defs=settings.scan_tool_defs):
        if not surface.text:
            continue
        context = _CONTEXT_FOR_KIND.get(surface.kind, "input")
        result = await scan(surface.text, context, {})

        threats = [
            d for d in result.detections if d.detector in threat_detectors and d.severity in ("critical", "high")
        ]
        if threats:
            threat_types = [f"{d.detector}:{d.type}" for d in threats]
            logger.info("[scan]    BLOCKED — threat detected in %s: %s", surface.label, ", ".join(threat_types))
            return request, anon_map, f"Blocked: {result.risk_level} risk detected in message"

        redactable = [d for d in result.detections if d.detector in redactable_detectors]
        if redactable:
            types = [d.type for d in redactable]
            logger.info(
                "[scan]    %s detected %d privacy item(s): %s", surface.label, len(redactable), ", ".join(types)
            )
            redacted = anon_map.redact(surface.text, redactable)
            surface.replace(redacted)
            logger.info("[upstream sees] %s", redacted)

    if anon_map.is_empty:
        logger.info("[scan]    clean — no redaction needed")
    else:
        logger.info("[redact]  forwarding upstream with %d placeholder(s)", len(anon_map.mapping))

    return working.model_copy(update={"messages": new_messages}), anon_map, None


def _restore_response(response: ChatCompletionResponse, anon_map: AnonymizationMap) -> ChatCompletionResponse:
    if anon_map.is_empty:
        return response
    from app.core.scan_surfaces import restore_message

    new_choices = []
    for choice in response.choices:
        if choice.message:
            new_choices.append(choice.model_copy(update={"message": restore_message(choice.message, anon_map)}))
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
    from app.gateway.schemas import FunctionCall, ToolCall

    provider, provider_name = get_provider(request.model)
    cb = get_circuit_breaker(provider_name)
    cb.check()

    content_tail: str = ""
    tool_arg_tails: dict[int, str] = {}
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
                    delta_updates: dict = {}

                    if choice.delta.content:
                        safe, content_tail = anon_map.restore_chunk(choice.delta.content, content_tail)
                        delta_updates["content"] = safe or None

                    if choice.delta.tool_calls:
                        new_tcs = []
                        for tc in choice.delta.tool_calls:
                            if tc.function and tc.function.arguments:
                                idx = tc.index if tc.index is not None else 0
                                prev = tool_arg_tails.get(idx, "")
                                safe_args, new_tail = anon_map.restore_chunk(tc.function.arguments, prev)
                                tool_arg_tails[idx] = new_tail
                                new_tcs.append(
                                    tc.model_copy(
                                        update={
                                            "function": tc.function.model_copy(update={"arguments": safe_args or None})
                                        }
                                    )
                                )
                            else:
                                new_tcs.append(tc)
                        delta_updates["tool_calls"] = new_tcs

                    if delta_updates:
                        new_choices.append(
                            choice.model_copy(update={"delta": choice.delta.model_copy(update=delta_updates)})
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

    if content_tail:
        restored = anon_map.restore(content_tail)
        if restored:
            flush = {
                "id": f"novisentinel-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{"index": 0, "delta": {"content": restored}, "finish_reason": None}],
            }
            yield _sse(json.dumps(flush))

    for idx, residual in tool_arg_tails.items():
        if residual:
            restored_args = anon_map.restore(residual)
            if restored_args:
                flush_tc = {
                    "id": f"novisentinel-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "tool_calls": [
                                    ToolCall(
                                        index=idx,
                                        function=FunctionCall(arguments=restored_args),
                                    ).model_dump(exclude_none=True)
                                ]
                            },
                            "finish_reason": None,
                        }
                    ],
                }
                yield _sse(json.dumps(flush_tc))

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

    content_tail: str = ""
    # tool_blocks[tc_index] = {block_index, args_tail, started, name, id}
    tool_blocks: dict[int, dict] = {}
    next_block_index: list[int] = [1]  # index 0 is the text block; tool_calls start at 1
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
                    safe, content_tail = anon_map.restore_chunk(choice.delta.content, content_tail)
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

                for tc in choice.delta.tool_calls or []:
                    tc_idx = tc.index if tc.index is not None else 0
                    if tc_idx not in tool_blocks:
                        blk_idx = next_block_index[0]
                        next_block_index[0] += 1
                        tool_blocks[tc_idx] = {
                            "block_index": blk_idx,
                            "args_tail": "",
                            "name": tc.function.name if tc.function else None,
                            "id": tc.id,
                        }
                        tc_id = tc.id or f"toolu_{int(time.time())}_{tc_idx}"
                        tc_name = (tc.function.name or "") if tc.function else ""
                        yield _sse_event(
                            "content_block_start",
                            {
                                "type": "content_block_start",
                                "index": blk_idx,
                                "content_block": {
                                    "type": "tool_use",
                                    "id": tc_id,
                                    "name": tc_name,
                                    "input": {},
                                },
                            },
                        )

                    if tc.function and tc.function.arguments:
                        blk = tool_blocks[tc_idx]
                        safe_args, new_tail = anon_map.restore_chunk(tc.function.arguments, blk["args_tail"])
                        blk["args_tail"] = new_tail
                        if safe_args:
                            yield _sse_event(
                                "content_block_delta",
                                {
                                    "type": "content_block_delta",
                                    "index": blk["block_index"],
                                    "delta": {"type": "input_json_delta", "partial_json": safe_args},
                                },
                            )

                if choice.finish_reason == "length":
                    stop_reason = "max_tokens"
                elif choice.finish_reason == "tool_calls" and tool_blocks:
                    stop_reason = "tool_use"

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

    if content_tail:
        restored = anon_map.restore(content_tail)
        if restored:
            yield _sse_event(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": restored},
                },
            )

    for blk in tool_blocks.values():
        if blk["args_tail"]:
            restored_args = anon_map.restore(blk["args_tail"])
            if restored_args:
                yield _sse_event(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": blk["block_index"],
                        "delta": {"type": "input_json_delta", "partial_json": restored_args},
                    },
                )
        yield _sse_event("content_block_stop", {"type": "content_block_stop", "index": blk["block_index"]})

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
    x_session: str | None = Header(default=None, alias="X-Novisentinel-Session"),
):
    from app.core.session_store import get_session_store
    from app.gateway.errors import GatewayError, normalize_error
    from app.gateway.orchestrator import call_provider_only
    from app.gateway.router import get_provider

    api_key = _bearer(authorization)
    _, provider_name = get_provider(request.model)
    resolved_key = _select_upstream_key(api_key, x_use_byok, provider_name)

    session_id = _derive_session_id(x_session, request.messages)

    if session_id:
        async with get_session_store().with_session(session_id) as anon_map:
            redacted_req, anon_map, block_reason = await _scan_and_redact(request, anon_map)
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
    else:
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
    x_session: str | None = Header(default=None, alias="X-Novisentinel-Session"),
):
    from app.core.session_store import get_session_store
    from app.gateway.errors import GatewayError, normalize_error
    from app.gateway.orchestrator import call_provider_only
    from app.gateway.router import get_provider

    body: dict = await raw_request.json()
    original_model: str = body.get("model", "claude-3-5-sonnet-20241022")
    bearer = x_api_key or _bearer(authorization) or ""

    internal_req = _to_internal(body)
    _, provider_name = get_provider(internal_req.model)
    resolved_key = _select_upstream_key(bearer, x_use_byok, provider_name)

    session_id = _derive_session_id(x_session, internal_req.messages)

    async def _run_scan(am=None):
        return await _scan_and_redact(internal_req, am)

    async def _do_respond(redacted_req, anon_map, block_reason):
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

    if session_id:
        async with get_session_store().with_session(session_id) as anon_map:
            redacted_req, anon_map, block_reason = await _scan_and_redact(internal_req, anon_map)
            return await _do_respond(redacted_req, anon_map, block_reason)
    else:
        redacted_req, anon_map, block_reason = await _scan_and_redact(internal_req)
        return await _do_respond(redacted_req, anon_map, block_reason)
