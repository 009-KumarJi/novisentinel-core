# Security Policy

NoviSentinel is a security tool — we take vulnerabilities in our own code extremely seriously.

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, report them privately:

1. **Email:** [security@novisentinel.com](mailto:security@novisentinel.com)
2. **Subject line:** `[SECURITY] <brief description>`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to expect

| Timeline          | Action                                              |
|-------------------|-----------------------------------------------------|
| Within 48 hours   | We acknowledge your report                          |
| Within 7 days     | We triage and assess severity                       |
| Within 30 days    | We release a fix for confirmed vulnerabilities      |

We will credit you in the release notes (unless you prefer to remain anonymous).

## Scope

The following are in scope for security reports:

| Area                         | Examples                                                      |
|------------------------------|---------------------------------------------------------------|
| **Authentication bypass**    | Accessing admin endpoints without master key                  |
| **Injection in the scanner** | Crafted input that bypasses all detection layers              |
| **PII / secrets leakage**    | Scan logs or API responses exposing raw sensitive text        |
| **SSRF via webhooks**        | Webhook URLs targeting internal services                      |
| **Dependency vulnerabilities** | Known CVEs in pinned dependencies                           |
| **Rate limit bypass**        | Circumventing the sliding-window rate limiter                 |

### Out of scope

- Denial of service via large payloads (we have rate limiting)
- Vulnerabilities in third-party ML models (report upstream to model maintainers)
- Social engineering attacks

## Security Design

NoviSentinel follows these security principles:

- **No raw text storage** — only SHA256 hashes of scanned text are persisted
- **HMAC-signed webhooks** — every webhook delivery is signed with `X-NoviSentinel-Signature`
- **SSRF protection** — webhook URLs are validated to block internal/private network targets
- **API key hashing** — keys are stored as SHA256 hashes, never in plaintext
- **Master key enforcement** — production deployments reject the default `dev-master-key`
- **Rate limiting** — sliding window per API key via Redis

## Responsible Disclosure

We ask that you:

1. Give us reasonable time to fix the issue before public disclosure
2. Do not access or modify data belonging to other users
3. Act in good faith to avoid degradation of our services

Thank you for helping keep NoviSentinel and its users safe.
