"""SSE streaming orchestrator with mid-stream scan.

Chunks flow from the provider through a sliding buffer. Every
SCAN_INTERVAL_CHARS characters (or SCAN_INTERVAL_MS milliseconds) the
accumulated text is scanned. If the scanner blocks, a synthetic error
event is emitted and the stream is closed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator

from app.gateway.schemas import ChatCompletionRequest

logger = logging.getLogger(__name__)

_SCAN_INTERVAL_CHARS = 200
_SCAN_INTERVAL_MS = 100


def _sse_line(data: str) -> bytes:
    return f"data: {data}\n\n".encode()


def _error_chunk(message: str) -> bytes:
    payload = {
        "error": {
            "message": message,
            "type": "content_filter",
            "code": "content_policy_violation",
        }
    }
    return _sse_line(json.dumps(payload))


async def stream_with_scan(
    request: ChatCompletionRequest,
    upstream_api_key: str,
) -> AsyncIterator[bytes]:
    """Yield SSE bytes. Scans accumulated text and blocks mid-stream if needed."""
    from app.core.scanner import scan
    from app.gateway.orchestrator import _resolve_upstream_key
    from app.gateway.router import get_provider

    provider, provider_name = get_provider(request.model)
    key = upstream_api_key or _resolve_upstream_key(provider_name)

    accumulated = ""
    last_scan_len = 0
    last_scan_time = time.monotonic()
    scan_task: asyncio.Task | None = None
    block_message: str | None = None

    async for chunk in provider.stream(request, key):
        if block_message is not None:
            break

        for choice in chunk.choices:
            if choice.delta.content:
                accumulated += choice.delta.content

        yield _sse_line(json.dumps(chunk.model_dump(exclude_none=True)))

        chars_since_scan = len(accumulated) - last_scan_len
        ms_since_scan = (time.monotonic() - last_scan_time) * 1000
        should_scan = chars_since_scan >= _SCAN_INTERVAL_CHARS or ms_since_scan >= _SCAN_INTERVAL_MS

        if should_scan and (scan_task is None or scan_task.done()):
            text_snapshot = accumulated
            last_scan_len = len(accumulated)
            last_scan_time = time.monotonic()

            async def _do_scan(text: str = text_snapshot) -> str | None:
                result = await scan(text, "output", {})
                if result.action == "block":
                    return f"Content blocked by NoviSentinel: {result.risk_level} risk detected"
                return None

            scan_task = asyncio.create_task(_do_scan())

        if scan_task is not None and scan_task.done():
            block_message = scan_task.result()
            if block_message:
                yield _error_chunk(block_message)
                yield _sse_line("[DONE]")
                return

    if accumulated and not block_message:
        result = await scan(accumulated, "output", {})
        if result.action == "block":
            yield _error_chunk(f"Content blocked by NoviSentinel: {result.risk_level} risk detected")
            yield _sse_line("[DONE]")
            return

    yield _sse_line("[DONE]")
