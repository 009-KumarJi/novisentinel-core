# NoviSentinel

**AI Safety & PII Firewall for LLM applications.**

Drop-in scan API that sits between your app and your LLM. Detects and blocks prompt injection, PII leaks, exposed credentials, and toxic content — in real time.

> Developer-first alternative to Lakera Guard. Self-hostable, open source, no sales call required.

---

## What it catches

| Threat | Method | Latency |
|--------|--------|---------|
| Prompt injection (override, jailbreak, role hijack, exfil) | Regex → ML fallback | ~1ms / ~80ms |
| PII (SSN, credit card, email, phone, IP, IBAN) | Presidio NLP | ~5ms |
| Secrets (OpenAI, Anthropic, AWS, GitHub, Stripe, JWT, private keys) | Regex | <1ms |
| Toxicity (threats, hate speech, harassment, obscenity) | detoxify ML | ~100ms |

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

Raw text is **never stored** — only a SHA256 hash of each scanned text is persisted.

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
│   └── toxicity.py    # detoxify ML
├── db/
│   ├── models.py      # ApiKey, ScanLog, WebhookConfig SQLAlchemy models
│   └── session.py     # Async engine
└── config.py          # Pydantic settings

sdk/python/            # pip install novisentinel
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

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

54 tests across: PII, injection, secrets, toxicity, webhooks, API integration.

---

## Stack

- **FastAPI** — async API framework
- **PostgreSQL + asyncpg** — scan logs, API keys, webhook configs
- **Redis** — sliding window rate limiting
- **Presidio** — Microsoft's PII detection engine
- **protectai/deberta-v3-base-prompt-injection-v2** — ML injection classifier
- **detoxify** — toxicity classification (unitary/toxic-bert)
- **httpx** — async webhook delivery + SDK HTTP client
- **Docker Compose** — postgres + redis + api, one command boot

---

## License

Copyright 2026 Kumar Ji (009-KumarJi)

Licensed under the [Apache License, Version 2.0](LICENSE). See [LICENSE](LICENSE) for the full text.
