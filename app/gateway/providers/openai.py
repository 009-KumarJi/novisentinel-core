from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.gateway.providers.base import Provider
from app.gateway.schemas import ChatCompletionChunk, ChatCompletionRequest, ChatCompletionResponse

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openai.com/v1"
_TIMEOUT = httpx.Timeout(60.0)


class OpenAIProvider(Provider):
    def __init__(self, base_url: str = _BASE_URL) -> None:
        self._base_url = base_url

    async def complete(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ChatCompletionResponse:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = False

        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
        return ChatCompletionResponse(**resp.json())

    async def stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[ChatCompletionChunk]:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True

        async with (
            httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client,
            client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                yield ChatCompletionChunk(**json.loads(data))
