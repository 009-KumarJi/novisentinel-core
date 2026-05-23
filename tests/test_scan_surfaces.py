"""Unit tests for app.core.scan_surfaces."""

from __future__ import annotations

import json

from app.core.anonymizer import AnonymizationMap
from app.core.scan_surfaces import message_surfaces, request_surfaces, restore_message
from app.gateway.schemas import (
    ChatCompletionRequest,
    ChatMessage,
    ContentPart,
    Function,
    FunctionCall,
    Tool,
    ToolCall,
)


def _make_req(messages: list[ChatMessage], tools=None) -> ChatCompletionRequest:
    return ChatCompletionRequest(model="gpt-4o", messages=messages, tools=tools)


def _new_msgs(req: ChatCompletionRequest) -> list[ChatMessage]:
    return list(req.messages)


# ── string content surfaces ───────────────────────────────────────────────────


def test_user_text_surface():
    msg = ChatMessage(role="user", content="hello alice@acme.com")
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "user_text"
    assert surfs[0].text == "hello alice@acme.com"

    surfs[0].replace("hello <REDACTED_EMAIL_ADDRESS_001>")
    assert msgs[0].content == "hello <REDACTED_EMAIL_ADDRESS_001>"


def test_assistant_text_surface():
    msg = ChatMessage(role="assistant", content="response text")
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "assistant_text"


def test_tool_result_string_surface():
    msg = ChatMessage(role="tool", content="DB url: postgres://user:pass@host/db", tool_call_id="x")
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "tool_result"
    assert "postgres" in surfs[0].text

    surfs[0].replace("DB url: <REDACTED_DATABASE_URL_001>")
    assert msgs[0].content == "DB url: <REDACTED_DATABASE_URL_001>"


# ── tool_calls surface ────────────────────────────────────────────────────────


def test_assistant_tool_call_args_surface_extracted_and_replaced():
    tc = ToolCall(id="c1", function=FunctionCall(name="send", arguments='{"to":"alice@acme.com"}'))
    msg = ChatMessage(role="assistant", content=None, tool_calls=[tc])
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "tool_call_args"
    assert surfs[0].text == '{"to":"alice@acme.com"}'

    surfs[0].replace('{"to":"<REDACTED_EMAIL_ADDRESS_001>"}')
    assert msgs[0].tool_calls[0].function.arguments == '{"to":"<REDACTED_EMAIL_ADDRESS_001>"}'


# ── Anthropic content-list surfaces ──────────────────────────────────────────


def test_anthropic_text_block_surface():
    part = ContentPart(type="text", text="hello alice@acme.com")
    msg = ChatMessage(role="user", content=[part])
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "user_text"
    assert surfs[0].text == "hello alice@acme.com"

    surfs[0].replace("hello <REDACTED_EMAIL_ADDRESS_001>")
    assert msgs[0].content[0].text == "hello <REDACTED_EMAIL_ADDRESS_001>"


def test_anthropic_tool_use_input_surface_roundtrips_json():
    raw = {"to": "alice@acme.com", "subject": "hi"}
    part = ContentPart.model_validate({"type": "tool_use", "input": raw, "name": "send", "id": "tu_1"})
    msg = ChatMessage(role="assistant", content=[part])
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "tool_use_input"
    assert json.loads(surfs[0].text) == raw

    new_json = json.dumps({"to": "<REDACTED_EMAIL_ADDRESS_001>", "subject": "hi"})
    surfs[0].replace(new_json)
    stored = msgs[0].content[0].model_dump()
    assert stored["input"]["to"] == "<REDACTED_EMAIL_ADDRESS_001>"


def test_anthropic_tool_result_block_surface():
    part = ContentPart.model_validate(
        {"type": "tool_result", "tool_use_id": "tu_1", "content": "User email: alice@acme.com"}
    )
    msg = ChatMessage(role="user", content=[part])
    msgs = [msg]
    surfs = message_surfaces(msg, 0, msgs)
    assert len(surfs) == 1
    assert surfs[0].kind == "tool_result"
    assert "alice@acme.com" in surfs[0].text

    surfs[0].replace("User email: <REDACTED_EMAIL_ADDRESS_001>")
    stored = msgs[0].content[0].model_dump()
    assert stored["content"] == "User email: <REDACTED_EMAIL_ADDRESS_001>"


# ── tool def surfaces ─────────────────────────────────────────────────────────


def test_tool_def_description_surface_when_flag_enabled():
    tool = Tool(function=Function(name="send_email", description="Send email to alice@acme.com"))
    req = _make_req([ChatMessage(role="user", content="hi")], tools=[tool])
    msgs = _new_msgs(req)
    surfs = request_surfaces(req, msgs, scan_tool_defs=True)
    tool_def_surfs = [s for s in surfs if s.kind == "tool_def_description"]
    assert len(tool_def_surfs) == 1
    assert "alice@acme.com" in tool_def_surfs[0].text


def test_tool_def_unscanned_when_flag_off():
    tool = Tool(function=Function(name="send_email", description="Send email to alice@acme.com"))
    req = _make_req([ChatMessage(role="user", content="hi")], tools=[tool])
    msgs = _new_msgs(req)
    surfs = request_surfaces(req, msgs, scan_tool_defs=False)
    tool_def_surfs = [s for s in surfs if s.kind == "tool_def_description"]
    assert len(tool_def_surfs) == 0


# ── restore_message ───────────────────────────────────────────────────────────


def test_restore_message_string_content():
    anon_map = AnonymizationMap(
        mapping={"<REDACTED_EMAIL_ADDRESS_001>": "alice@acme.com"},
        reverse={"alice@acme.com": "<REDACTED_EMAIL_ADDRESS_001>"},
        counters={"EMAIL_ADDRESS": 1},
    )
    msg = ChatMessage(role="user", content="Contact <REDACTED_EMAIL_ADDRESS_001> for help")
    restored = restore_message(msg, anon_map)
    assert restored.content == "Contact alice@acme.com for help"
    assert msg.content == "Contact <REDACTED_EMAIL_ADDRESS_001> for help"  # original unchanged


def test_restore_message_tool_calls():
    anon_map = AnonymizationMap(
        mapping={"<REDACTED_EMAIL_ADDRESS_001>": "alice@acme.com"},
        reverse={"alice@acme.com": "<REDACTED_EMAIL_ADDRESS_001>"},
        counters={"EMAIL_ADDRESS": 1},
    )
    tc = ToolCall(
        id="c1",
        function=FunctionCall(name="send", arguments='{"to":"<REDACTED_EMAIL_ADDRESS_001>"}'),
    )
    msg = ChatMessage(role="assistant", content=None, tool_calls=[tc])
    restored = restore_message(msg, anon_map)
    assert json.loads(restored.tool_calls[0].function.arguments)["to"] == "alice@acme.com"


def test_restore_message_anthropic_content_list():
    anon_map = AnonymizationMap(
        mapping={"<REDACTED_EMAIL_ADDRESS_001>": "alice@acme.com"},
        reverse={"alice@acme.com": "<REDACTED_EMAIL_ADDRESS_001>"},
        counters={"EMAIL_ADDRESS": 1},
    )
    part = ContentPart(type="text", text="email is <REDACTED_EMAIL_ADDRESS_001>")
    msg = ChatMessage(role="assistant", content=[part])
    restored = restore_message(msg, anon_map)
    assert restored.content[0].text == "email is alice@acme.com"
