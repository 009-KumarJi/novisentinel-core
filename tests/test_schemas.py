"""Unit tests for gateway schemas — streaming-delta edge cases."""

from __future__ import annotations

from app.gateway.schemas import FunctionCall, ToolCall


def test_tool_call_partial_streaming_delta():
    """A streaming delta with only index + partial arguments must parse without error."""
    tc = ToolCall.model_validate({"index": 0, "function": {"arguments": '{"to"'}})
    assert tc.index == 0
    assert tc.id is None
    assert tc.function.arguments == '{"to"'
    assert tc.function.name is None


def test_tool_call_full_response_shape():
    """A complete non-streaming tool_call must still parse correctly."""
    tc = ToolCall.model_validate(
        {
            "id": "call_abc123",
            "type": "function",
            "function": {"name": "send_email", "arguments": '{"to":"alice@acme.com"}'},
        }
    )
    assert tc.id == "call_abc123"
    assert tc.function.name == "send_email"


def test_function_call_name_optional():
    fc = FunctionCall.model_validate({"arguments": '{"key":"val"}'})
    assert fc.name is None
    assert fc.arguments == '{"key":"val"}'
