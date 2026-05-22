# NoviSentinel

**Stop leaking secrets to AI.**

NoviSentinel is the open-source privacy layer between your coding agents — Claude Code, Cursor, Aider, Cline — and the LLMs they talk to. It runs locally on your machine, replaces your sensitive data (API keys, secrets, PII) with stable placeholders before the request leaves your machine, and restores them transparently in the response. The agent gets the work done. Your secrets stay yours.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![CI](https://github.com/009-KumarJi/novisentinel-core/actions/workflows/ci.yml/badge.svg)](https://github.com/009-KumarJi/novisentinel-core/actions/workflows/ci.yml)

---

## Try it in 30 seconds

```bash
docker run -d -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-your-key \
  ghcr.io/009-kumarji/novisentinel:latest

export ANTHROPIC_BASE_URL=http://localhost:8000
# Now use Claude Code, Cursor, or any Anthropic-API client — normally.
claude
```

Your traffic now flows through NoviSentinel. Every secret, API key, email, SSN, credit card, and IP address is replaced with a placeholder before it leaves your machine. The model's response is unredacted on the way back. **You don't change a line of code in your agent — it just works.**

---

## What it protects

Out of the box, NoviSentinel intercepts and redacts:

| Type | Example | Replaced with |
|------|---------|---------------|
| API keys & tokens | `sk-ant-api03-xxx`, `ghp_xxx`, `AKIA…` | `<REDACTED_AWS_ACCESS_KEY_001>` |
| Secrets in code | private keys, JWTs, passwords, AWS secrets | `<REDACTED_JWT_TOKEN_001>` |
| Customer PII | emails, phone, SSN, credit cards, IBAN | `<REDACTED_EMAIL_ADDRESS_001>` |
| Internal URLs / IPs | URLs, bare IP addresses | `<REDACTED_URL_001>` |
| Prompt injection | jailbreaks, role hijacks, exfil attempts | blocked outright |

**Same placeholder for the same value** means the agent can still reason about context. "Fix the bug where `AWS_KEY=<REDACTED_AWS_ACCESS_KEY_001>` isn't loading" works fine — the agent tells you what to change, NoviSentinel swaps the real key back in the response. The model never saw your secret.

### Tool-surface coverage

Coding agents spend most of their time in tool calls — reading files, running shell commands, querying databases. NoviSentinel scans every surface that carries text:

| Surface | Direction | Notes |
|---------|-----------|-------|
| `messages[].content` (string) | Request | User messages, assistant turns, tool-result strings |
| `messages[].content[]` (Anthropic blocks) | Request | `text`, `tool_use.input`, `tool_result.content` |
| `messages[].tool_calls[].function.arguments` | Request | JSON arguments emitted by the model in assistant turns |
| `delta.content` (stream) | Response | Streamed text delta — placeholders restored chunk-by-chunk |
| `delta.tool_calls[].function.arguments` (stream) | Response | Streamed tool-call args — placeholder reassembly across chunk boundaries |
| `choices[].message` (non-stream) | Response | Full non-streaming response message |
| `tools[].function.description` | Request | Optional; disabled by default (`SCAN_TOOL_DEFS=false`) to avoid false-positives on JSON schema field names |

---

## Supported clients

Anything that speaks the Anthropic or OpenAI HTTP API. Set the base URL and you're done:

```bash
# Anthropic (Claude Code, Cursor with Claude, anthropic SDK)
export ANTHROPIC_BASE_URL=http://localhost:8000

# OpenAI (Codex, Cursor with GPT, openai SDK, aider, cline)
export OPENAI_BASE_URL=http://localhost:8000/v1
```

Upstream providers supported: **Anthropic**, **OpenAI**, **Google Gemini**.

See the [examples/](examples/) directory for per-tool setup guides.

---

## How it works

```
┌─────────────┐     ┌────────────────────────────────────────────┐     ┌──────────────┐
│ Claude Code │────▶│ NoviSentinel (localhost:8000)              │────▶│ Anthropic    │
│ Cursor      │     │ 1. Detect secrets/PII in your message      │     │ OpenAI       │
│ Aider       │     │ 2. Replace with <REDACTED_*> placeholders  │     │ Google, etc. │
│ Cline       │     │ 3. Forward redacted request                │     └──────────────┘
└─────────────┘     │ 4. On response, restore original values    │
                    │ 5. Return to your agent — unchanged         │
                    └────────────────────────────────────────────┘
```

Detection runs across 7 parallel detectors — Presidio (PII), regex (secrets), DeBERTa-v3 (injection), Detoxify (toxicity), URL safety, code injection, and optional custom HTTP endpoints. Typical added latency is ~300ms p95 on English text up to 2KB on a laptop CPU; this is dominated by transformer inference for the injection + toxicity detectors. Disabling those two via env config brings p95 below 50ms when only regex/PII detection is needed. Streaming is preserved end-to-end.

---

## Why this exists

Coding agents are the most powerful dev tool of the last decade. They're also the largest accidental data-exfiltration risk most developers have ever wired into their workflow:

- Your `.env` files are in scope every time you ask an agent to fix a config bug.
- Customer data in your test fixtures gets sent to a model provider.
- Internal hostnames, schema names, and code structure leak into every prompt.

NoviSentinel is a 30-second install that says: **the agent can still help you, without your secrets being part of the deal.**

---

## Configuration

Copy `.env.example` to `.env` and fill in the keys for the providers you use:

```env
# At least one provider key is required
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Optional: custom detector endpoints (comma-separated URLs)
# CUSTOM_DETECTOR_ENDPOINTS=https://your-detector.example.com/scan
```

All settings are optional except for the provider key. NoviSentinel starts without any API keys; it will return a 502 if you proxy a request without the relevant key configured.

### BYOK (Bring Your Own Key)

By default, NoviSentinel uses the server-side env key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) for all upstream calls. Any bearer token or `x-api-key` header sent by your client is silently ignored — this prevents IDE/agent vestigial auth headers from breaking upstream calls.

To forward your own key instead, add `X-Use-BYOK: true` to the request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "X-Use-BYOK: true" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'
```

If `X-Use-BYOK: true` is set but no bearer is supplied, the request is rejected with HTTP 400.

### Session persistence

By default each request starts a fresh anonymization map, so there is no state between calls. For multi-turn conversations where the same secret must map to the same placeholder across turns — even across proxy restarts — send `X-Novisentinel-Session` with an opaque identifier of your choice:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-Novisentinel-Session: my-dev-session-1" \
  -H "Content-Type: application/json" \
  -d '...'
```

NoviSentinel persists the anonymization map to `~/.novisentinel/sessions/` (configurable via `SESSION_DIR`). Files are cleaned up after `SESSION_TTL_HOURS` hours of inactivity (default 24 h).

**Privacy note:** Session files contain the original plaintext values next to their placeholders (so the proxy can restore them in responses). They are stored with mode `0600` under a `0700` directory. To wipe all session data:

```bash
python scripts/purge_sessions.py --all
```

Or to remove only expired files:

```bash
python scripts/purge_sessions.py
```

Additional session-related env vars:

```env
SESSION_DIR=~/.novisentinel/sessions   # where session files live
SESSION_TTL_HOURS=24                   # evict files older than this
```

---

## What it's not

Honest limitations:

- **Not a corporate DLP.** A motivated developer can unset the env var. This protects you from yourself and from accidents, not from a malicious insider.
- **Not a model-side guarantee.** If the model receives a secret in a previous turn (before NoviSentinel was in the loop), it may repeat it in later responses. NoviSentinel scans your prompts on the way out — once a secret has reached the model in an earlier session, this proxy can't pull it back.
- **Output content is not scanned.** The proxy restores placeholders in responses; it does not block new secrets the LLM might hallucinate. Scanning model output for novel secrets/exfil patterns is on the roadmap.
- **Detectors are imperfect.** Presidio misses some unusual PII formats. The injection model has a ~2-5% false positive rate. We tune toward over-redacting.

---

## Build from source

```bash
git clone https://github.com/009-KumarJi/novisentinel-core
cd novisentinel-core
pip install -r requirements.txt
python -m spacy download en_core_web_lg
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest tests/ -v
```

API docs (after starting): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Roadmap

- [ ] MCP-aware proxy (intercept tool calls before they execute)
- [ ] One-binary install (`npx novisentinel` / `brew install novisentinel`)
- [ ] On-device redaction status via VS Code extension
- [ ] Custom redaction rules via YAML config
- [ ] Bring your own detector (any HuggingFace model)
- [ ] Groq, OpenRouter, Ollama, and vLLM provider support

---

## License

Apache 2.0. Use it, fork it, ship it.

---

## Get involved

- **Star this repo** — it helps with discovery.
- **Open an issue** if you find a detection NoviSentinel misses. Real-world false negatives are how we improve.
- **Email**: krishna902kumar@gmail.com — for anything else.

NoviSentinel is built by [Krishna Kumar](https://github.com/009-KumarJi). If this saves you a sleepless night worrying about what your agent just sent to Claude, that's the whole point.
