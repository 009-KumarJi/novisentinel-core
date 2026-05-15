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
| API keys & tokens | `sk-ant-api03-xxx`, `ghp_xxx`, `AKIA…` | `<REDACTED_API_KEY_001>` |
| Secrets in code | private keys, JWTs, OAuth secrets | `<REDACTED_SECRET_001>` |
| Customer PII | emails, phone, SSN, credit cards, IBAN | `<REDACTED_EMAIL_001>` |
| Internal URLs / IPs | bare IP addresses, IDN homographs | `<REDACTED_IP_ONLY_001>` |
| Prompt injection | jailbreaks, role hijacks, exfil attempts | blocked outright |
| Malicious output | `rm -rf`, hidden exfiltration patterns | blocked outright |

**Same placeholder for the same value** means the agent can still reason about context. "Fix the bug where `AWS_KEY=<REDACTED_API_KEY_001>` isn't loading" works fine — the agent tells you what to change, NoviSentinel swaps the real key back in the response. The model never saw your secret.

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

Detection runs across 7 parallel detectors — Presidio (PII), regex (secrets), DeBERTa-v3 (injection), Detoxify (toxicity), URL safety, code injection, and optional custom HTTP endpoints. Added latency is ~50ms p95 on English text up to 2KB on a laptop CPU. Streaming is preserved end-to-end.

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

---

## What it's not

Honest limitations:

- **Not a corporate DLP.** A motivated developer can unset the env var. This protects you from yourself and from accidents, not from a malicious insider.
- **Not a model-side guarantee.** If the model receives a secret in a previous turn (before NoviSentinel was in the loop), it may repeat it in later responses. Output scanning catches most such cases but isn't bulletproof.
- **Streaming output cannot be blocked mid-token.** Inputs are blocked before they leave your machine. Streamed responses are scanned at stream end, not preemptively mid-token.
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
