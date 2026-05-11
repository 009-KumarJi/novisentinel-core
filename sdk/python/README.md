# novisentinel

Python SDK for the [NoviSentinel](https://github.com/009-KumarJi/novisentinel-core) AI safety and PII firewall.

## Installation

```bash
pip install novisentinel
```

## Quick start

```python
from novisentinel import Client

client = Client(api_key="nvs_...")

result = client.scan("My SSN is 123-45-6789", context="input")
print(result.action)       # "block" | "warn" | "redact" | "allow"
print(result.has_pii)      # True
print(result.redacted_text) # "My SSN is [SSN]"
```

## Async

```python
from novisentinel import AsyncClient

async with AsyncClient(api_key="nvs_...") as client:
    result = await client.scan("Hello world", context="input")
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
