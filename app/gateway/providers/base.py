from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.gateway.schemas import ChatCompletionChunk, ChatCompletionRequest, ChatCompletionResponse


class Provider(ABC):
    @abstractmethod
    async def complete(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ChatCompletionResponse: ...

    @abstractmethod
    async def stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[ChatCompletionChunk]:
        raise NotImplementedError
        yield  # type: ignore[misc]
