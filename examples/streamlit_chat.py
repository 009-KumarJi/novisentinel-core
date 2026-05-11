"""
Streamlit chat demo with NoviSentinel guarding both directions.

Usage:
    export OPENAI_API_KEY=sk-...
    export NOVISENTINEL_API_KEY=nvs_...
    streamlit run examples/streamlit_chat.py
"""

from __future__ import annotations

import os

import streamlit as st
from openai import OpenAI

from novisentinel import Client

# ── Setup ─────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="NoviSentinel Chat Demo", page_icon="🛡")
st.title("🛡 NoviSentinel Chat Demo")
st.caption("Every message is scanned for PII, prompt injection, secrets, and toxicity.")

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
sentinel = Client(
    api_key=os.environ.get("NOVISENTINEL_API_KEY", "dev-master-key"),
    base_url=os.environ.get("NOVISENTINEL_URL", "http://localhost:8000"),
)

# ── Session state ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "scan_log" not in st.session_state:
    st.session_state.scan_log = []

# ── Sidebar: scan log ──────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader("Recent Scans")
    for entry in reversed(st.session_state.scan_log[-10:]):
        badge = {"block": "🛑", "warn": "⚠️", "redact": "✏️", "allow": "✅"}.get(entry["action"], "?")
        st.markdown(
            f"{badge} **{entry['action'].upper()}** · {entry['direction']} · {len(entry['detections'])} detection(s)"
        )
        for d in entry["detections"]:
            st.caption(f"  {d['detector']}/{d['type']} ({d['severity']})")

# ── Chat history ───────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("blocked"):
            st.error(f"🛑 Blocked by NoviSentinel — {msg['reason']}")
            with st.expander("Detection details"):
                for d in msg.get("detections", []):
                    st.json(d)

# ── Input ──────────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Type a message..."):
    # 1. Scan input
    input_scan = sentinel.scan(prompt, context="input")
    st.session_state.scan_log.append(
        {
            "direction": "input",
            "action": input_scan.action,
            "detections": [d.model_dump() for d in input_scan.detections],
        }
    )

    if input_scan.action == "block":
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
                "blocked": True,
                "reason": input_scan.detections[0].type if input_scan.detections else "unknown",
                "detections": [d.model_dump() for d in input_scan.detections],
            }
        )
        with st.chat_message("user"):
            st.markdown(prompt)
            st.error(f"🛑 Message blocked — {input_scan.detections[0].type if input_scan.detections else ''}")
        st.rerun()

    cleaned = input_scan.redacted_text
    st.session_state.messages.append({"role": "user", "content": cleaned})
    with st.chat_message("user"):
        st.markdown(cleaned)
        if cleaned != prompt:
            st.caption("✏️ PII was redacted before sending.")

    # 2. Call OpenAI
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            )
            reply = resp.choices[0].message.content or ""

        # 3. Scan output
        output_scan = sentinel.scan(reply, context="output")
        st.session_state.scan_log.append(
            {
                "direction": "output",
                "action": output_scan.action,
                "detections": [d.model_dump() for d in output_scan.detections],
            }
        )

        if output_scan.action == "block":
            st.error("🛑 Response blocked by NoviSentinel safety filter.")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": "[response blocked]",
                    "blocked": True,
                    "reason": output_scan.detections[0].type if output_scan.detections else "unknown",
                    "detections": [d.model_dump() for d in output_scan.detections],
                }
            )
        else:
            st.markdown(output_scan.redacted_text)
            st.session_state.messages.append({"role": "assistant", "content": output_scan.redacted_text})
