# Changelog

All notable changes to NoviSentinel are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2026-05-07

### Added

- **Core scan engine** — orchestrates PII, injection, secrets, and toxicity detectors in parallel
- **PII detection** — SSN, credit card, email, phone, IP, IBAN via Microsoft Presidio NLP
- **Prompt injection detection** — two-layer system: fast regex patterns → ML fallback (DeBERTa v3)
- **Secrets detection** — regex scanner for OpenAI, Anthropic, AWS, GitHub, Stripe, JWT, and private keys
- **Toxicity detection** — detoxify ML model for threats, hate speech, harassment, obscenity
- **REST API** — `POST /v1/scan`, `POST /v1/scan/batch`, health endpoint
- **API key management** — create, list, revoke keys (master key protected)
- **Webhook system** — HMAC-signed HTTP POST notifications on block/warn events
- **Scan logging** — persistent scan history with SHA256 text hashing (no raw text stored)
- **Stats endpoint** — aggregate scan statistics via SQL
- **Rate limiting** — sliding window per API key via Redis
- **Python SDK** — sync and async clients, batch scanning (`pip install novisentinel`)
- **Admin dashboard** — Next.js dashboard with overview, logs, analytics, and settings pages
- **Docker Compose** — one-command boot with PostgreSQL, Redis, and API
- **Test suite** — 54 tests covering all detectors, API endpoints, auth, and webhooks
- **Postman collection** — 20 requests with auto-save test scripts

### Security

- Master key enforcement — production rejects the default `dev-master-key`
- SSRF protection — webhook URLs validated against internal/private network targets
- API keys stored as SHA256 hashes
- Configurable CORS origins

### Performance

- Batch scan runs items concurrently with `asyncio.gather`
- Stats aggregated with SQL instead of loading all rows into Python
- Database indexes on `created_at` for scan logs and webhook configs
- CPU-only PyTorch in Docker build (avoids 1GB+ CUDA packages)
- ML models pre-downloaded during Docker build for instant startup
