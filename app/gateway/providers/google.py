"""Google Gemini egress provider.

Translates OpenAI chat-completion shape ↔ Google GenerativeAI (gemini) shape.
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

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT = httpx.Timeout(60.0)


def _to_gemini(request: ChatCompletionRequest) -> tuple[str, dict[str, Any]]:
    model_name = request.model.split("/", 1)[-1]

    contents: list[dict[str, Any]] = []
    system_instruction: str | None = None

    for msg in request.messages:
        if msg.role == "system":
            system_instruction = msg.content if isinstance(msg.content, str) else str(msg.content)
            continue

        gemini_role = "user" if msg.role == "user" else "model"

        if msg.tool_calls:
            parts: list[dict[str, Any]] = []
            if msg.content:
                parts.append({"text": msg.content if isinstance(msg.content, str) else str(msg.content)})
            for tc in msg.tool_calls:
                parts.append(
                    {
                        "functionCall": {
                            "name": tc.function.name,
                            "args": json.loads(tc.function.arguments),
                        }
                    }
                )
            contents.append({"role": gemini_role, "parts": parts})
        elif msg.role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": msg.tool_call_id or "tool",
                                "response": {"content": msg.content},
                            }
                        }
                    ],
                }
            )
        elif isinstance(msg.content, list):
            parts = []
            for part in msg.content:
                if part.type == "text":
                    parts.append({"text": part.text or ""})
                else:
                    parts.append(part.model_dump(exclude_none=True))
            contents.append({"role": gemini_role, "parts": parts})
        else:
            contents.append(
                {
                    "role": gemini_role,
                    "parts": [{"text": msg.content or ""}],
                }
            )

    payload: dict[str, Any] = {"contents": contents}

    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    generation_config: dict[str, Any] = {}
    if request.temperature is not None:
        generation_config["temperature"] = request.temperature
    if request.top_p is not None:
        generation_config["topP"] = request.top_p
    if request.max_tokens or request.max_completion_tokens:
        generation_config["maxOutputTokens"] = request.max_completion_tokens or request.max_tokens
    if request.stop:
        generation_config["stopSequences"] = request.stop if isinstance(request.stop, list) else [request.stop]
    if generation_config:
        payload["generationConfig"] = generation_config

    if request.tools:
        payload["tools"] = [
            {
                "functionDeclarations": [
                    {
                        "name": t.function.name,
                        "description": t.function.description or "",
                        "parameters": t.function.parameters or {"type": "object", "properties": {}},
                    }
                    for t in request.tools
                ]
            }
        ]

    return model_name, payload


def _from_gemini(data: dict[str, Any], original_model: str) -> ChatCompletionResponse:
    candidates = data.get("candidates", [])
    choices: list[Choice] = []

    for i, candidate in enumerate(candidates):
        parts = candidate.get("content", {}).get("parts", [])
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=f"call_{fc['name']}_{i}",
                        function=FunctionCall(
                            name=fc["name"],
                            arguments=json.dumps(fc.get("args", {})),
                        ),
                    )
                )

        finish_map = {
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter",
            "TOOL_CODE": "tool_calls",
        }
        finish_reason = finish_map.get(candidate.get("finishReason", "STOP"), "stop")
        if tool_calls:
            finish_reason = "tool_calls"

        choices.append(
            Choice(
                index=i,
                message=ChatMessage(
                    role="assistant",
                    content="\n".join(text_parts) if text_parts else None,
                    tool_calls=tool_calls or None,
                ),
                finish_reason=finish_reason,
            )
        )

    usage_meta = data.get("usageMetadata", {})
    usage = Usage(
        prompt_tokens=usage_meta.get("promptTokenCount", 0),
        completion_tokens=usage_meta.get("candidatesTokenCount", 0),
        total_tokens=usage_meta.get("totalTokenCount", 0),
    )

    return ChatCompletionResponse(
        id=f"gemini-{int(time.time())}",
        object="chat.completion",
        created=int(time.time()),
        model=original_model,
        choices=choices,
        usage=usage,
    )


class GoogleProvider(Provider):
    async def complete(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ChatCompletionResponse:
        model_name, payload = _to_gemini(request)

        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
            resp = await client.post(
                f"{_BASE_URL}/models/{model_name}:generateContent",
                json=payload,
                params={"key": api_key},
            )
            resp.raise_for_status()

        return _from_gemini(resp.json(), request.model)

    async def stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[ChatCompletionChunk]:
        model_name, payload = _to_gemini(request)

        async with (
            httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client,
            client.stream(
                "POST",
                f"{_BASE_URL}/models/{model_name}:streamGenerateContent",
                json=payload,
                params={"key": api_key, "alt": "sse"},
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                event = json.loads(data_str)
                candidates = event.get("candidates", [])
                for candidate in candidates:
                    parts = candidate.get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts if "text" in p)
                    finish_reason = candidate.get("finishReason")
                    yield ChatCompletionChunk(
                        id=f"gemini-{int(time.time())}",
                        created=int(time.time()),
                        model=request.model,
                        choices=[
                            ChunkChoice(
                                index=candidate.get("index", 0),
                                delta=ChoiceDelta(role="assistant", content=text),
                                finish_reason=finish_reason,
                            )
                        ],
                    )
