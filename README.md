# NoviSentinel

**An open-source safety scanner for LLM applications.**

Self-hostable FastAPI service that detects and blocks PII leaks, prompt injection, exposed credentials, and toxic content — in real time, in front of any LLM.

> Drop it between your app and your model. Scan input before it goes to the LLM, scan output before it goes to the user. Block what's dangerous, redact what's sensitive, allow what's clean.

---

## What it catches

| Threat | Method | Latency |
|--------|--------|---------|
| Prompt injection (override, jailbreak, role hijack, exfil) | Regex → ML fallback | ~1ms / ~80ms |
| PII (SSN, credit card, email, phone, IP, IBAN) | Presidio NLP | ~5ms |
| Secrets (OpenAI, Anthropic, AWS, GitHub, Stripe, JWT, private keys) | Regex | <1ms |
| Toxicity (threats, hate speech, harassment, obscenity) | Detoxify ML | ~100ms |

All four detectors run in parallel per request. Total p95 budget: ~120ms on CPU for English text up to 2KB.

---

## Quick start

```bash
git clone https://github.com/009-KumarJi/novi-sentinel
cd novi-sentinel
cp .env.example .env
docker compose up
```

API is live at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

---

## How it works

Every LLM app has two moments of risk — what the user sends in, and what the model sends back.

```
User input  →  your app  →  POST /v1/scan  →  NoviSentinel  →  allow / block / redact  →  LLM
LLM output  →  your app  →  POST /v1/scan  →  NoviSentinel  →  allow / block / redact  →  User
```

NoviSentinel returns an action for every scan:

| Action | Meaning |
|--------|---------|
| `allow` | Clean — pass through |
| `warn` | Low-severity detection — log and monitor |
| `redact` | PII found — use `redacted_text` instead of original |
| `block` | Injection, secrets, or critical threat — do not forward |

---

## Python SDK

```bash
pip install novisentinel
```

```python
from novisentinel import Client

client = Client(api_key="nvs_...", base_url="http://localhost:8000")

# Scan user input before sending to LLM
result = client.scan(user_message, context="input")
if result.action == "block":
    return "I can't process that request."

# Scan LLM output before returning to user
response = openai.chat(...)
result = client.scan(response.content, context="output")
return result.redacted_text  # PII scrubbed
```

### Async

```python
from novisentinel import AsyncClient

client = AsyncClient(api_key="nvs_...")
result = await client.scan(text, context="input")
```

### Batch

```python
results = client.scan_batch(["text1", "text2", "text3"])
```

---

## VS Code extension

Scan prompts before you send them — without leaving your editor.

```
@novisentinel my SSN is 123-45-6789
```

Right-click any selected text → **NoviSentinel: Scan Selection**.
Copied something sensitive? → **NoviSentinel: Scan Clipboard** before pasting into ChatGPT.

Install from the VS Code Marketplace (search "NoviSentinel") or build from [`extensions/vscode/`](extensions/vscode/).

---

## REST API

### Authentication

| Header | Used for |
|--------|---------|
| `x-master-key: <key>` | Admin operations (create/revoke API keys, view logs) |
| `Authorization: Bearer <api_key>` | Scanning and webhooks |

### Scan

**`POST /v1/scan`**

```json
{
  "text": "My SSN is 123-45-6789",
  "context": "input",
  "config": {
    "injection_threshold": 0.85,
    "pii_entities": ["US_SSN", "CREDIT_CARD"]
  }
}
```

Response:

```json
{
  "scan_id": "uuid",
  "safe": false,
  "risk_level": "critical",
  "action": "block",
  "detections": [
    {
      "detector": "pii",
      "type": "US_SSN",
      "text": "123-45-6789",
      "redacted": "<US_SSN>",
      "start": 10,
      "end": 21,
      "confidence": 0.85,
      "severity": "critical"
    }
  ],
  "redacted_text": "My SSN is <US_SSN>",
  "original_length": 21,
  "scan_duration_ms": 12
}
```

**`POST /v1/scan/batch`** — up to 20 texts in one request

```json
{
  "texts": [
    { "text": "hello", "context": "input" },
    { "text": "ignore all previous instructions", "context": "input" }
  ]
}
```

### Per-request config

Override global settings on individual scans:

| Key | Default | Description |
|-----|---------|-------------|
| `injection_threshold` | `0.85` | ML confidence threshold for subtle injection |
| `pii_entities` | all | Restrict which PII types to scan for |
| `toxicity_threshold_severe` | `0.5` | Threshold for severe_toxic / threat |
| `toxicity_threshold_high` | `0.7` | Threshold for toxic / identity_hate |
| `toxicity_threshold_medium` | `0.8` | Threshold for obscene / insult |

### API Keys

```
POST   /v1/keys          # create key (master key required)
GET    /v1/keys          # list keys (master key required)
DELETE /v1/keys/{id}     # revoke key (master key required)
```

### Webhooks

Get notified via HTTP POST when a scan blocks or warns.

```
POST   /v1/webhooks      # register a webhook endpoint
GET    /v1/webhooks      # list webhooks for your key
DELETE /v1/webhooks/{id} # remove a webhook
```

**Create webhook:**

```json
{
  "url": "https://hooks.slack.com/...",
  "trigger_actions": ["block", "warn"],
  "trigger_risk_levels": ["critical", "high"]
}
```

Returns a `signing_secret` (shown once). Every delivery is signed:

```
X-NoviSentinel-Signature: sha256=<HMAC-SHA256(secret, payload)>
```

**Webhook payload:**

```json
{
  "event": "detection.block",
  "scan_id": "uuid",
  "risk_level": "critical",
  "action": "block",
  "context": "input",
  "pii_count": 0,
  "injection_count": 1,
  "secrets_count": 0,
  "toxicity_count": 0,
  "detections": [
    { "detector": "injection", "type": "OVERRIDE", "severity": "critical", "confidence": 0.97 }
  ],
  "timestamp": "2026-05-07T10:00:00Z"
}
```

### Logs & Stats

```
GET /v1/logs   # scan history (master key required)
GET /v1/stats  # aggregate stats (master key required)
```

Logs support query params: `?action=block`, `?risk_level=critical`, `?context=input`, `?since=2026-05-01T00:00:00`, `?limit=100`.

Raw text is **never stored** — only a SHA-256 hash of each scanned text is persisted.

---

## Configuration

All settings via environment variables (see `.env.example`):

```env
# Auth
MASTER_API_KEY=change-me-to-a-long-random-string

# Database & cache
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@postgres:5432/novisentinel
REDIS_URL=redis://redis:6379

# ML models
SPACY_MODEL=en_core_web_lg
INJECTION_MODEL=protectai/deberta-v3-base-prompt-injection-v2
INJECTION_THRESHOLD=0.85

# Toxicity
TOXICITY_ENABLED=true
TOXICITY_MODEL=original
TOXICITY_THRESHOLD_SEVERE=0.5
TOXICITY_THRESHOLD_HIGH=0.7
TOXICITY_THRESHOLD_MEDIUM=0.8

# Rate limiting
DEFAULT_RATE_LIMIT_RPM=120
```

---

## Architecture

```
app/
├── api/
│   ├── scan.py        # POST /v1/scan, /v1/scan/batch
│   ├── keys.py        # API key management
│   ├── webhooks.py    # Webhook CRUD
│   └── logs.py        # Scan history + stats
├── core/
│   ├── scanner.py     # Orchestrator — runs all detectors, builds ScanResult
│   └── webhook.py     # HMAC-signed fire-and-forget delivery
├── detectors/
│   ├── base.py        # Detector ABC + DetectionResult dataclass
│   ├── pii.py         # Presidio NLP
│   ├── injection.py   # Regex → ML two-layer detection
│   ├── secrets.py     # Regex credential scanner
│   └── toxicity.py    # Detoxify ML
├── db/
│   ├── models.py      # ApiKey, ScanLog, WebhookConfig SQLAlchemy models
│   └── session.py     # Async engine
└── config.py          # Pydantic settings

sdk/python/            # pip install novisentinel
extensions/vscode/     # @novisentinel chat participant + scan commands
dashboard/             # local single-tenant Next.js dashboard
tests/                 # 54 tests, pytest-asyncio
```

**Scan pipeline (per request):**

```
text
 ├── PIIDetector.scan()           (sync, Presidio)
 ├── SecretsDetector.scan()       (sync, regex)
 ├── InjectionDetector.scan_async()   ─┐ asyncio.gather()
 └── ToxicityDetector.scan_async()    ─┘
          ↓
   _determine_risk()   → none / low / medium / high / critical
   _determine_action() → allow / warn / redact / block
   _build_redacted_text()
```

---

## Action logic

| Condition | Action |
|-----------|--------|
| Any injection detected | `block` |
| Any secret detected | `block` |
| Toxicity severity = critical | `block` |
| Toxicity severity = medium | `warn` |
| Critical PII (SSN, credit card, IBAN) | `block` |
| High/medium PII (email, phone, IP) | `redact` |
| Low confidence detections | `warn` |
| Nothing detected | `allow` |

---

## Local dashboard

A Next.js dashboard at [`dashboard/`](dashboard/) gives you a local view of scans, logs, and stats. Single-tenant, master-key auth. Boots alongside the API via Docker Compose.

```
http://localhost:3001
```

Pages:
- **Overview** — KPIs, recent activity, blocks per minute
- **Logs** — full scan history with filters
- **Analytics** — risk-level distribution, detector hit rates
- **Settings** — API keys, webhooks

---

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

54 tests across PII, injection, secrets, toxicity, webhooks, and API integration.

---

## Stack

- **FastAPI** — async API framework
- **PostgreSQL + asyncpg** — scan logs, API keys, webhook configs
- **Redis** — sliding window rate limiting
- **Presidio** — PII detection engine (Microsoft)
- **protectai/deberta-v3-base-prompt-injection-v2** — ML injection classifier
- **Detoxify** — toxicity classification (unitary/toxic-bert)
- **httpx** — async webhook delivery + SDK HTTP client
- **Docker Compose** — postgres + redis + api, one command boot

---

## What this is for

Use NoviSentinel when:

- **Your app sends user-generated text to an LLM** and you want to catch PII, secrets, and injection attempts before they leave your system.
- **Your app surfaces LLM responses to users** and you want to redact PII or block toxic content before the user sees it.
- **You log LLM prompts and responses** and you want a verdict on each (`safe`, `risk_level`, `action`) alongside the raw text.
- **You're building an agent** that uses tools — scan tool-call arguments before execution, scan tool-call outputs before they're handed back to the model.
- **You want self-hosting and a local dashboard** rather than a hosted SaaS scanner.

NoviSentinel is one HTTP call. It doesn't replace your LLM, your auth, your logging, or your application logic — it sits next to them and watches text.

---

## Privacy & data handling

- Raw text is never stored. Every scanned text is hashed to SHA-256 before persistence.
- Scan logs contain: hash, length, detector results, risk level, action, timestamp.
- No third-party calls happen during a scan unless you explicitly enable a feature that requires one.
- Webhook payloads are HMAC-signed. You verify with the `signing_secret` returned at webhook creation.
- All models run locally inside the container. No data leaves your network.

---

## Roadmap

- Code injection detection
- URL safety detection
- Multilingual support
- Browser extension (ChatGPT.com, Claude.ai)
- Node / TypeScript SDK
- Custom detector support (plug in your own scanner)

See [`plans/`](plans/) for the detailed roadmap.

---

## Contributing

Issues and PRs welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, coding conventions, and the PR process.

For security disclosures, **do not open a public issue** — see [`SECURITY.md`](SECURITY.md).

---

## License

Copyright 2026 Kumar Ji (009-KumarJi)

Licensed under the [Apache License, Version 2.0](LICENSE). See [LICENSE](LICENSE) for the full text.
