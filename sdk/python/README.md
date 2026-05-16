# novisentinel

Python SDK for [NoviSentinel](https://github.com/009-KumarJi/novisentinel-core) — the open-source privacy proxy for AI coding agents.

## Installation

```bash
pip install novisentinel
```

## Quick start

```python
from novisentinel import Client

# No API key needed for local self-hosted NoviSentinel
client = Client()

result = client.scan("My SSN is 123-45-6789", context="input")
print(result.action)        # "block" | "warn" | "redact" | "allow"
print(result.has_pii)       # True
print(result.redacted_text) # "My SSN is [SSN]"
```

## Hosted / remote usage

```python
client = Client(api_key="nvs_...", base_url="https://api.novisentinel.com")
```

## Async

```python
from novisentinel import AsyncClient

async with AsyncClient() as client:
    result = await client.scan("Hello world", context="input")
```

## Batch scanning

```python
results = client.scan_batch(["text1", "text2"], context="input")
# Async version runs concurrently
results = await async_client.scan_batch(["text1", "text2"])
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
