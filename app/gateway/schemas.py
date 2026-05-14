"""OpenAI-compatible request/response schemas.

Extra fields are preserved (extra="allow") so unknown parameters pass through
to the upstream without being silently dropped.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ContentPart(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    text: str | None = None


class FunctionCall(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: str | list[ContentPart] | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class Function(BaseModel):
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None


class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: Function


class ResponseFormat(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str


class StreamOptions(BaseModel):
    include_usage: bool | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    top_p: float | None = None
    n: int | None = None
    stream: bool | None = False
    stop: str | list[str] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    logit_bias: dict[str, float] | None = None
    user: str | None = None
    tools: list[Tool] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_format: ResponseFormat | None = None
    logprobs: bool | None = None
    top_logprobs: int | None = None
    seed: int | None = None
    stream_options: StreamOptions | None = None
    parallel_tool_calls: bool | None = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    model_config = ConfigDict(extra="allow")
    index: int
    message: ChatMessage | None = None
    finish_reason: str | None = None
    logprobs: Any = None


class ChoiceDelta(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str | None = None
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChunkChoice(BaseModel):
    model_config = ConfigDict(extra="allow")
    index: int
    delta: ChoiceDelta
    finish_reason: str | None = None
    logprobs: Any = None


class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage | None = None
    system_fingerprint: str | None = None


class ChatCompletionChunk(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]
    usage: Usage | None = None
