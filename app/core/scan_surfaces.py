"""Enumerates scannable text regions inside structured chat requests/messages.

Each Surface knows its label, the current text, and how to write a redacted
replacement back into the originating message in-place. The proxy iterates
surfaces instead of just msg.content, so tool_call arguments, Anthropic
content blocks, and tool definitions all get scanned + redacted uniformly.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.gateway.schemas import ChatCompletionRequest, ChatMessage, ContentPart, ToolCall

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

SurfaceKind = Literal[
    "user_text",
    "assistant_text",
    "system_text",
    "tool_result",
    "tool_call_args",
    "tool_use_input",
    "tool_def_description",
]


@dataclass
class Surface:
    kind: SurfaceKind
    label: str
    text: str
    replace: Callable[[str], None]


def message_surfaces(msg: ChatMessage, msg_index: int, new_messages: list[ChatMessage]) -> list[Surface]:
    """Yield every scannable text region within one message.

    Mutations are applied to new_messages[msg_index] via replace() closures.
    """
    surfaces: list[Surface] = []

    # ── string content ────────────────────────────────────────────────────────
    if isinstance(msg.content, str) and msg.content:
        kind: SurfaceKind
        if msg.role == "tool":
            kind = "tool_result"
        elif msg.role == "user":
            kind = "user_text"
        elif msg.role == "assistant":
            kind = "assistant_text"
        else:
            kind = "system_text"

        def _replace_str(new_text: str, _idx: int = msg_index) -> None:
            new_messages[_idx] = new_messages[_idx].model_copy(update={"content": new_text})

        surfaces.append(Surface(kind=kind, label=f"msg[{msg_index}].content", text=msg.content, replace=_replace_str))

    # ── list[ContentPart] — Anthropic-style blocks ────────────────────────────
    elif isinstance(msg.content, list):
        for part_idx, part in enumerate(msg.content):
            dumped = part.model_dump()
            ptype = dumped.get("type", "")

            if ptype == "text":
                text_val = dumped.get("text") or ""
                if not text_val:
                    continue
                parent_role = msg.role
                if parent_role == "tool":
                    pkind: SurfaceKind = "tool_result"
                elif parent_role == "user":
                    pkind = "user_text"
                elif parent_role == "assistant":
                    pkind = "assistant_text"
                else:
                    pkind = "system_text"

                def _replace_text_part(
                    new_text: str,
                    _msg_idx: int = msg_index,
                    _part_idx: int = part_idx,
                    _part: ContentPart = part,
                ) -> None:
                    cur = new_messages[_msg_idx]
                    parts = list(cur.content)  # type: ignore[arg-type]
                    parts[_part_idx] = _part.model_copy(update={"text": new_text})
                    new_messages[_msg_idx] = cur.model_copy(update={"content": parts})

                surfaces.append(
                    Surface(
                        kind=pkind,
                        label=f"msg[{msg_index}].content[{part_idx}].text",
                        text=text_val,
                        replace=_replace_text_part,
                    )
                )

            elif ptype == "tool_use":
                raw_input = dumped.get("input", {})
                if not isinstance(raw_input, dict):
                    continue
                text_val = json.dumps(raw_input, ensure_ascii=False)

                def _replace_tool_use(
                    new_text: str,
                    _msg_idx: int = msg_index,
                    _part_idx: int = part_idx,
                    _part: ContentPart = part,
                ) -> None:
                    try:
                        parsed = json.loads(new_text)
                    except (json.JSONDecodeError, ValueError):
                        logger.warning(
                            "scan_surfaces: tool_use input broke JSON after redaction; wrapping as _redacted_text"
                        )
                        parsed = {"_redacted_text": new_text}
                    cur = new_messages[_msg_idx]
                    parts = list(cur.content)  # type: ignore[arg-type]
                    parts[_part_idx] = _part.model_copy(update={"input": parsed})
                    new_messages[_msg_idx] = cur.model_copy(update={"content": parts})

                surfaces.append(
                    Surface(
                        kind="tool_use_input",
                        label=f"msg[{msg_index}].content[{part_idx}].input",
                        text=text_val,
                        replace=_replace_tool_use,
                    )
                )

            elif ptype == "tool_result":
                inner = dumped.get("content")
                if isinstance(inner, str) and inner:

                    def _replace_tool_result_str(
                        new_text: str,
                        _msg_idx: int = msg_index,
                        _part_idx: int = part_idx,
                        _part: ContentPart = part,
                    ) -> None:
                        cur = new_messages[_msg_idx]
                        parts = list(cur.content)  # type: ignore[arg-type]
                        parts[_part_idx] = _part.model_copy(update={"content": new_text})
                        new_messages[_msg_idx] = cur.model_copy(update={"content": parts})

                    surfaces.append(
                        Surface(
                            kind="tool_result",
                            label=f"msg[{msg_index}].content[{part_idx}].content",
                            text=inner,
                            replace=_replace_tool_result_str,
                        )
                    )
                elif isinstance(inner, list):
                    # Recurse one level: nested text blocks inside tool_result
                    for nested_idx, nested in enumerate(inner):
                        if not isinstance(nested, dict):
                            continue
                        if nested.get("type") == "text" and isinstance(nested.get("text"), str):
                            nested_text = nested["text"]
                            if not nested_text:
                                continue

                            def _replace_nested(
                                new_text: str,
                                _msg_idx: int = msg_index,
                                _part_idx: int = part_idx,
                                _nested_idx: int = nested_idx,
                                _part: ContentPart = part,
                                _dumped: dict = dumped,
                            ) -> None:
                                new_inner = list(_dumped["content"])
                                new_inner[_nested_idx] = {**new_inner[_nested_idx], "text": new_text}
                                cur = new_messages[_msg_idx]
                                parts = list(cur.content)  # type: ignore[arg-type]
                                parts[_part_idx] = _part.model_copy(update={"content": new_inner})
                                new_messages[_msg_idx] = cur.model_copy(update={"content": parts})

                            surfaces.append(
                                Surface(
                                    kind="tool_result",
                                    label=f"msg[{msg_index}].content[{part_idx}].content[{nested_idx}].text",
                                    text=nested_text,
                                    replace=_replace_nested,
                                )
                            )

    # ── tool_calls (assistant function calls) ─────────────────────────────────
    if msg.tool_calls:
        for tc_idx, tc in enumerate(msg.tool_calls):
            args = tc.function.arguments
            if not args:
                continue

            def _replace_tool_call_args(
                new_args: str,
                _msg_idx: int = msg_index,
                _tc_idx: int = tc_idx,
                _tc: ToolCall = tc,
            ) -> None:
                new_tc = _tc.model_copy(update={"function": _tc.function.model_copy(update={"arguments": new_args})})
                cur = new_messages[_msg_idx]
                tcs = list(cur.tool_calls or [])
                tcs[_tc_idx] = new_tc
                new_messages[_msg_idx] = cur.model_copy(update={"tool_calls": tcs})

            surfaces.append(
                Surface(
                    kind="tool_call_args",
                    label=f"msg[{msg_index}].tool_calls[{tc_idx}].arguments",
                    text=args,
                    replace=_replace_tool_call_args,
                )
            )

    return surfaces


def request_surfaces(
    req: ChatCompletionRequest,
    new_messages: list[ChatMessage],
    *,
    scan_tool_defs: bool,
) -> list[Surface]:
    """Yield all scannable surfaces in a request (messages + optionally tool defs)."""
    surfaces: list[Surface] = []

    for i, msg in enumerate(req.messages):
        surfaces.extend(message_surfaces(msg, i, new_messages))

    if scan_tool_defs and req.tools:
        for tool_idx, tool in enumerate(req.tools):
            desc = tool.function.description
            if desc:
                surfaces.append(
                    Surface(
                        kind="tool_def_description",
                        label=f"tools[{tool_idx}].function.description",
                        text=desc,
                        replace=lambda _new: None,  # tool defs are read-only; redaction logged only
                    )
                )

    return surfaces


def restore_message(msg: ChatMessage, anon_map) -> ChatMessage:
    """Return a new ChatMessage with all placeholders restored to originals."""
    updates: dict = {}

    if isinstance(msg.content, str):
        restored = anon_map.restore(msg.content)
        if restored != msg.content:
            updates["content"] = restored

    elif isinstance(msg.content, list):
        new_parts = []
        changed = False
        for part in msg.content:
            dumped = part.model_dump()
            ptype = dumped.get("type", "")
            if ptype == "text" and dumped.get("text"):
                restored = anon_map.restore(dumped["text"])
                if restored != dumped["text"]:
                    part = part.model_copy(update={"text": restored})
                    changed = True
            elif ptype == "tool_use":
                raw_input = dumped.get("input", {})
                if isinstance(raw_input, dict):
                    serialized = json.dumps(raw_input, ensure_ascii=False)
                    restored = anon_map.restore(serialized)
                    if restored != serialized:
                        try:
                            part = part.model_copy(update={"input": json.loads(restored)})
                        except (json.JSONDecodeError, ValueError):
                            part = part.model_copy(update={"input": {"_redacted_text": restored}})
                        changed = True
            elif ptype == "tool_result":
                inner = dumped.get("content")
                if isinstance(inner, str):
                    restored = anon_map.restore(inner)
                    if restored != inner:
                        part = part.model_copy(update={"content": restored})
                        changed = True
            new_parts.append(part)
        if changed:
            updates["content"] = new_parts

    if msg.tool_calls:
        new_tcs = []
        tc_changed = False
        for tc in msg.tool_calls:
            args = tc.function.arguments
            if args:
                restored_args = anon_map.restore(args)
                if restored_args != args:
                    tc = tc.model_copy(update={"function": tc.function.model_copy(update={"arguments": restored_args})})
                    tc_changed = True
            new_tcs.append(tc)
        if tc_changed:
            updates["tool_calls"] = new_tcs

    if updates:
        return msg.model_copy(update=updates)
    return msg
