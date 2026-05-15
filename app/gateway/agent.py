"""Tool-call extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.gateway.schemas import ChatCompletionRequest


@dataclass
class ToolCallSpec:
    id: str
    name: str
    arguments: str
    origin: str  # "openai" | "mcp"


@dataclass
class ToolOutput:
    tool_call_id: str
    text: str


def extract_tool_calls(request: ChatCompletionRequest) -> list[ToolCallSpec]:
    specs: list[ToolCallSpec] = []
    for msg in request.messages:
        if msg.role != "assistant" or not msg.tool_calls:
            continue
        for tc in msg.tool_calls:
            if tc.type != "function":
                continue
            specs.append(
                ToolCallSpec(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                    origin="openai",
                )
            )
    return specs
