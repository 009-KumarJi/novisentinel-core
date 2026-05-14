"""Anthropic egress provider.

Translates OpenAI chat-completion shape ↔ Anthropic Messages API shape.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.gateway.providers.base import Provider
from app.gateway.schemas import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    ChoiceDelta,
    ChunkChoice,
    FunctionCall,
    ToolCall,
    Usage,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = httpx.Timeout(60.0)
_DEFAULT_MAX_TOKENS = 4096


def _to_anthropic(request: ChatCompletionRequest) -> dict[str, Any]:
    system_parts: list[str] = []
    messages: list[dict[str, Any]] = []

    for msg in request.messages:
        role = msg.role
        content = msg.content

        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            continue

        if role == "tool":
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": content if isinstance(content, str) else json.dumps(content),
                        }
                    ],
                }
            )
            continue

        if role == "assistant" and msg.tool_calls:
            content_blocks: list[dict[str, Any]] = []
            if content:
                content_blocks.append(
                    {
                        "type": "text",
                        "text": content if isinstance(content, str) else str(content),
                    }
                )
            for tc in msg.tool_calls:
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments),
                    }
                )
            messages.append({"role": "assistant", "content": content_blocks})
            continue

        if isinstance(content, list):
            anthropic_parts: list[dict[str, Any]] = []
            for part in content:
                if part.type == "text":
                    anthropic_parts.append({"type": "text", "text": part.text or ""})
                else:
                    anthropic_parts.append(part.model_dump(exclude_none=True))
            messages.append({"role": role, "content": anthropic_parts})
        else:
            messages.append({"role": role, "content": content or ""})

    payload: dict[str, Any] = {
        "model": request.model.split("/", 1)[-1],
        "messages": messages,
        "max_tokens": (request.max_completion_tokens or request.max_tokens or _DEFAULT_MAX_TOKENS),
    }

    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    if request.stop:
        payload["stop_sequences"] = request.stop if isinstance(request.stop, list) else [request.stop]
    if request.tools:
        payload["tools"] = [
            {
                "name": t.function.name,
                "description": t.function.description or "",
                "input_schema": t.function.parameters or {"type": "object", "properties": {}},
            }
            for t in request.tools
        ]
    if request.tool_choice and isinstance(request.tool_choice, dict):
        payload["tool_choice"] = request.tool_choice
    elif request.tool_choice == "auto":
        payload["tool_choice"] = {"type": "auto"}
    elif request.tool_choice == "none":
        payload["tool_choice"] = {"type": "none"}

    return payload


def _from_anthropic(data: dict[str, Any], original_model: str) -> ChatCompletionResponse:
    content_blocks = data.get("content", [])
    tool_calls: list[ToolCall] = []
    text_parts: list[str] = []

    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block["id"],
                    function=FunctionCall(
                        name=block["name"],
                        arguments=json.dumps(block.get("input", {})),
                    ),
                )
            )

    stop_reason = data.get("stop_reason", "end_turn")
    finish_reason_map = {
        "end_turn": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
        "stop_sequence": "stop",
    }
    finish_reason = finish_reason_map.get(stop_reason, "stop")

    msg = ChatMessage(
        role="assistant",
        content="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls or None,
    )

    anthropic_usage = data.get("usage", {})
    usage = Usage(
        prompt_tokens=anthropic_usage.get("input_tokens", 0),
        completion_tokens=anthropic_usage.get("output_tokens", 0),
        total_tokens=anthropic_usage.get("input_tokens", 0) + anthropic_usage.get("output_tokens", 0),
    )

    return ChatCompletionResponse(
        id=data.get("id", ""),
        object="chat.completion",
        created=int(time.time()),
        model=original_model,
        choices=[Choice(index=0, message=msg, finish_reason=finish_reason)],
        usage=usage,
    )


class AnthropicProvider(Provider):
    async def complete(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ChatCompletionResponse:
        payload = _to_anthropic(request)

        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
            resp = await client.post(
                f"{_BASE_URL}/messages",
                json=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()

        return _from_anthropic(resp.json(), request.model)

    async def stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[ChatCompletionChunk]:
        payload = _to_anthropic(request)
        payload["stream"] = True

        msg_id = ""
        model_name = request.model

        async with (
            httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client,
            client.stream(
                "POST",
                f"{_BASE_URL}/messages",
                json=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if not data_str.strip():
                    continue
                event = json.loads(data_str)
                event_type = event.get("type", "")

                if event_type == "message_start":
                    msg_id = event.get("message", {}).get("id", "")

                elif event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield ChatCompletionChunk(
                            id=msg_id,
                            created=int(time.time()),
                            model=model_name,
                            choices=[
                                ChunkChoice(
                                    index=event.get("index", 0),
                                    delta=ChoiceDelta(role="assistant", content=delta.get("text", "")),
                                    finish_reason=None,
                                )
                            ],
                        )

                elif event_type == "message_delta":
                    stop_reason = event.get("delta", {}).get("stop_reason")
                    finish_reason_map = {
                        "end_turn": "stop",
                        "max_tokens": "length",
                        "tool_use": "tool_calls",
                    }
                    finish_reason = finish_reason_map.get(stop_reason or "", "stop")
                    yield ChatCompletionChunk(
                        id=msg_id,
                        created=int(time.time()),
                        model=model_name,
                        choices=[
                            ChunkChoice(
                                index=0,
                                delta=ChoiceDelta(),
                                finish_reason=finish_reason,
                            )
                        ],
                    )
